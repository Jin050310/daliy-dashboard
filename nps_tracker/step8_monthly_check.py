"""8단계: 국민연금이 공시한 월말 국내주식 평가액과 비교한다.

    python step8_monthly_check.py

입력: data/daily_value.csv (step7), config.OFFICIAL_MONTHLY, data/official_monthly.csv (fetch_official, 같은 달이면 우선)
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


def official_list() -> list[tuple]:
    """수동 목록에 자동 수집 값을 덮어쓴 (월, 금액, 출처, 신뢰) 목록."""
    merged = {ym: (ym, val, src, trust) for ym, val, src, trust in config.OFFICIAL_MONTHLY}
    if config.OFFICIAL_AUTO_CSV.exists():
        auto = pd.read_csv(config.OFFICIAL_AUTO_CSV, dtype={"월": str}, encoding="utf-8-sig")
        for _, r in auto.iterrows():
            merged[r["월"]] = (r["월"], float(r["공시값_조"]), r["출처"], "공식")
    return [merged[k] for k in sorted(merged)]


def main() -> None:
    if not config.DAILY_VALUE_CSV.exists():
        raise SystemExit(f"파일이 없습니다: {config.DAILY_VALUE_CSV} (먼저 step7을 실행하세요)")
    v = pd.read_csv(config.DAILY_VALUE_CSV, dtype={"basDt": str}, encoding="utf-8-sig")

    officials = official_list()
    amount = {ym: val for ym, val, _, _ in officials}
    rows = []
    for ym, official, src, trust in officials:
        month_days = v[v["basDt"].str[:6] == ym]
        if month_days.empty:
            continue
        last = month_days.iloc[-1]  # 그 달의 마지막 거래일
        # 그 날 적용 중인 보유 기준의 출발 커버율. 그 해 말 공시값이 없으면 비교하지 않는다
        base_official = amount.get(f"{last['보유기준연도']}12")
        base_cover = last["기준평가액_조"] / base_official * 100 if base_official else None
        cover = last["평가액_조"] / official * 100
        rows.append({
            "월": ym, "기준거래일": last["basDt"], "보유기준연도": last["보유기준연도"],
            "추적값_조": round(last["평가액_조"], 2),
            "공시값_조": official, "커버율_%": round(cover, 2),
            # 추적값이 공시값보다 작으면(커버율 하락) 기준일 이후 순매수, 크면 순매도 쪽으로 해석한다
            "기준대비_추가차이_%p": round(cover - base_cover, 2) if base_cover else None,
            "매매효과_추정_조": round(official * base_cover / 100 - last["평가액_조"], 1) if base_cover else None,
            "신뢰": trust, "출처": src,
        })
    df = pd.DataFrame(rows)
    if df.empty:
        raise SystemExit("비교할 공시값이 없습니다. config.OFFICIAL_MONTHLY나 fetch_official을 확인하세요.")
    df.to_csv(config.MONTHLY_CHECK_CSV, index=False, encoding="utf-8-sig")

    print("=== 월별 검증: 추적값(연말 공시 보유분 고정) vs 국민연금 공시 ===")
    show = ["월", "기준거래일", "보유기준연도", "추적값_조", "공시값_조", "커버율_%", "기준대비_추가차이_%p", "매매효과_추정_조", "신뢰"]
    print(df[show].to_string(index=False))

    off = df[(df["신뢰"] == "공식") & (df["기준대비_추가차이_%p"].fillna(0) != 0)]
    if not off.empty:
        worst = off.loc[off["기준대비_추가차이_%p"].abs().idxmax()]
        print(f"공식 값 기준 추가 차이 범위: {off['기준대비_추가차이_%p'].min():+.2f} ~ "
              f"{off['기준대비_추가차이_%p'].max():+.2f}%p (가장 큰 달 {worst['월']})")
        print("-> 매매효과_추정_조 > 0: 기준일 이후 국내주식을 순매수했거나 오른 종목 비중을 늘린 효과")
        print("   매매효과_추정_조 < 0: 순매도했거나 비중을 줄인 효과 (시장 변동과 섞여 있으므로 대략적인 크기로만 볼 것)")
    print(f"\n저장: {config.MONTHLY_CHECK_CSV}")


if __name__ == "__main__":
    main()
