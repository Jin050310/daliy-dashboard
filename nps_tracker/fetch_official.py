"""기금운용본부 홈페이지에서 국민연금 국내주식 평가액(월말)을 읽어 기록한다.

    python fetch_official.py

출력: data/official_monthly.csv (월, 공시값_조, 출처, 수집일)

- '자산군별 운용규모' 데이터에는 연도별 국내주식 규모(십억 원)가 있다. 지난 해는 연말 값이고,
  올해는 최신 달 값이며 매달 덮어써진다.
- 같은 홈페이지의 'YYYY년 M월 말 기준' 표시로 올해 값이 몇 월 말 값인지 정한다.
- 매일 실행하면 새 달 값이 올라온 날 한 줄이 추가된다. 지난 달 값은 홈페이지에서 사라지므로 여기서만 남는다.
- 기준월을 확인하지 못하면 아무것도 기록하지 않는다(추측하지 않는다).
"""
import re
import sys
from datetime import date

import pandas as pd
import requests

import config

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

SOURCE = "기금운용본부 자산군별 운용규모(자동 수집)"
COLS = ["월", "공시값_조", "출처", "수집일"]


def main() -> None:
    page = requests.get(config.OFFICIAL_MONTH_URL, timeout=30).text
    months = set(re.findall(r"(\d{4})년\s*(\d{1,2})월\s*말\s*기준", page))
    if len(months) != 1:
        raise SystemExit(f"기준월을 하나로 정하지 못했습니다: {months or '표시 없음'}")
    (yy, mm), = months
    latest_ym = f"{yy}{int(mm):02d}"

    r = requests.post(config.OFFICIAL_SIZE_URL, json={"searchGbu": "5", "cartMngSn": "1"}, timeout=30)
    rows = r.json().get("resultDtlList") or []
    # artclCn1 = 연도, artclCn3 = 국내주식(십억 원)
    by_year = {x["artclCn1"]: float(x["artclCn3"]) / 1000 for x in rows if x.get("artclCn1") and x.get("artclCn3")}
    if yy not in by_year:
        raise SystemExit(f"{yy}년 국내주식 규모가 없습니다. 받은 연도: {sorted(by_year)}")

    found = {latest_ym: by_year[yy]}
    for y, v in by_year.items():
        if y < yy:
            found[f"{y}12"] = v  # 지난 해 값은 연말 값

    old = (pd.read_csv(config.OFFICIAL_AUTO_CSV, dtype=str, encoding="utf-8-sig")
           if config.OFFICIAL_AUTO_CSV.exists() else pd.DataFrame(columns=COLS))
    have = set(old["월"])
    today = date.today().isoformat()
    new = [{"월": ym, "공시값_조": f"{v:.3f}", "출처": SOURCE, "수집일": today}
           for ym, v in sorted(found.items()) if ym not in have and ym >= config.OFFICIAL_MONTHLY[0][0]]
    out = pd.concat([old, pd.DataFrame(new, columns=COLS)], ignore_index=True).sort_values("월")
    out.to_csv(config.OFFICIAL_AUTO_CSV, index=False, encoding="utf-8-sig")

    print(f"홈페이지 기준월: {latest_ym}, 국내주식 {by_year[yy]:.3f}조 원")
    print(f"새로 기록: {', '.join(n['월'] for n in new) if new else '없음'} (전체 {len(out)}개월)")
    print(f"저장: {config.OFFICIAL_AUTO_CSV}")


if __name__ == "__main__":
    main()
