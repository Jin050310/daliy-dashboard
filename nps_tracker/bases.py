"""연말 공시 보유 기준 목록.

기준 하나 = 어느 해 말 공시 보유분(shares)과 그 해 마지막 거래일의 전 종목 종가(prices).
- 2025년: 처음 손으로 만든 data/shares.csv, data/prices_20251230.csv
- 2026년부터: roll_year.py가 자동으로 만드는 data/bases/YYYY/shares.csv, prices.csv
"""
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

import config


@dataclass(frozen=True)
class Base:
    year: int      # 공시 기준 연도
    date: str      # 그 해 마지막 거래일 (YYYYMMDD)
    shares: Path   # 종목별 보유 주식 수
    prices: Path   # 마지막 거래일 전 종목 종가

    def load_shares(self) -> pd.DataFrame:
        return pd.read_csv(self.shares, dtype={"종목코드": str}, encoding="utf-8-sig")


def list_bases() -> list[Base]:
    """연도순 목록. 마지막이 현재 쓰는 기준이다."""
    out = []
    if config.SHARES_CSV.exists() and config.PRICES_CSV.exists():
        out.append(Base(int(config.PRICE_DATE[:4]), config.PRICE_DATE, config.SHARES_CSV, config.PRICES_CSV))
    for d in sorted(config.BASES_DIR.glob("[0-9][0-9][0-9][0-9]")):
        s, p = d / "shares.csv", d / "prices.csv"
        if s.exists() and p.exists():
            date = pd.read_csv(p, dtype=str, encoding="utf-8-sig", nrows=1)["basDt"].iloc[0]
            out.append(Base(int(d.name), date, s, p))
    return sorted(out, key=lambda b: b.year)
