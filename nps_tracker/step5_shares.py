"""5단계: 종목별 보유 주식 수를 계산한다.

    python step5_shares.py

입력: data/mapping.csv (step4), data/prices_20251230.csv (fetch_prices.py)
출력: data/shares.csv

공시에는 평가액만 있고 주식 수가 없으므로, 연말 마지막 거래일(12/30) 종가로 역산한다.
    보유주식수 = 평가액(원) / 12월 30일 종가
교차 검증으로 '공시 지분율 x 상장주식수'와 비교한다. 평가액은 억 원 단위로 반올림되어 있고
지분율은 소수 둘째 자리까지라, 작은 종목일수록 두 값의 차이가 커지는 것은 정상이다.
"""
import sys

import pandas as pd

import config

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

CHECK_MIN_EOK = 100  # 이 금액(억) 이상인 종목만 교차 검증 경고를 띄운다 (작은 종목은 반올림 오차가 큼)
CHECK_TOL = 0.05     # 두 방식의 차이가 5%를 넘으면 경고


def main() -> None:
    for p in (config.MAPPING_CSV, config.PRICES_CSV):
        if not p.exists():
            raise SystemExit(f"파일이 없습니다: {p} (먼저 step4, fetch_prices를 실행하세요)")
    m = pd.read_csv(config.MAPPING_CSV, dtype={"종목코드": str}, encoding="utf-8-sig")
    prices = pd.read_csv(config.PRICES_CSV, dtype=str, encoding="utf-8-sig")
    prices = prices[["srtnCd", "clpr", "lstgStCnt"]].rename(
        columns={"srtnCd": "종목코드", "clpr": "종가", "lstgStCnt": "상장주식수"}
    )
    prices["종가"] = pd.to_numeric(prices["종가"])
    prices["상장주식수"] = pd.to_numeric(prices["상장주식수"])

    mapped = m[m["매핑방식"].isin(["manual", "exact", "normalized"])].copy()
    skipped = m[~m.index.isin(mapped.index)]
    df = mapped.merge(prices, on="종목코드", how="left")
    no_price = df[df["종가"].isna()]
    if not no_price.empty:
        print(f"주의: 12/30 종가가 없는 종목 {len(no_price)}개 (제외):")
        print(no_price[["종목명", "종목코드", "평가액_억"]].to_string(index=False))
    df = df[df["종가"].notna()].copy()

    df["보유주식수"] = (df["평가액_억"] * 1e8 / df["종가"]).round().astype("int64")
    df["지분율기준_주식수"] = (df["지분율"] / 100 * df["상장주식수"]).round().astype("int64")
    df["역산지분율"] = (df["보유주식수"] / df["상장주식수"] * 100).round(3)
    both = df["지분율기준_주식수"] > 0
    df["차이율"] = 0.0
    df.loc[both, "차이율"] = (df.loc[both, "보유주식수"] / df.loc[both, "지분율기준_주식수"] - 1).round(4)

    out_cols = ["번호", "종목명", "종목코드", "시장", "평가액_억", "종가", "보유주식수",
                "지분율", "역산지분율", "상장주식수", "지분율기준_주식수", "차이율"]
    df[out_cols].to_csv(config.SHARES_CSV, index=False, encoding="utf-8-sig")

    total = m["평가액_억"].sum()
    covered = df["평가액_억"].sum()
    print("=== 보유 주식 수 계산 ===")
    print(f"계산한 종목: {len(df):,}개, 평가액 {covered:,}억 ({covered / total * 100:.2f}%)")
    print(f"제외한 종목: {len(skipped) + len(no_price)}개 (특수 항목·미매핑·종가 없음)")

    # 기준일 재평가 합계는 평가액을 종가로 나눴다 곱한 것이므로 반올림 오차만 남아야 한다
    revalued = (df["보유주식수"] * df["종가"]).sum() / 1e8
    print(f"12/30 종가 x 보유주식수 합계: {revalued:,.0f}억 (공시 평가액과 차이 {revalued - covered:+,.0f}억)")

    print("\n=== 교차 검증 (평가액 역산 vs 공시 지분율) ===")
    big = df[(df["평가액_억"] >= CHECK_MIN_EOK) & both]
    within = (big["차이율"].abs() <= CHECK_TOL).sum()
    print(f"평가액 {CHECK_MIN_EOK}억 이상 {len(big)}개 중 차이 {CHECK_TOL:.0%} 이내: {within}개")
    print(f"차이율 중앙값: {big['차이율'].median():+.2%}")
    bad = big[big["차이율"].abs() > CHECK_TOL].sort_values("평가액_억", ascending=False)
    if bad.empty:
        print("-> 큰 차이가 나는 종목이 없습니다.")
    else:
        print(f"-> 차이가 {CHECK_TOL:.0%}를 넘는 종목 (평가액 상위 20개):")
        print(bad[["종목명", "평가액_억", "지분율", "역산지분율", "차이율"]].head(20).to_string(index=False))

    print(f"\n저장: {config.SHARES_CSV}")


if __name__ == "__main__":
    main()
