"""연말 마지막 거래일(config.PRICE_DATE, 12월 30일) 전 종목의 종가를 받아 data/prices_20251230.csv로 저장한다.

    python fetch_prices.py

우선주를 포함한 전체 종목이 들어 있어서, 종목코드 매핑의 보조 이름표와
5단계(보유 주식 수 계산)의 기준 종가로 함께 쓴다.
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
    rows = krx_api.fetch_all(config.STOCK_PRICE_URL, {"basDt": config.PRICE_DATE})
    if not rows:
        raise SystemExit("결과가 비어 있습니다. 기준일(휴장일 여부)과 요청 주소를 확인하세요.")
    df = pd.DataFrame(rows)
    config.DATA.mkdir(parents=True, exist_ok=True)
    df.to_csv(config.PRICES_CSV, index=False, encoding="utf-8-sig")
    print(f"{len(df):,}건 저장: {config.PRICES_CSV}")
    print("컬럼:", list(df.columns))
    print(df.head().to_string(index=False))


if __name__ == "__main__":
    main()
