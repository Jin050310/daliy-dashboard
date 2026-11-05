"""그날(Asia/Seoul) 실제로 API를 호출해 일별 기록을 저장한다.

    python record_daily.py

입력: 공공데이터포털 주식시세정보 API, data/daily_value.csv (step7 결과)
출력: data/source_records/YYYY-MM-DD.csv (API 응답 원본 전체), data/daily_record.csv (일별 기록)

규칙 (과제 공개 계약 normalized-reading 형식):
- 같은 signal_id + record_date면 새 행 없이 같은 행을 갱신한다. record_id와 first_fetched_at은 유지한다.
- 다음 Asia/Seoul 날짜의 성공 조회는 새 행을 만든다. 기록은 지우지 않는다.
- 실패하면 아무것도 쓰지 않는다. 마지막 정상값이 그대로 남는다.
- 인증키는 주소·원본·기록 어디에도 남기지 않는다(주소는 쿼리 없는 경로만 적는다).
"""
import hashlib
import math
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit

import pandas as pd

import config
import krx_api

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

KST = timezone(timedelta(hours=9), "Asia/Seoul")
LOOKBACK_DAYS = 10  # 긴 연휴까지 거슬러 올라가 게시된 최신 거래일을 찾는다
CLOSE_TIME = "15:30:00+09:00"  # API는 거래일만 주므로, 원천 관측 시각은 그 거래일의 장 마감 시각으로 적는다

SIGNAL_ID = "nps-domestic-equity-value"
UNIT = "조 원"
SOURCE_NAME = "금융위원회 주식시세정보(공공데이터포털)로 평가한 국민연금 국내주식 공시 보유분"

READING_KEYS = ["signal_id", "normalized_value", "unit", "source_name", "source_url",
                "source_time", "fetched_at", "record_timezone", "record_date"]
EXTRA_KEYS = ["trade_date", "response_rows", "raw_file", "raw_sha256", "holdings_source_url", "holdings_as_of"]
COLS = ["record_id", "signal_id", "record_date", "normalized_value", "unit", "source_name", "source_url",
        "source_time", "first_fetched_at", "last_fetched_at", "record_timezone"] + EXTRA_KEYS


def validate(reading: dict) -> None:
    """normalized-reading 형식이 아니면 ValueError를 낸다."""
    if sorted(reading) != sorted(READING_KEYS):
        raise ValueError("항목이 형식과 다릅니다")
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]*", str(reading["signal_id"])) or len(reading["signal_id"]) > 100:
        raise ValueError("signal_id가 잘못됐습니다")
    value = reading["normalized_value"]
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("normalized_value는 유한한 숫자여야 합니다")
    for field in ("unit", "source_name"):
        if not isinstance(reading[field], str) or not reading[field].strip():
            raise ValueError(f"{field}가 비어 있습니다")
    if urlsplit(str(reading["source_url"])).scheme != "https":
        raise ValueError("source_url은 HTTPS여야 합니다")
    if reading["source_time"] is not None:
        datetime.fromisoformat(reading["source_time"].replace("Z", "+00:00"))
    fetched = datetime.fromisoformat(str(reading["fetched_at"]).replace("Z", "+00:00"))
    if reading["record_timezone"] != "Asia/Seoul":
        raise ValueError("record_timezone은 Asia/Seoul이어야 합니다")
    if reading["record_date"] != fetched.astimezone(KST).strftime("%Y-%m-%d"):
        raise ValueError("record_date는 fetched_at의 Asia/Seoul 날짜여야 합니다")


