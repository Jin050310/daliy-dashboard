"""공공데이터포털(금융위원회) API 공통 호출 도우미.

- 인증키는 환경변수(config.API_KEY_ENV) 또는 git에서 제외된 .env에서만 읽는다. 코드·로그에 남기지 않는다.
- 'Decoding(일반) 인증키'를 쓴다. requests가 한 번 더 인코딩하므로
  'Encoding 인증키'를 넣으면 %가 이중으로 인코딩되어 인증 오류가 난다.
- 응답 구조(response -> body -> items -> item)는 금융위원회 API 공통 형식을
  가정했다. 다르면 parse_items()만 고치면 된다.
"""
import os
import time

import requests

import config


def _read_dotenv() -> dict[str, str]:
    """ROOT/.env의 KEY=VALUE 줄을 읽는다. 파일이 없으면 빈 dict."""
    path = config.ROOT / ".env"
    if not path.exists():
        return {}
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def get_key() -> str:
    # 환경변수가 있으면 그것을 우선하고, 없으면 .env를 본다
    key = os.environ.get(config.API_KEY_ENV) or _read_dotenv().get(config.API_KEY_ENV)
    if not key:
        raise SystemExit(
            f"{config.API_KEY_ENV}가 환경변수에도 .env에도 없습니다. README의 '인증키 설정'을 보세요."
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
        r = requests.get(url, params=p, timeout=30)
        # raise_for_status()는 오류 메시지에 주소(=인증키)가 들어가므로 쓰지 않는다
        if r.status_code != 200:
            raise SystemExit(f"HTTP {r.status_code}: 요청 주소·활용신청 승인 여부·키를 확인하세요.")
        try:
            data = r.json()
        except ValueError:
            raise SystemExit("JSON이 아닌 응답입니다(인증 오류일 수 있음): " + r.text[:200])
        try:
            items, total = parse_items(data)
        except (KeyError, TypeError):
            raise SystemExit("예상과 다른 응답 구조입니다. parse_items()를 확인하세요: " + str(data)[:300])
        out.extend(items)
        if not items or page * rows_per_page >= total:
            break
        page += 1
        time.sleep(pause)
    return out
