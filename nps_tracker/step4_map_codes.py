"""4단계: 국민연금 보유 종목명을 종목코드(단축코드)로 연결한다.

    python step4_map_codes.py

입력: data/holdings_clean.csv (step1), data/listed_20251230.csv (fetch_listed.py)
      data/manual_map.csv (선택) - 사람이 확인한 매핑. 컬럼: 종목명,종목코드
출력: data/mapping.csv, data/mapping_review.csv(사람이 확인할 목록)

매핑 순서: 수동 -> 이름 완전 일치 -> 정리 후 일치 -> (괄호 특수항목) -> 비슷한 이름 후보 -> 미매칭
"""
import difflib
import re
import sys
import unicodedata

import pandas as pd

import config

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

NAME_COLS = ["itmsNm", "종목명", "name"]
CODE_COLS = ["srtnCd", "단축코드", "code"]
MKT_COLS = ["mrktCtg", "시장구분", "market"]

CONFIRMED = {"manual", "exact", "normalized"}  # 확정으로 보는 방식


def pick(df: pd.DataFrame, candidates: list[str], label: str, required: bool = True):
    for c in candidates:
        if c in df.columns:
            return c
    if required:
        raise SystemExit(f"상장목록에서 {label} 컬럼을 찾지 못했습니다. 현재 컬럼: {list(df.columns)}")
    return None


def normalize(s: str) -> str:
    """공백·대소문자·기호를 정리한 비교용 이름."""
    s = unicodedata.normalize("NFKC", str(s)).upper()
    return re.sub(r"[\s\-_.·,&'\"/]+", "", s)


def clean_code(x) -> str:
    c = str(x).strip()
    if len(c) == 7 and c.startswith("A"):  # 'A005930' 형식 대비
        c = c[1:]
    return c.zfill(6) if c.isdigit() else c


def build_index(listed: pd.DataFrame):
    name_col, code_col, mkt_col = "_name", "_code", "_mkt"
    exact: dict[str, set] = {}
    norm: dict[str, set] = {}
    market: dict[str, str] = {}
    for _, r in listed.iterrows():
        name = str(r[name_col]).strip()
        code = clean_code(r[code_col])
        exact.setdefault(name, set()).add(code)
        norm.setdefault(normalize(name), set()).add(code)
        market[code] = str(r[mkt_col]) if mkt_col else ""
    return exact, norm, market


def load_manual() -> dict[str, str]:
    if not config.MANUAL_MAP_CSV.exists():
        return {}
    m = pd.read_csv(config.MANUAL_MAP_CSV, dtype=str, encoding="utf-8-sig")
    return {str(a).strip(): clean_code(b) for a, b in zip(m["종목명"], m["종목코드"])}


def match_one(name, exact, norm, norm_keys, manual):
    """(코드, 방식, 후보문자열)"""
    if name in manual:
        return manual[name], "manual", ""
    codes = exact.get(name)
    if codes:
        if len(codes) == 1:
            return next(iter(codes)), "exact", ""
        return "", "ambiguous", ",".join(sorted(codes))
    n = normalize(name)
    codes = norm.get(n)
    if codes:
        if len(codes) == 1:
            return next(iter(codes)), "normalized", ""
        return "", "ambiguous", ",".join(sorted(codes))
    if re.search(r"[()]", name):  # 한온시스템(유상) 같은 특수 항목은 자동 매핑하지 않는다
        return "", "special", ""
    close = difflib.get_close_matches(n, norm_keys, n=3, cutoff=0.75)
    if close:
        cands = [f"{c}:{','.join(sorted(norm[c]))}" for c in close]
        return "", "review", " | ".join(cands)
    return "", "unmatched", ""


def main() -> None:
    for p in (config.HOLDINGS_CLEAN, config.LISTED_CSV):
        if not p.exists():
            raise SystemExit(f"파일이 없습니다: {p} (먼저 step1, fetch_listed를 실행하세요)")
    hold = pd.read_csv(config.HOLDINGS_CLEAN, encoding="utf-8-sig")
    sources = [pd.read_csv(config.LISTED_CSV, dtype=str, encoding="utf-8-sig")]
    if config.PRICES_CSV.exists():  # 우선주까지 들어 있는 시세 목록을 보조 이름표로 쓴다
        sources.append(pd.read_csv(config.PRICES_CSV, dtype=str, encoding="utf-8-sig"))
    parts = []
    for df in sources:
        n, c = pick(df, NAME_COLS, "종목명"), pick(df, CODE_COLS, "종목코드")
        m = pick(df, MKT_COLS, "시장구분", required=False)
        parts.append(pd.DataFrame({"_name": df[n], "_code": df[c], "_mkt": df[m] if m else ""}))
    listed = pd.concat(parts, ignore_index=True).drop_duplicates()
    exact, norm, market = build_index(listed)
    norm_keys = list(norm.keys())
    manual = load_manual()

    results = [match_one(n, exact, norm, norm_keys, manual) for n in hold["종목명"]]
    hold["종목코드"] = [r[0] for r in results]
    hold["매핑방식"] = [r[1] for r in results]
    hold["후보"] = [r[2] for r in results]
    hold["시장"] = hold["종목코드"].map(market).fillna("")

    out_cols = ["번호", "종목명", "평가액_억", "지분율", "종목코드", "시장", "매핑방식", "후보"]
    hold[out_cols].to_csv(config.MAPPING_CSV, index=False, encoding="utf-8-sig")

    review = hold[~hold["매핑방식"].isin(CONFIRMED)]
    review[out_cols].to_csv(config.MAPPING_REVIEW_CSV, index=False, encoding="utf-8-sig")

    total = hold["평가액_억"].sum()
    print("=== 매핑 결과 ===")
    summary = hold.groupby("매핑방식")["평가액_억"].agg(["count", "sum"])
    summary["비율%"] = (summary["sum"] / total * 100).round(3)
    print(summary.rename(columns={"count": "종목수", "sum": "평가액(억)"}).to_string())

    ok = hold.loc[hold["매핑방식"].isin(CONFIRMED), "평가액_억"].sum()
    rate = ok / total * 100
    print(f"\n확정 매핑 평가액 비율: {rate:.2f}%  (목표 99.5% 이상)")
    if rate < 99.5:
        print("-> data/mapping_review.csv를 열어 확인한 뒤 data/manual_map.csv에 추가하고 다시 실행하세요.")

    print("\n확인이 필요한 종목 중 평가액 상위 20개:")
    top = review.sort_values("평가액_억", ascending=False).head(20)
    print(top[["종목명", "평가액_억", "매핑방식", "후보"]].to_string(index=False))
    print(f"\n저장: {config.MAPPING_CSV}\n저장: {config.MAPPING_REVIEW_CSV}")


if __name__ == "__main__":
    main()
