"""그날(Asia/Seoul) 실제로 API를 호출하고, 그 응답 원본과 함께 하루 한 건을 기록한다.

    python record_daily.py

입력: 공공데이터포털 주식시세정보 API, data/daily_value.csv (step7 결과)
출력: data/source_records/호출일.csv (API 응답 원본 전체)
      data/daily_record.csv (호출일, 조회시각, 조회_거래일, 응답_건수, 원천파일, 원천파일_sha256, API_주소, 평가액_조, 전일대비_%)

- 오늘 기록이 이미 있으면 API를 부르지 않고 끝낸다. 그날의 첫 성공만 남긴다.
- 오늘 기록이 없으면 반드시 API를 새로 호출한다. 이미 받아 둔 데이터로 기록을 만들지 않는다.
- 호출이 실패하거나 평가액을 맞출 수 없으면 기록을 만들지 않는다. 다음 실행 때 다시 시도한다.
- 조회일이 서로 다른 최근 2건만 남기고, 더 오래된 기록과 그 원본 파일은 지운다(git 기록에는 남는다).
- 인증키는 API 주소·원본·기록 어디에도 남기지 않는다(주소는 쿼리 없는 경로만 적는다).
"""
import hashlib
import sys
from datetime import datetime, timedelta, timezone

import pandas as pd

import config
import krx_api

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

KST = timezone(timedelta(hours=9), "Asia/Seoul")
COLS = ["호출일", "조회시각", "조회_거래일", "응답_건수", "원천파일", "원천파일_sha256", "API_주소", "평가액_조", "전일대비_%"]
LOOKBACK_DAYS = 10  # 긴 연휴까지 거슬러 올라가 게시된 최신 거래일을 찾는다
KEEP_RECORDS = 2    # 보존할 기록 수 (조회일 기준)


def fetch_latest(now: datetime) -> tuple[str, list[dict]]:
    """어제부터 거슬러 올라가 API에 게시된 최신 거래일과 응답 전체를 돌려준다."""
    day = now.date()
    for _ in range(LOOKBACK_DAYS):
        day -= timedelta(days=1)
        if day.weekday() >= 5:
            continue
        ymd = day.strftime("%Y%m%d")
        rows = krx_api.fetch_all(config.STOCK_PRICE_URL, {"basDt": ymd}, rows_per_page=5000)
        if rows:
            return ymd, rows
    raise SystemExit(f"최근 {LOOKBACK_DAYS}일의 API 응답이 비어 있어 기록하지 않습니다.")


def load_records() -> pd.DataFrame:
    """기존 기록을 읽는다. 원천파일이 없는 기록은 조회 증거가 없으므로 무효로 보고 제외한다."""
    path = config.DAILY_RECORD_CSV
    if not path.exists():
        return pd.DataFrame(columns=COLS)
    old = pd.read_csv(path, dtype=str, encoding="utf-8-sig", keep_default_na=False).reindex(columns=COLS, fill_value="")
    return old[old["원천파일"] != ""]


def record(now: datetime | None = None) -> bool:
    """새 기록을 만들었으면 True, 오늘 기록이 이미 있으면 False를 돌려준다."""
    now = now or datetime.now(KST)
    today = now.strftime("%Y%m%d")

    old = load_records()
    if today in set(old["호출일"]):
        print(f"{today} 기록이 이미 있어 그대로 둡니다 (전체 {len(old)}건)")
        return False

    trade_day, rows = fetch_latest(now)

    values = pd.read_csv(config.DAILY_VALUE_CSV, dtype=str, encoding="utf-8-sig", keep_default_na=False)
    match = values[values["basDt"] == trade_day]
    if match.empty:
        raise SystemExit(f"거래일 {trade_day}의 평가액이 daily_value.csv에 없어 기록하지 않습니다. step6·step7을 확인하세요.")
    value = match.iloc[-1]

    config.SOURCE_RECORDS_DIR.mkdir(parents=True, exist_ok=True)
    source = config.SOURCE_RECORDS_DIR / f"{today}.csv"
    pd.DataFrame(rows).to_csv(source, index=False, encoding="utf-8-sig", lineterminator="\n")

    row = {"호출일": today, "조회시각": now.strftime("%Y-%m-%d %H:%M"), "조회_거래일": trade_day,
           "응답_건수": str(len(rows)), "원천파일": f"source_records/{source.name}",
           "원천파일_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
           "API_주소": config.STOCK_PRICE_URL, "평가액_조": value["평가액_조"], "전일대비_%": value["전일대비_%"]}
    out = pd.concat([old, pd.DataFrame([row], columns=COLS)], ignore_index=True).sort_values("호출일").tail(KEEP_RECORDS)
    out.to_csv(config.DAILY_RECORD_CSV, index=False, encoding="utf-8-sig")
    # 새 기록을 저장한 뒤에 지운다. 도중에 끊겨도 기록이 줄어들지 않는다
    kept = {f"{d}.csv" for d in out["호출일"]}
    for f in config.SOURCE_RECORDS_DIR.glob("*.csv"):
        if f.name not in kept:
            f.unlink()
    print(f"{today} 기록 추가: 거래일 {trade_day}, 응답 {len(rows):,}건, {value['평가액_조']}조 (전체 {len(out)}건)")
    return True


if __name__ == "__main__":
    record()
