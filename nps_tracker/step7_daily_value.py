"""7단계: 연말 공시 보유분을 매일 종가로 평가한다.

    python step7_daily_value.py

입력: 보유 기준들 (bases.py), data/daily/*.csv (step6)
출력: data/daily_value.csv (일별 합계), data/share_events.csv (주식 수 변동 사건),
      data/latest_holdings.csv (현재 기준의 종목별 기준일·최근일 평가액)

    일별 평가액 = 보유주식수 x 분할 보정 배수 x 그날 종가

- 연말 공시가 여러 해 있으면 각 공시를 그 해 마지막 거래일 다음 날부터 적용한다. 교체 시점에 합계가
  달라지는 것은 그동안의 실제 매매가 드러난 것이며, 전일 대비는 같은 보유분끼리 비교해 계산한다.
- 이 API 종가는 수정주가가 아니므로 주식 수 변동을 보유주식수에 직접 반영한다.
  - 분할·병합: 상장주식수와 종가가 같은 날 반대로 움직여 서로 상쇄된 경우, 그날 반영한다.
  - 무상증자: 권리락일에 가격이 먼저 떨어지고 신주는 몇 주 뒤 상장된다. 신주 상장일에서
    거슬러 올라가 가격이 그만큼 떨어진 날을 찾으면, 그 권리락일부터 반영한다.
- 주식으로 교부되는 합병(config.MERGERS)은 신주 상장일부터 존속 종목 주식으로 바꿔 평가한다.
- 유상증자처럼 그 밖의 변동은 반영하지 않고 share_events.csv에 남긴다.
- 종가가 끊긴 종목(상장폐지·합병·거래정지)은 마지막 종가로 고정한다.
"""
import sys

import numpy as np
import pandas as pd

import bases
import config

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

EVENT_RATIO = 1.3   # 상장주식수가 하루 사이 이 배수 이상 바뀌면 사건으로 본다
LIMIT_MOVE = 0.3    # 국내 가격제한폭(±30%). 이를 넘는 하루 변동은 보정 누락 의심
BONUS_LOOKBACK = 60  # 무상증자 신주 상장일에서 권리락일을 찾아 거슬러 올라가는 최대 거래일 수
PRICE_COLS = ["basDt", "srtnCd", "itmsNm", "clpr", "lstgStCnt"]


def offsets(sr: float, pr: float) -> bool:
    """가격 변동이 주식 수 변동을 상쇄하는가.

    주식수배율 x 종가배율이 1에 가깝되, 그 차이가 주식 수 변동 폭의 절반 이하이고
    하루 가격제한폭 안이어야 한다. (유상증자 신주 상장처럼 가격이 그대로면 거짓)
    """
    gap = abs(np.log(sr * pr))
    return gap <= min(np.log(1 + LIMIT_MOVE), 0.5 * abs(np.log(sr)))


def find_adjustments(p: pd.DataFrame) -> pd.DataFrame:
    """종목·날짜별 보정배율과 사건 목록을 만든다. p는 srtnCd, basDt 순으로 정렬돼 있어야 한다."""
    p["보정배율"] = 1.0
    events = []
    for code, grp in p.groupby("srtnCd", sort=False):
        idx = grp.index.to_list()
        for k, i in enumerate(idx):
            sr, pr = p.at[i, "주식수배율"], p.at[i, "종가배율"]
            if np.isnan(sr) or (1 / EVENT_RATIO < sr < EVENT_RATIO):
                continue
            row = {"srtnCd": code, "itmsNm": p.at[i, "itmsNm"], "basDt": p.at[i, "basDt"],
                   "주식수배율": sr, "종가배율": pr, "반영일": "", "처리": "미반영(확인 필요)"}
            if offsets(sr, pr):
                p.at[i, "보정배율"] *= sr
                row.update(반영일=row["basDt"], 처리="자동 반영(분할·병합)")
            elif sr > 1:
                # 무상증자: 신주 상장 전에 가격이 1/sr 근처로 떨어진 권리락일을 찾는다
                best = None
                for j in reversed(idx[max(0, k - BONUS_LOOKBACK):k]):
                    pj = p.at[j, "종가배율"]
                    if not np.isnan(pj) and pj < 1 - LIMIT_MOVE + 0.05 and offsets(sr, pj):
                        if best is None or abs(np.log(sr * pj)) < abs(np.log(sr * p.at[best, "종가배율"])):
                            best = j
                if best is not None:
                    p.at[best, "보정배율"] *= sr
                    row.update(반영일=p.at[best, "basDt"], 처리="자동 반영(무상증자, 권리락일)")
            events.append(row)
    return pd.DataFrame(events, columns=["srtnCd", "itmsNm", "basDt", "주식수배율", "종가배율", "반영일", "처리"])


