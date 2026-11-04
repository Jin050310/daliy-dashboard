"""기준일(config.BASE_DATE)의 KRX 상장 종목 목록을 받아 data/listed_20251230.csv로 저장한다.

    python fetch_listed.py
"""
import sys

import pandas as pd

import config
import krx_api

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def main() -> None:
    rows = krx_api.fetch_all(config.KRX_LISTED_URL, {"basDt": config.BASE_DATE})
    if not rows:
        raise SystemExit("결과가 비어 있습니다. 기준일(휴장일 여부)과 요청 주소를 확인하세요.")
    df = pd.DataFrame(rows)
    config.DATA.mkdir(parents=True, exist_ok=True)
    df.to_csv(config.LISTED_CSV, index=False, encoding="utf-8-sig")
    print(f"{len(df):,}건 저장: {config.LISTED_CSV}")
    print("컬럼:", list(df.columns))
    print(df.head().to_string(index=False))


if __name__ == "__main__":
    main()
