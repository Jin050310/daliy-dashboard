"""인증키 진단: 같은 키로 여러 API를 한 번씩 불러 서버 답을 비교한다. 키는 출력하지 않는다.

    python diagnose_key.py
"""
import os
import sys
from urllib.parse import unquote

import requests

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

key = os.environ.get("DATA_GO_KR_KEY", "")
print(f"키 길이: {len(key)}자 / '%' 포함: {'%' in key} / 공백 포함: {key != key.strip() or ' ' in key}")
if not key:
    raise SystemExit("환경변수 DATA_GO_KR_KEY가 비어 있습니다.")

B = "https://apis.data.go.kr/1160100"
TESTS = [
    ("상장종목정보 V2 (성공했던 API)", f"{B}/GetKrxListedInfoService_V2/getItemInfo_V2", {"basDt": "20251230"}),
    ("주식시세정보 V2 (우리가 쓰려는 API)", f"{B}/GetStockSecuritiesInfoService_V2/getStockPriceInfo_V2", {"basDt": "20251230"}),
    ("주식시세정보 구버전 주소", f"{B}/service/GetStockSecuritiesInfoService/getStockPriceInfo", {"basDt": "20251230"}),
]


def call(url, extra, k):
    p = {"serviceKey": k, "resultType": "json", "numOfRows": 1, "pageNo": 1}
    p.update(extra)
    try:
        r = requests.get(url, params=p, timeout=60)
    except Exception as e:
        return f"연결 실패: {type(e).__name__}"
    txt = r.text
    if r.status_code == 200:
        try:
            d = r.json()["response"]
            return f"HTTP 200 / 결과코드 {d['header'].get('resultCode')} {d['header'].get('resultMsg')} / 전체건수 {d['body'].get('totalCount')}"
        except Exception:
            return "HTTP 200 / 구조 확인 필요: " + txt[:150].replace("\n", " ")
    import re
    m = re.search(r'"errMsg"\s*:\s*"([^"]+)"', txt) or re.search(r"<errMsg>([^<]+)", txt)
    return f"HTTP {r.status_code} / {m.group(1) if m else txt[:120]}"


for name, url, extra in TESTS:
    print(f"\n[{name}]")
    print("  그대로:", call(url, extra, key))
    if "%" in key:
        print("  % 풀어서:", call(url, extra, unquote(key)))
