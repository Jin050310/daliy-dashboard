"""6단계: 보유 종목의 일별 종가를 모은다.

    python step6_daily_prices.py

입력: 현재 보유 기준 (bases.py)
출력: data/daily/YYYYMM.csv (basDt, srtnCd, itmsNm, clpr, lstgStCnt)

- 첫 보유 기준일 다음 날부터 어제까지 평일마다 하루치 전 종목을 한 번에 받는다(호출 1회/일).
- 이미 받은 날짜는 건너뛰므로 매일 다시 실행하면 새 날짜만 추가된다.
- 월별 파일로 나눠 저장하므로 매일 바뀌는 파일은 이번 달 것 하나뿐이다(git 커밋이 작다).
- 휴장일은 결과가 0건이라 저장하지 않는다.
- 종가는 다음 영업일 오후 1시 이후에 올라오므로 어제 값이 아직 없을 수 있다.
- 이 API의 종가는 수정주가가 아니므로, 상장주식수가 크게 바뀐 종목(액면분할·무상증자 후보)을 따로 알려 준다.
"""
import sys
from datetime import date, datetime, timedelta

import pandas as pd

import bases
import config
import krx_api

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

KEEP_COLS = ["basDt", "srtnCd", "itmsNm", "clpr", "lstgStCnt"]
SPLIT_RATIO = 1.3  # 하루 사이 상장주식수가 이 배수 이상 바뀌면 분할·병합·무상증자 후보
SAVE_EVERY = 20    # 이 날짜 수마다 중간 저장 (도중에 끊겨도 받은 만큼은 남는다)


def load_daily() -> pd.DataFrame:
    """data/daily/*.csv를 모두 읽는다. 없으면 빈 표."""
    files = sorted(config.DAILY_PRICES_DIR.glob("*.csv"))
    if not files:
        return pd.DataFrame(columns=KEEP_COLS)
    return pd.concat([pd.read_csv(f, dtype=str, encoding="utf-8-sig") for f in files], ignore_index=True)


def save(parts: list[pd.DataFrame]) -> pd.DataFrame:
    allp = pd.concat(parts, ignore_index=True)
    allp = allp.drop_duplicates(["basDt", "srtnCd"]).sort_values(["basDt", "srtnCd"])
    config.DAILY_PRICES_DIR.mkdir(parents=True, exist_ok=True)
    for ym, grp in allp.groupby(allp["basDt"].str[:6]):
        grp.to_csv(config.DAILY_PRICES_DIR / f"{ym}.csv", index=False, encoding="utf-8-sig")
    return allp


def weekdays(start: str, end: date) -> list[str]:
    d = datetime.strptime(start, "%Y%m%d").date()
    out = []
    while d <= end:
        if d.weekday() < 5:
            out.append(d.strftime("%Y%m%d"))
        d += timedelta(days=1)
    return out


def main() -> None:
    all_bases = bases.list_bases()
    if not all_bases:
        raise SystemExit("보유 기준이 없습니다. 먼저 step5나 roll_year를 실행하세요.")
    sh = all_bases[-1].load_shares()
    held = set(sh["종목코드"])
    held |= {to for _, to, _, _ in config.MERGERS}  # 합병 존속 종목은 보유하지 않았더라도 종가가 필요하다

    old = load_daily()
    have = set(old["basDt"])

    first = datetime.strptime(all_bases[0].date, "%Y%m%d").date() + timedelta(days=1)
    todo = [d for d in weekdays(first.strftime("%Y%m%d"), date.today() - timedelta(days=1)) if d not in have]
    print(f"받을 날짜: {len(todo)}일 (이미 있는 날짜 {len(have)}일)")

    new_parts, holidays = [], []
    for i, d in enumerate(todo, 1):
        rows = krx_api.fetch_all(config.STOCK_PRICE_URL, {"basDt": d}, rows_per_page=5000)
        if not rows:
            holidays.append(d)
            continue
        df = pd.DataFrame(rows)
        new_parts.append(df[df["srtnCd"].isin(held)][KEEP_COLS])
        if i % SAVE_EVERY == 0:
            save([old] + new_parts)
            print(f"  {i}/{len(todo)} ({d}) 중간 저장")
    if holidays:
        print(f"결과 없음(휴장일 또는 아직 미게시): {', '.join(holidays)}")

    allp = save([old] + new_parts)

    days = sorted(allp["basDt"].unique())
    print(f"\n=== 일별 종가 ===")
    print(f"거래일 {len(days)}일: {days[0]} ~ {days[-1]}, 행 {len(allp):,}개")

    last = allp[allp["basDt"] == days[-1]]
    missing = sorted(held - set(last["srtnCd"]))
    if missing:
        lastseen = allp.groupby("srtnCd")["basDt"].max()
        mm = sh[sh["종목코드"].isin(missing)][["종목명", "종목코드", "평가액_억"]].copy()
        mm["마지막_종가일"] = mm["종목코드"].map(lastseen).fillna("없음")
        print(f"\n최근일({days[-1]})에 종가가 없는 보유 종목 {len(mm)}개 (상장폐지·코드변경·거래정지 등):")
        print(mm.sort_values("평가액_억", ascending=False).to_string(index=False))

    # 상장주식수가 하루 사이 크게 바뀐 종목: 액면분할·병합·무상증자 후보
    p = allp.sort_values(["srtnCd", "basDt"]).copy()
    p["clpr"] = pd.to_numeric(p["clpr"])
    p["lstgStCnt"] = pd.to_numeric(p["lstgStCnt"])
    p["주식수배율"] = p["lstgStCnt"] / p.groupby("srtnCd")["lstgStCnt"].shift()
    p["종가배율"] = p["clpr"] / p.groupby("srtnCd")["clpr"].shift()
    ev = p[(p["주식수배율"] >= SPLIT_RATIO) | (p["주식수배율"] <= 1 / SPLIT_RATIO)]
    print(f"\n상장주식수가 하루 사이 {SPLIT_RATIO}배 이상 바뀐 경우: {len(ev)}건 (처리는 step7)")

    print(f"\n저장: {config.DAILY_PRICES_DIR}")


if __name__ == "__main__":
    main()
