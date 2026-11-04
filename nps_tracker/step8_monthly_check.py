"""8단계: 국민연금이 공시한 월말 국내주식 평가액과 비교한다.

    python step8_monthly_check.py

입력: data/daily_value.csv (step7), config.OFFICIAL_MONTHLY
출력: data/monthly_check.csv

이 지표는 2025년 말 보유분을 그대로 들고 있다고 가정하므로, 공시값과의 차이는
- 2025년 말 이후 국민연금의 실제 매매(순매수·순매도, 종목 교체)
- 공시 범위 차이(목록 밖 자산, 기준일 차이 등)
를 합친 것이다. 기준일(2025년 말)에도 이미 차이(커버율)가 있으므로, 그 기준 차이를 뺀
'기준 대비 추가 차이'를 매매 효과의 대략적인 크기로 본다.
"""
import sys

import pandas as pd

import config

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def main() -> None:
    if not config.DAILY_VALUE_CSV.exists():
        raise SystemExit(f"파일이 없습니다: {config.DAILY_VALUE_CSV} (먼저 step7을 실행하세요)")
    v = pd.read_csv(config.DAILY_VALUE_CSV, dtype={"basDt": str}, encoding="utf-8-sig")

    rows = []
    for ym, official, src, trust in config.OFFICIAL_MONTHLY:
        month_days = v[v["basDt"].str[:6] == ym]
        if month_days.empty:
            continue
        last = month_days.iloc[-1]  # 그 달의 마지막 거래일
        rows.append({
            "월": ym, "기준거래일": last["basDt"], "추적값_조": round(last["평가액_조"], 2),
            "공시값_조": official, "커버율_%": round(last["평가액_조"] / official * 100, 2),
            "신뢰": trust, "출처": src,
        })
    df = pd.DataFrame(rows)
    if df.empty or df.iloc[0]["월"] != "202512":
        raise SystemExit("2025년 12월 공시값(기준)이 없습니다. config.OFFICIAL_MONTHLY를 확인하세요.")

    base_cover = df.iloc[0]["커버율_%"]
    df["기준대비_추가차이_%p"] = (df["커버율_%"] - base_cover).round(2)
    # 추적값이 공시값보다 작으면(커버율 하락) 2025년 말 이후 순매수, 크면 순매도 쪽으로 해석한다
    df["매매효과_추정_조"] = (df["공시값_조"] * base_cover / 100 - df["추적값_조"]).round(1)
    df.to_csv(config.MONTHLY_CHECK_CSV, index=False, encoding="utf-8-sig")

    print("=== 월별 검증: 추적값(2025년 말 보유분 고정) vs 국민연금 공시 ===")
    show = ["월", "기준거래일", "추적값_조", "공시값_조", "커버율_%", "기준대비_추가차이_%p", "매매효과_추정_조", "신뢰"]
    print(df[show].to_string(index=False))

    print(f"\n기준(2025년 12월) 커버율: {base_cover:.2f}%")
    off = df[(df["신뢰"] == "공식") & (df["월"] != "202512")]
    if not off.empty:
        worst = off.loc[off["기준대비_추가차이_%p"].abs().idxmax()]
        print(f"공식 값 기준 추가 차이 범위: {off['기준대비_추가차이_%p'].min():+.2f} ~ "
              f"{off['기준대비_추가차이_%p'].max():+.2f}%p (가장 큰 달 {worst['월']})")
        print("-> 매매효과_추정_조 > 0: 2025년 말 이후 국내주식을 순매수했거나 오른 종목 비중을 늘린 효과")
        print("   매매효과_추정_조 < 0: 순매도했거나 비중을 줄인 효과 (시장 변동과 섞여 있으므로 대략적인 크기로만 볼 것)")
    print(f"\n저장: {config.MONTHLY_CHECK_CSV}")


if __name__ == "__main__":
    main()