def load_daily() -> pd.DataFrame:
    files = sorted(config.DAILY_PRICES_DIR.glob("*.csv"))
    return pd.concat([pd.read_csv(f, dtype=str, encoding="utf-8-sig") for f in files], ignore_index=True)[PRICE_COLS]


def evaluate(base: bases.Base, until: str | None, daily: pd.DataFrame) -> dict:
    """보유 기준 하나를 기준일부터 until(없으면 끝)까지 평가한다."""
    sh = base.load_shares()
    shares = sh.set_index("종목코드")["보유주식수"]
    mergers = [m for m in config.MERGERS if m[0] in shares.index and m[3] > base.date]
    codes = set(shares.index) | {to for _, to, _, _ in mergers}

    start = pd.read_csv(base.prices, dtype=str, encoding="utf-8-sig")[PRICE_COLS]
    d = daily[(daily["basDt"] > base.date) & ((daily["basDt"] <= until) if until else True)]
    p = pd.concat([start, d], ignore_index=True)
    p = p[p["srtnCd"].isin(codes)].drop_duplicates(["basDt", "srtnCd"])
    p["clpr"] = pd.to_numeric(p["clpr"])
    p["lstgStCnt"] = pd.to_numeric(p["lstgStCnt"])
    p = p.sort_values(["srtnCd", "basDt"]).reset_index(drop=True)

    g = p.groupby("srtnCd")
    p["주식수배율"] = p["lstgStCnt"] / g["lstgStCnt"].shift()
    p["종가배율"] = p["clpr"] / g["clpr"].shift()
    ev = find_adjustments(p)
    p["누적배율"] = p.groupby("srtnCd")["보정배율"].cumprod()
    ev = ev.merge(sh[["종목코드", "평가액_억"]], left_on="srtnCd", right_on="종목코드", how="left")
    ev.insert(0, "보유기준연도", base.year)

    # 날짜 x 종목 표로 펼치고, 종가가 없는 날은 마지막 종가로 채운다
    price = p.pivot(index="basDt", columns="srtnCd", values="clpr").sort_index()
    mult = p.pivot(index="basDt", columns="srtnCd", values="누적배율").sort_index()
    stale = price.isna()
    price = price.ffill()
    mult = mult.ffill().fillna(1.0)
    value = price * mult * shares.reindex(price.columns).fillna(0)  # 원

    # 합병: 신주 상장일부터 소멸 종목 보유분 = 보유주식수 x 교부비율 x 존속 종목 종가 (이후 분할 보정 포함)
    for frm, to, ratio, eff in mergers:
        after = price.index >= eff
        if frm not in price.columns or not after.any():
            continue
        if to not in price.columns:
            raise SystemExit(f"합병 존속 종목 {to}의 종가가 없습니다. step6을 다시 실행하세요.")
        to_mult = mult[to] / mult.loc[after, to].iloc[0]
        value.loc[after, frm] = shares[frm] * ratio * price.loc[after, to] * to_mult[after]
        stale.loc[after, frm] = stale.loc[after, to]

    return {"base": base, "sh": sh, "value": value, "stale": stale, "events": ev}


