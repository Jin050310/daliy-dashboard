"""새 연말 공시가 나오면 보유 기준을 자동으로 교체한다.

    python roll_year.py            # 새 공시가 있으면 적용 (없으면 아무것도 안 한다)
    python roll_year.py --year 2026  # 그 연도를 지정해 적용

기금운용본부는 전년도 말 종목별 보유 내역을 매년 3분기에 공시한다. 자동 업데이트가 매일 이 스크립트를 돌린다.
    1) 홈페이지 '투자종목' 다운로드 버튼에서 새 연도를 찾는다.
    2) 엑셀을 받아 종목명·평가액·지분율을 읽고, 그 해 마지막 거래일 전 종목 종가로 종목코드를 맞춘다.
    3) 보유주식수 = 평가액 / 그 날 종가 로 계산한다.
    4) 아래 검증을 모두 통과할 때만 data/bases/YYYY/에 저장하고, 기준일 뒤 일별 종가를 지워 step6이
       새 보유 종목으로 다시 받게 한다. 실패하면 아무것도 바꾸지 않고 오류로 끝나 알림 메일이 온다.

검증: 파일 안의 기준 연도 일치, 종목 수, 확정 매핑 비율, 공시 총액 대비 커버율,
      평가액 역산 주식 수와 '지분율 x 상장주식수'의 일치 여부(평가액이 그 날 종가 기준인지 확인).
"""
import argparse
import html
import io
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from datetime import date, timedelta

import pandas as pd

import bases
import config
import krx_api
import nps_http
import step4_map_codes as step4

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

MIN_ROWS = 500          # 이보다 종목이 적으면 파일을 잘못 읽은 것으로 본다
MIN_MAPPED_PCT = 99.5   # 확정 매핑 평가액 비율 하한
COVER_RANGE = (95, 105)  # 공시 국내주식 총액 대비 합계 비율 (%)
CHECK_MIN_EOK = 100     # 교차 검증 대상 평가액 하한 (억)
CHECK_TOL = 0.05        # 교차 검증 허용 차이
CHECK_PASS_PCT = 95     # 대상 중 허용 차이 안에 들어야 하는 비율 (%)
XLSX_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
CONFIRMED = {"manual", "exact", "normalized"}


def available_files() -> dict[int, str]:
    """홈페이지 '투자종목' 버튼: {연도: 파일 주소}."""
    page = nps_http.fetch("GET", config.HOLDINGS_PAGE_URL).text
    links = re.findall(r'href="(/fileDown\.do\?[^"]+)"[^>]*>\s*(20\d\d)\s*</a>', page)
    return {int(y): config.HOLDINGS_FILE_BASE + html.unescape(u) for u, y in links}


