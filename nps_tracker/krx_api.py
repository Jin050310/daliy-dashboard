"""공공데이터포털(금융위원회) API 공통 호출 도우미.

- 인증키는 환경변수(config.API_KEY_ENV)에서만 읽는다. 파일·로그에 남기지 않는다.
- 'Decoding(일반) 인증키'를 쓴다. requests가 한 번 더 인코딩하므로
  'Encoding 인증키'를 넣으면 %가 이중으로 인코딩되어 인증 오류가 난다.
- 응답 구조(response -> body -> items -> item)는 금융위원회 API 공통 형식을
  가정했다. 다르면 parse_items()만 고치면 된다.
"""
import os
import time
from urllib.parse import quote, quote_plus

import requests

import config


def redact(text: str, key: str) -> str:
    """서버 응답을 출력하기 전에 인증키(원문·URL 인코딩 형태)를 지운다."""
    for form in (key, quote(key, safe=""), quote_plus(key)):
        text = text.replace(form, "***")
    return text


def get_key() -> str:
    key = os.environ.get(config.API_KEY_ENV)
    if not key:
        raise SystemExit(
            f"환경변수 {config.API_KEY_ENV}가 없습니다. README의 '인증키 설정'을 보세요."
        )
    return key


def parse_items(data: dict) -> tuple[list[dict], int]:
    """(항목 목록, 전체 건수)를 돌려준다."""
    body = data["response"]["body"]
    total = int(body.get("totalCount", 0) or 0)
    items = body.get("items") or {}
    item = items.get("item", []) if isinstance(items, dict) else []
    if isinstance(item, dict):  # 결과가 1건이면 dict로 오는 경우가 있다
        item = [item]
    return item, total


def fetch_all(url: str, params: dict, rows_per_page: int = 1000, pause: float = 0.2) -> list[dict]:
    """페이지를 넘기며 전체 결과를 모은다."""
    key = get_key()
    page = 1
    out: list[dict] = []
    while True:
        p = dict(params)
        p.update(
            {"serviceKey": key, "resultType": "json", "numOfRows": rows_per_page, "pageNo": page}
        )
        r = None
        for attempt in range(4):  # 서버가 잠깐 불안정(5xx·연결 끊김)하면 잠시 후 다시 시도
            try:
                r = requests.get(url, params=p, timeout=60)
            except requests.RequestException as e:
                # 예외 메시지에는 주소(=인증키)가 들어가므로 종류 이름만 남긴다
                if attempt == 3:
                    raise SystemExit(f"연결 실패({type(e).__name__}): 네트워크나 서버 상태를 확인하세요.") from None
                time.sleep(5 * (attempt + 1))
                continue
            if r.status_code < 500:
                break
            time.sleep(3 * (attempt + 1))
        # raise_for_status()는 오류 메시지에 주소(=인증키)가 들어가므로 쓰지 않는다
        if r.status_code != 200:
            # 서버가 알려 주는 거절 사유(본문)를 보여 준다. 키가 잘린 채 남지 않도록 지운 뒤에 자른다.
            raise SystemExit(
                f"HTTP {r.status_code}: 요청 주소·활용신청 승인 여부·키를 확인하세요.\n"
                f"서버 응답: {redact(r.text, key)[:400]}"
            )
        try:
            data = r.json()
        except ValueError:
            raise SystemExit("JSON이 아닌 응답입니다(인증 오류일 수 있음): " + redact(r.text, key)[:200])
        try:
            items, total = parse_items(data)
        except (KeyError, TypeError):
            raise SystemExit("예상과 다른 응답 구조입니다. parse_items()를 확인하세요: " + redact(str(data), key)[:300])
        out.extend(items)
        if not items or page * rows_per_page >= total:
            break
        page += 1
        time.sleep(pause)
    return out