def main() -> None:
    all_bases = bases.list_bases()
    if not all_bases:
        raise SystemExit("보유 기준이 없습니다. 먼저 step5나 roll_year를 실행하세요.")
    if not any(config.DAILY_PRICES_DIR.glob("*.csv")):
        raise SystemExit(f"일별 종가가 없습니다: {config.DAILY_PRICES_DIR} (먼저 step6을 실행하세요)")
    daily = load_daily()

    parts, results = [], []
    for k, base in enumerate(all_bases):
        next_date = all_bases[k + 1].date if k + 1 < len(all_bases) else None
        r = evaluate(base, next_date, daily)
        results.append(r)
        total = r["value"].sum(axis=1) / 1e12  # 조 원
        part = pd.DataFrame({
            "basDt": total.index,
            "평가액_조": total.round(4).values,
            "전일대비_%": (total.pct_change() * 100).round(3).values,
            "기준일대비_%": ((total / total.iloc[0] - 1) * 100).round(3).values,
            "종가고정_종목수": r["stale"].sum(axis=1).values,
            "보유기준연도": base.year,
            "기준평가액_조": round(total.iloc[0], 4),
        })
        # 기준일 자체는 앞 기준의 마지막 날로 남기고, 첫 기준만 기준일부터 보여 준다
        parts.append(part if k == 0 else part.iloc[1:])
    out = pd.concat(parts, ignore_index=True)
    out.to_csv(config.DAILY_VALUE_CSV, index=False, encoding="utf-8-sig")

    ev = pd.concat([r["events"] for r in results], ignore_index=True)
    ev[["보유기준연도", "srtnCd", "itmsNm", "basDt", "주식수배율", "종가배율", "반영일", "처리", "평가액_억"]].round(4).to_csv(
        config.SHARE_EVENTS_CSV, index=False, encoding="utf-8-sig"
    )

    cur = results[-1]
    sh, value, stale = cur["sh"], cur["value"], cur["stale"]
    held_codes = [c for c in value.columns if c in set(sh["종목코드"])]
    names = sh.set_index("종목코드")["종목명"]
    latest = pd.DataFrame({
        "종목코드": held_codes,
        "종목명": names.loc[held_codes].values,
        "기준일_억": (value.iloc[0][held_codes] / 1e8).round(1).values,
        "최근일_억": (value.iloc[-1][held_codes] / 1e8).round(1).values,
        "종가고정": stale.iloc[-1][held_codes].values,
    })
    latest["변화율_%"] = ((latest["최근일_억"] / latest["기준일_억"] - 1) * 100).round(2)
    latest["최근_비중_%"] = (latest["최근일_억"] / latest["최근일_억"].sum() * 100).round(3)
    latest.sort_values("최근일_억", ascending=False).to_csv(
        config.LATEST_HOLDINGS_CSV, index=False, encoding="utf-8-sig"
    )

    # 결과와 점검
    base = cur["base"]
    last = out.iloc[-1]
    print(f"=== 일별 평가액 ({base.year}년 말 공시 보유분 기준) ===")
    print(f"보유 기준 {[b.year for b in all_bases]}, 현재 기준일 {base.date}: {last['기준평가액_조']:.2f}조 원 "
          f"(공시 평가액 합계 {sh['평가액_억'].sum() / 1e4:.2f}조 원)")
    print(f"최근일 {last['basDt']}: {last['평가액_조']:.2f}조 원 (기준일 대비 {last['기준일대비_%']:+.2f}%)")
    print(f"기간 중 최고 {out['평가액_조'].max():.2f}조 원 ({out.loc[out['평가액_조'].idxmax(), 'basDt']}), "
          f"최저 {out['평가액_조'].min():.2f}조 원 ({out.loc[out['평가액_조'].idxmin(), 'basDt']})")

    cur_ev = cur["events"]
    print(f"\n현재 기준의 주식 수 변동 사건 {len(cur_ev)}건:")
    print(cur_ev["처리"].value_counts().to_string())
    todo = cur_ev[cur_ev["처리"].str.startswith("미반영")].sort_values("평가액_억", ascending=False)
    if not todo.empty:
        print("미반영 사건 (평가액 상위 10개):")
        print(todo[["itmsNm", "basDt", "주식수배율", "종가배율", "평가액_억"]].round(3).head(10).to_string(index=False))
    print(f"최근일 종가 고정(종가 끊김) 종목: {int(last['종가고정_종목수'])}개")

    print("\n=== 점검: 전일 대비 큰 변동일 (합계 ±3% 초과) ===")
    big_days = out[out["전일대비_%"].abs() > 3]
    print(f"{len(big_days)}일" if not big_days.empty else "없음")

    # 보정 후에도 하루 ±30%를 넘게 움직인 종목은 보정 누락 가능성이 있다
    v_ratio = (value / value.shift()).stack().dropna()
    sus = v_ratio[(v_ratio > 1 + LIMIT_MOVE + 0.01) | (v_ratio < 1 - LIMIT_MOVE - 0.01)]
    print(f"\n=== 점검: 보정 후에도 하루 ±{LIMIT_MOVE:.0%}를 넘은 종목·날짜: {len(sus)}건 ===")
    if len(sus):
        s = sus.rename("배율").reset_index()
        s["평가액_억"] = s["srtnCd"].map(sh.set_index("종목코드")["평가액_억"])
        s["종목명"] = s["srtnCd"].map(names)
        print(s.sort_values("평가액_억", ascending=False)[["종목명", "basDt", "배율", "평가액_억"]]
              .round(3).head(15).to_string(index=False))

    print(f"\n저장: {config.DAILY_VALUE_CSV}\n저장: {config.SHARE_EVENTS_CSV}\n저장: {config.LATEST_HOLDINGS_CSV}")


if __name__ == "__main__":
    main()