def apply_reading(rows: list[dict], reading: dict, extra: dict | None = None) -> list[dict]:
    """정상 조회 한 건을 반영한 새 행 목록을 돌려준다. 같은 날짜면 같은 행을 갱신한다."""
    validate(reading)
    existing = next((r for r in rows if r["signal_id"] == reading["signal_id"]
                     and r["record_date"] == reading["record_date"]), None)
    row = {k: reading[k] for k in READING_KEYS if k != "fetched_at"}
    row["record_id"] = existing["record_id"] if existing else f"{reading['signal_id']}-{reading['record_date']}"
    row["first_fetched_at"] = existing["first_fetched_at"] if existing else reading["fetched_at"]
    row["last_fetched_at"] = reading["fetched_at"]
    row.update({k: (extra or {}).get(k, "") for k in EXTRA_KEYS})
    others = [r for r in rows if r is not existing]
    return sorted(others + [row], key=lambda r: r["record_date"])


def load_rows() -> list[dict]:
    if not config.DAILY_RECORD_CSV.exists():
        return []
    return pd.read_csv(config.DAILY_RECORD_CSV, dtype=str, encoding="utf-8-sig", keep_default_na=False).to_dict("records")


def replace_file(path, write) -> None:
    """임시 파일에 다 쓴 뒤 한 번에 바꾼다. 중간에 끊겨도 기존 파일이 깨지지 않는다."""
    tmp = path.with_name(path.name + ".tmp")
    write(tmp)
    os.replace(tmp, path)


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
    krx_api.fail("schema_error", f"최근 {LOOKBACK_DAYS}일의 API 응답이 비어 있어 기록하지 않습니다.")


def record(now: datetime | None = None) -> list[dict]:
    """API를 호출해 오늘 기록을 만들거나 갱신하고, 전체 기록을 돌려준다."""
    now = (now or datetime.now(KST)).astimezone(KST)
    record_date = now.strftime("%Y-%m-%d")
    trade_day, api_rows = fetch_latest(now)

    values = pd.read_csv(config.DAILY_VALUE_CSV, dtype=str, encoding="utf-8-sig", keep_default_na=False)
    match = values[values["basDt"] == trade_day]
    if match.empty:
        krx_api.fail("schema_error", f"거래일 {trade_day}의 평가액이 daily_value.csv에 없어 기록하지 않습니다.")
    value = match.iloc[-1]

    trade_iso = f"{trade_day[:4]}-{trade_day[4:6]}-{trade_day[6:]}"
    reading = {
        "signal_id": SIGNAL_ID, "normalized_value": float(value["평가액_조"]), "unit": UNIT,
        "source_name": SOURCE_NAME, "source_url": config.STOCK_PRICE_URL,
        "source_time": f"{trade_iso}T{CLOSE_TIME}", "fetched_at": now.isoformat(timespec="seconds"),
        "record_timezone": "Asia/Seoul", "record_date": record_date,
    }
    config.SOURCE_RECORDS_DIR.mkdir(parents=True, exist_ok=True)
    source = config.SOURCE_RECORDS_DIR / f"{record_date}.csv"
    raw = pd.DataFrame(api_rows)
    tmp_raw = source.with_name(source.name + ".tmp")
    raw.to_csv(tmp_raw, index=False, encoding="utf-8-sig", lineterminator="\n")
    extra = {
        "trade_date": trade_iso, "response_rows": str(len(api_rows)),
        "raw_file": f"source_records/{source.name}", "raw_sha256": hashlib.sha256(tmp_raw.read_bytes()).hexdigest(),
        "holdings_source_url": config.HOLDINGS_PAGE_URL, "holdings_as_of": f"{value['보유기준연도']}-12-31",
    }
    try:
        rows = apply_reading(load_rows(), reading, extra)
    except ValueError as e:
        tmp_raw.unlink(missing_ok=True)
        krx_api.fail("schema_error", f"형식 검사 실패: {e}")
    os.replace(tmp_raw, source)
    replace_file(config.DAILY_RECORD_CSV,
                 lambda p: pd.DataFrame(rows, columns=COLS).to_csv(p, index=False, encoding="utf-8-sig"))
    print(f"{record_date} 기록: 거래일 {trade_iso}, 응답 {len(api_rows):,}건, {reading['normalized_value']} {UNIT} (전체 {len(rows)}건)")
    return rows


if __name__ == "__main__":
    record()
