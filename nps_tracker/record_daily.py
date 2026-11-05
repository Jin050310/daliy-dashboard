"""호출일(Asia/Seoul) 기준으로 하루 한 건만 기록한다.

    python record_daily.py

입력: data/daily_value.csv (step7 결과)
출력: data/daily_record.csv (호출일, 사용_거래일, 평가액_조, 전일대비_%, 기록시각)

- 같은 날 여러 번 실행해도 기록은 1건이다. 그날의 첫 성공만 남기고 이후 실행은 덮어쓰지 않는다.
- 다음 날 실행하면 새 기록이 생긴다. 휴장일에는 마지막 거래일 값으로 기록한다.
- daily_value.csv는 거래일별 평가액이고, 이 파일은 '언제 호출해서 어떤 값을 얻었는가'의 기록이다.
- 수집이 실패한 실행에서는 부르지 않는다(워크플로 조건). 다음 성공 때 그날 기록이 생긴다.
"""
import sys
from datetime import datetime, timedelta, timezone

import pandas as pd

import config

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

KST = timezone(timedelta(hours=9), "Asia/Seoul")
COLS = ["호출일", "사용_거래일", "평가액_조", "전일대비_%", "기록시각"]


def record(now: datetime | None = None) -> bool:
    """새 기록을 만들었으면 True, 오늘 기록이 이미 있으면 False를 돌려준다."""
    now = now or datetime.now(KST)
    today = now.strftime("%Y%m%d")

    path = config.DAILY_RECORD_CSV
    old = (pd.read_csv(path, dtype=str, encoding="utf-8-sig", keep_default_na=False)
           if path.exists() else pd.DataFrame(columns=COLS))
    if today in set(old["호출일"]):
        print(f"{today} 기록이 이미 있어 그대로 둡니다 (전체 {len(old)}건)")
        return False

    values = pd.read_csv(config.DAILY_VALUE_CSV, dtype=str, encoding="utf-8-sig", keep_default_na=False)
    if values.empty:
        raise SystemExit("daily_value.csv가 비어 있어 기록하지 않습니다.")
    last = values.sort_values("basDt").iloc[-1]

    row = {"호출일": today, "사용_거래일": last["basDt"], "평가액_조": last["평가액_조"],
           "전일대비_%": last["전일대비_%"], "기록시각": now.strftime("%Y-%m-%d %H:%M")}
    out = pd.concat([old, pd.DataFrame([row], columns=COLS)], ignore_index=True).sort_values("호출일")
    out.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"{today} 기록 추가: 거래일 {last['basDt']}, {last['평가액_조']}조 (전체 {len(out)}건)")
    return True


if __name__ == "__main__":
    record()