def read_sheet(content: bytes) -> list[list[str]]:
    """표준 라이브러리로 엑셀 첫 시트를 읽는다."""
    def col_index(ref: str) -> int:
        n = 0
        for ch in re.match(r"[A-Z]+", ref).group():
            n = n * 26 + ord(ch) - 64
        return n - 1

    with zipfile.ZipFile(io.BytesIO(content)) as z:
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall(f"{XLSX_NS}si"):
                shared.append("".join(t.text or "" for t in si.iter(f"{XLSX_NS}t")))
        sheet = sorted(n for n in z.namelist() if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", n))[0]
        rows = []
        for row in ET.fromstring(z.read(sheet)).iter(f"{XLSX_NS}row"):
            cells = {}
            for c in row.findall(f"{XLSX_NS}c"):
                v, t = c.find(f"{XLSX_NS}v"), c.get("t")
                if t == "inlineStr":
                    val = "".join(x.text or "" for x in c.iter(f"{XLSX_NS}t"))
                elif v is None:
                    val = ""
                else:
                    val = shared[int(v.text)] if t == "s" else v.text
                cells[col_index(c.get("r"))] = val
            rows.append([cells.get(i, "") for i in range(max(cells) + 1)] if cells else [])
    return rows


def number(x: str) -> tuple[float, bool]:
    """연도마다 다른 숫자 표기를 읽는다. (값, % 표시 여부). '7.28%', '551,095', '-', 빈칸을 모두 받는다."""
    s = str(x).strip().replace(",", "")
    is_pct = s.endswith("%")
    s = s.rstrip("%").strip()
    return (float(s) if s not in ("", "-") else 0.0), is_pct


def parse_holdings(rows: list[list[str]], year: int) -> pd.DataFrame:
    head = "\n".join(str(c) for r in rows[:6] for c in r)
    label = re.search(r"(20\d\d)\s*년\s*말\s*기준", head)
    if not label or int(label.group(1)) != year:
        raise SystemExit(f"파일의 기준 연도가 {year}년이 아닙니다: {label.group(0) if label else '표시 없음'}")
    idx = next((i for i, r in enumerate(rows) if r and str(r[0]).strip() == "번호"), None)
    if idx is None:
        raise SystemExit("'번호' 머리글을 찾지 못했습니다. 파일 형식이 바뀐 것 같습니다.")
    cols = {str(c).strip(): i for i, c in enumerate(rows[idx])}
    find = lambda word: next((i for name, i in cols.items() if name.startswith(word)), None)
    i_name, i_val, i_stake = find("종목명"), find("평가액"), find("지분율")
    if None in (i_name, i_val, i_stake):
        raise SystemExit(f"필요한 열을 찾지 못했습니다: {list(cols)}")
    out, any_pct_text = [], False
    for r in rows[idx + 1:]:
        if len(r) <= max(i_name, i_val, i_stake) or not str(r[0]).strip() or not str(r[i_name]).strip():
            continue
        try:
            stake, is_pct = number(r[i_stake])
            out.append({"번호": int(float(r[0])), "종목명": str(r[i_name]).strip(),
                        "평가액_억": number(r[i_val])[0], "지분율": stake})
        except ValueError:
            raise SystemExit(f"숫자를 읽지 못했습니다: {r}") from None
        any_pct_text = any_pct_text or is_pct
    df = pd.DataFrame(out)
    if len(df) < MIN_ROWS:
        raise SystemExit(f"종목이 {len(df)}개뿐입니다. 파일을 잘못 읽은 것 같습니다.")
    # 7.76%가 '7.76%' 글자나 7.76이 아니라 0.0776으로 저장된 해가 있다. 0.0776을 그대로 쓰면 지분율이 100배 작아진다
    if not any_pct_text and df["지분율"].max() <= 1:
        df["지분율"] = (df["지분율"] * 100).round(2)
    return df


def last_trading_day(year: int) -> tuple[str, pd.DataFrame]:
    d = date(year, 12, 31)
    for _ in range(10):
        rows = krx_api.fetch_all(config.STOCK_PRICE_URL, {"basDt": d.strftime("%Y%m%d")}, rows_per_page=5000)
        if rows:
            return d.strftime("%Y%m%d"), pd.DataFrame(rows)
        d -= timedelta(days=1)
    raise SystemExit(f"{year}년 말 거래일의 종가를 찾지 못했습니다.")


def official_total(year: int) -> float | None:
    """홈페이지 자산군별 운용규모의 그 해 국내주식 총액(조 원)."""
    r = nps_http.fetch("POST", config.OFFICIAL_SIZE_URL, json={"searchGbu": "5", "cartMngSn": "1"})
    for x in r.json().get("resultDtlList") or []:
        if x.get("artclCn1") == str(year) and x.get("artclCn3"):
            return float(x["artclCn3"]) / 1000
    return None


def build_shares(hold: pd.DataFrame, prices: pd.DataFrame) -> pd.DataFrame:
    """종목코드를 맞추고 보유주식수를 계산한다."""
    listed = pd.DataFrame({"_name": prices["itmsNm"], "_code": prices["srtnCd"], "_mkt": prices["mrktCtg"]})
    exact, norm, market = step4.build_index(listed)
    keys, manual = list(norm.keys()), step4.load_manual()
    res = [step4.match_one(n, exact, norm, keys, manual) for n in hold["종목명"]]
    hold = hold.assign(종목코드=[r[0] for r in res], 매핑방식=[r[1] for r in res])
    hold["시장"] = hold["종목코드"].map(market).fillna("")
    p = prices[["srtnCd", "clpr", "lstgStCnt"]].rename(
        columns={"srtnCd": "종목코드", "clpr": "종가", "lstgStCnt": "상장주식수"}
    )
    p["종가"], p["상장주식수"] = pd.to_numeric(p["종가"]), pd.to_numeric(p["상장주식수"])
    df = hold.merge(p, on="종목코드", how="left")
    df["확정"] = df["매핑방식"].isin(CONFIRMED) & df["종가"].notna()
    ok = df["확정"]
    df.loc[ok, "보유주식수"] = (df.loc[ok, "평가액_억"] * 1e8 / df.loc[ok, "종가"]).round()
    df.loc[ok, "지분율기준_주식수"] = (df.loc[ok, "지분율"] / 100 * df.loc[ok, "상장주식수"]).round()
    df.loc[ok, "역산지분율"] = (df.loc[ok, "보유주식수"] / df.loc[ok, "상장주식수"] * 100).round(3)
    both = ok & (df["지분율기준_주식수"] > 0)
    df["차이율"] = 0.0
    df.loc[both, "차이율"] = (df.loc[both, "보유주식수"] / df.loc[both, "지분율기준_주식수"] - 1).round(4)
    return df


def validate(df: pd.DataFrame, official: float | None) -> list[str]:
    """통과하지 못한 항목 목록. 비어 있으면 통과."""
    errors = []
    total = df["평가액_억"].sum()
    mapped = df.loc[df["확정"], "평가액_억"].sum() / total * 100
    print(f"종목 {len(df):,}개, 합계 {total / 1e4:.2f}조 원, 확정 매핑 {mapped:.2f}%")
    if mapped < MIN_MAPPED_PCT:
        errors.append(f"확정 매핑 비율 {mapped:.2f}% < {MIN_MAPPED_PCT}%")
    if official is None:
        errors.append("공시 국내주식 총액을 찾지 못했습니다")
    else:
        cover = total / 1e4 / official * 100
        print(f"공시 총액 {official:.3f}조 원 대비 {cover:.2f}%")
        if not COVER_RANGE[0] <= cover <= COVER_RANGE[1]:
            errors.append(f"공시 총액 대비 {cover:.2f}%로 범위 {COVER_RANGE}를 벗어납니다")
    big = df[df["확정"] & (df["평가액_억"] >= CHECK_MIN_EOK) & (df["지분율기준_주식수"] > 0)]
    within = (big["차이율"].abs() <= CHECK_TOL).mean() * 100 if len(big) else 0
    print(f"교차 검증: 평가액 {CHECK_MIN_EOK}억 이상 {len(big)}개 중 차이 {CHECK_TOL:.0%} 이내 {within:.1f}%")
    if within < CHECK_PASS_PCT:
        errors.append(f"교차 검증 통과율 {within:.1f}% < {CHECK_PASS_PCT}%")
    return errors


def trim_daily_after(base_date: str) -> int:
    """기준일 뒤 일별 종가를 지운다. step6이 새 보유 종목으로 다시 받는다."""
    removed = 0
    for f in sorted(config.DAILY_PRICES_DIR.glob("*.csv")):
        d = pd.read_csv(f, dtype=str, encoding="utf-8-sig")
        keep = d[d["basDt"] <= base_date]
        removed += len(d) - len(keep)
        if keep.empty:
            f.unlink()
        elif len(keep) != len(d):
            keep.to_csv(f, index=False, encoding="utf-8-sig")
    return removed


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, help="적용할 공시 연도 (없으면 홈페이지의 최신 연도)")
    args = ap.parse_args()

    known = {b.year for b in bases.list_bases()}
    files = available_files()
    if not files:
        raise SystemExit("홈페이지에서 투자종목 다운로드 버튼을 찾지 못했습니다. 화면이 바뀐 것 같습니다.")
    year = args.year or max(files)
    if year in known or (not args.year and known and year < max(known)):
        print(f"새 연말 공시 없음 (홈페이지 최신 {max(files)}년, 적용된 기준 {sorted(known)})")
        return
    if year not in files:
        raise SystemExit(f"{year}년 파일이 홈페이지에 없습니다. 있는 연도: {sorted(files)}")

    print(f"새 연말 공시 발견: {year}년")
    res = nps_http.fetch("GET", files[year], timeout=60)
    if not res.content.startswith(b"PK"):
        raise SystemExit(f"{year}년 파일이 엑셀 형식이 아닙니다.")
    hold = parse_holdings(read_sheet(res.content), year)
    base_date, prices = last_trading_day(year)
    print(f"{year}년 마지막 거래일: {base_date}")

    df = build_shares(hold, prices)
    errors = validate(df, official_total(year))
    if errors:
        unmatched = df[~df["확정"]].sort_values("평가액_억", ascending=False)
        print("확정되지 않은 종목 (평가액 상위 15개):")
        print(unmatched[["종목명", "평가액_억", "매핑방식"]].head(15).to_string(index=False))
        raise SystemExit(f"검증 실패로 {year}년 공시를 적용하지 않았습니다: " + "; ".join(errors))

    removed = trim_daily_after(base_date)  # 기준 파일보다 먼저 지워야 중간에 끊겨도 다음 실행이 다시 처리한다
    out = df[df["확정"]].copy()
    out["보유주식수"] = out["보유주식수"].astype("int64")
    out["지분율기준_주식수"] = out["지분율기준_주식수"].astype("int64")
    cols = ["번호", "종목명", "종목코드", "시장", "평가액_억", "종가", "보유주식수",
            "지분율", "역산지분율", "상장주식수", "지분율기준_주식수", "차이율"]
    folder = config.BASES_DIR / str(year)
    folder.mkdir(parents=True, exist_ok=True)
    prices.to_csv(folder / "prices.csv", index=False, encoding="utf-8-sig")
    out[cols].to_csv(folder / "shares.csv", index=False, encoding="utf-8-sig")
    print(f"적용: {folder} (종목 {len(out):,}개). 기준일 뒤 일별 종가 {removed:,}행을 지웠습니다. step6이 다시 받습니다.")


if __name__ == "__main__":
    main()
