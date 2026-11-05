"""국민연금 국내 의결권 행사내역을 모은다.

    python fetch_votes.py

출력: data/votes_meetings.csv (주총 목록), data/votes_items.csv (안건별 행사내용)

- 기금운용본부 홈페이지의 '국내 의결권 행사내역' 목록과 상세 화면을 읽는다(해외는 다루지 않는다).
- config.VOTES_START 이후 주총만 모으고, 이미 받은 주총은 건너뛴다. 매일 실행하면 새 주총만 추가된다.
- 공개 홈페이지이므로 요청 사이에 간격을 두고, 중간 저장으로 끊겨도 받은 만큼은 남긴다.
"""
import html
import re
import sys
import time
from datetime import date

import pandas as pd

import config
import nps_http

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

PAGE_SIZE = 100
PAUSE = 0.3       # 요청 사이 간격(초)
SAVE_EVERY = 50   # 이 주총 수마다 중간 저장
KEY = ["코드", "주총일자", "구분코드"]
MEETING_COLS = ["주총일자", "회사명", "코드", "구분", "구분코드", "제공기관코드", "일련번호", "안건수"]
ITEM_COLS = ["주총일자", "회사명", "코드", "구분", "의안번호", "의안내용", "행사내용", "반대사유", "근거조항"]

DETAIL_RE = re.compile(
    r"fnc_goDetail\('([^']*)','([^']*)','([^']*)','([^']*)','([^']*)'\);\">\s*([^<]+?)\s*<"
    r".*?<td>\s*\d{4}/\d{2}/\d{2}\s*</td>\s*<td>\s*([^<]*?)\s*</td>",
    re.S,
)


def clean(s: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def get(url: str, **kw) -> str:
    return nps_http.fetch("POST", url, **kw).text


def list_meetings(start: str, end: str) -> pd.DataFrame:
    rows, page = [], 1
    while True:
        body = {"pageIndex": page, "pageUnit": PAGE_SIZE, "recordCountPerPage": PAGE_SIZE,
                "issueInsNm": "", "gmosStartDt": start, "gmosEndDt": end}
        text = get(config.VOTES_LIST_URL, json=body)
        found = DETAIL_RE.findall(text)
        for sn, prov, code, ymd, kind, name, kind_nm in found:
            rows.append({"일련번호": sn, "제공기관코드": prov, "코드": code, "주총일자": ymd,
                         "구분코드": kind, "회사명": clean(name), "구분": clean(kind_nm)})
        if len(found) < PAGE_SIZE:
            break
        page += 1
        time.sleep(PAUSE)
    return pd.DataFrame(rows).drop_duplicates(KEY)


def fetch_items(m: dict) -> list[dict]:
    text = get(config.VOTES_DETAIL_URL, data={
        "edwmVtrtUseSn": m["일련번호"], "dataPvsnInstCdVl": m["제공기관코드"],
        "pblcnInstCdVl": m["코드"], "gmosYmd": m["주총일자"], "gmosKindCd": m["구분코드"],
    })
    start = text.find("의안번호")
    body = text[start:text.find("</tbody>", start)] if start >= 0 else ""
    items = []
    for tr in re.findall(r"<tr>(.*?)</tr>", body, re.S):
        tds = [clean(td) for td in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
        if len(tds) >= 3:
            tds += [""] * (5 - len(tds))
            items.append({"주총일자": m["주총일자"], "회사명": m["회사명"], "코드": m["코드"], "구분": m["구분"],
                          "의안번호": tds[0], "의안내용": tds[1], "행사내용": tds[2],
                          "반대사유": tds[3], "근거조항": tds[4]})
    return items


def load(path, cols) -> pd.DataFrame:
    if path.exists():
        return pd.read_csv(path, dtype=str, encoding="utf-8-sig").fillna("")
    return pd.DataFrame(columns=cols)


def save(meetings: pd.DataFrame, items: pd.DataFrame) -> None:
    meetings.sort_values(["주총일자", "코드"]).to_csv(config.VOTES_MEETINGS_CSV, index=False, encoding="utf-8-sig")
    items.sort_values(["주총일자", "코드", "의안번호"]).to_csv(config.VOTES_ITEMS_CSV, index=False, encoding="utf-8-sig")


def main() -> None:
    old_m = load(config.VOTES_MEETINGS_CSV, MEETING_COLS)
    old_i = load(config.VOTES_ITEMS_CSV, ITEM_COLS)
    listed = list_meetings(config.VOTES_START, date.today().isoformat())
    have = set(map(tuple, old_m[KEY].values))
    todo = listed[[tuple(r) not in have for r in listed[KEY].values]]
    print(f"홈페이지 목록 {len(listed)}건, 이미 받은 주총 {len(have)}건, 새로 받을 주총 {len(todo)}건")

    new_m, new_i = [], []
    for k, (_, m) in enumerate(todo.iterrows(), 1):
        items = fetch_items(m.to_dict())
        new_i.extend(items)
        new_m.append({**{c: m[c] for c in MEETING_COLS if c in m}, "안건수": str(len(items))})
        if k % SAVE_EVERY == 0:
            save(pd.concat([old_m, pd.DataFrame(new_m)]), pd.concat([old_i, pd.DataFrame(new_i, columns=ITEM_COLS)]))
            print(f"  {k}/{len(todo)} 중간 저장")
        time.sleep(PAUSE)

    meetings = pd.concat([old_m, pd.DataFrame(new_m, columns=MEETING_COLS)], ignore_index=True).drop_duplicates(KEY)
    items = pd.concat([old_i, pd.DataFrame(new_i, columns=ITEM_COLS)], ignore_index=True)
    save(meetings, items)

    print(f"\n=== 국내 의결권 행사 ({config.VOTES_START} 이후) ===")
    print(f"주총 {len(meetings):,}건, 안건 {len(items):,}건")
    print(items["행사내용"].value_counts().to_string())
    print(f"\n저장: {config.VOTES_MEETINGS_CSV}\n저장: {config.VOTES_ITEMS_CSV}")


if __name__ == "__main__":
    main()
