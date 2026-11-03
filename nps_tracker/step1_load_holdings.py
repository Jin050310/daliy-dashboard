"""1~3단계: 국민연금 연말 보유 CSV를 읽어 정리하고 합계·커버율·집중도를 점검한다.

API 없이 실행된다.
    python step1_load_holdings.py
결과: data/holdings_clean.csv
"""
import re
import sys

import pandas as pd

import config

COLS = ["번호", "종목명", "평가액_억", "비중", "지분율"]

try:  # 윈도우 터미널에서 한글이 깨지지 않게
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def load_raw() -> pd.DataFrame:
    if not config.RAW_CSV.exists():
        raise SystemExit(f"파일이 없습니다: {config.RAW_CSV}")
    df = pd.read_csv(config.RAW_CSV, encoding=config.CSV_ENCODING)
    if df.shape[1] != 5:
        raise SystemExit(f"컬럼이 5개여야 하는데 {df.shape[1]}개입니다.")
    df.columns = COLS
    df["종목명"] = df["종목명"].astype(str).str.strip()
    return df


def add_flags(df: pd.DataFrame) -> pd.DataFrame:
    total = df["평가액_억"].sum()
    df = df.copy()
    df["누적비율"] = (df["평가액_억"].cumsum() / total * 100).round(3)
    df["소형(10억미만)"] = df["평가액_억"] < 10
    df["지분율0"] = df["지분율"] <= 0
    df["괄호항목"] = df["종목명"].str.contains(r"[()]", regex=True)
    # 우선주로 보이는 이름 (참고용 표시일 뿐 판정은 매핑 단계에서 한다)
    df["우선주추정"] = df["종목명"].str.contains(r"\d?우(?:[ABC])?$|우\(", regex=True)
    return df


def report(df: pd.DataFrame) -> None:
    total_eok = df["평가액_억"].sum()
    total_jo = total_eok / 10000
    print("=== 기본 현황 ===")
    print(f"종목 수: {len(df):,}")
    print(f"평가액 합계: {total_eok:,}억 원 = {total_jo:,.2f}조 원")
    print(f"비중 합계: {df['비중'].sum():.2f}% (100%보다 작은 만큼은 목록 밖 자산)")
    if df["종목명"].duplicated().any():
        print("주의: 종목명이 중복된 행이 있습니다.")

    print("\n=== 커버율 (3단계) ===")
    cover = total_jo / config.OFFICIAL_TOTAL_JO * 100
    print(f"공시 국내주식 평가액 {config.OFFICIAL_TOTAL_JO:.1f}조 원 대비: {cover:.1f}%")
    if cover < 95 or cover > 105:
        print("-> 크게 어긋납니다. 구조를 다시 생각해야 합니다.")
    else:
        print("-> 계속 진행해도 됩니다. (OFFICIAL_TOTAL_JO를 정확한 값으로 바꿔 다시 확인하세요.)")

    print("\n=== 집중도 ===")
    print(f"상위 2종목 비중: {df['비중'].head(2).sum():.1f}%")
    print(f"상위 10종목 비중: {df['비중'].head(10).sum():.1f}%")
    for p in (50, 80, 90, 95, 99):
        n = int((df["누적비율"] < p).sum()) + 1
        print(f"누적 {p}%에 도달하는 종목 수: {n}")

    print("\n=== 데이터 품질 ===")
    print(f"평가액 0억 원 종목: {(df['평가액_억'] <= 0).sum()}개")
    small = df["소형(10억미만)"]
    print(f"평가액 10억 원 미만 종목: {small.sum()}개 (합계 {df.loc[small, '평가액_억'].sum():,}억 원)")
    print(f"지분율 0.00인 종목: {df['지분율0'].sum()}개")
    print(f"괄호가 붙은 특수 항목: {df['괄호항목'].sum()}개")
    print(f"우선주로 보이는 항목: {df['우선주추정'].sum()}개")
    print("\n지분율 0인 종목:")
    print(df.loc[df["지분율0"], ["종목명", "평가액_억", "지분율"]].to_string(index=False))


def main() -> None:
    df = add_flags(load_raw())
    report(df)
    config.DATA.mkdir(parents=True, exist_ok=True)
    df.to_csv(config.HOLDINGS_CLEAN, index=False, encoding="utf-8-sig")
    print(f"\n저장: {config.HOLDINGS_CLEAN}")


if __name__ == "__main__":
    main()
