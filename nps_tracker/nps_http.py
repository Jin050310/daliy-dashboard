"""기금운용본부 홈페이지(fund.nps.or.kr) 요청 도우미.

- 이 서버는 GitHub Actions에서 접속할 때 연결을 정상 종료 절차 없이 닫기도 한다(SSL UNEXPECTED_EOF).
  공개 자료만 읽으므로 이런 종료를 오류로 보지 않게 하고, 인증서 검증은 그대로 둔다.
- 일시적인 오류는 잠시 뒤 다시 시도한다.
"""
import ssl
import time

import requests
from requests.adapters import HTTPAdapter

ATTEMPTS = 4


class _TolerantTLS(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        ctx = ssl.create_default_context()
        ctx.options |= ssl.OP_IGNORE_UNEXPECTED_EOF
        kwargs["ssl_context"] = ctx
        return super().init_poolmanager(*args, **kwargs)


_session = requests.Session()
_session.mount("https://", _TolerantTLS())


def fetch(method: str, url: str, timeout: int = 30, **kwargs) -> requests.Response:
    """HTTP 200 응답을 돌려준다. 끝내 실패하면 원인 종류를 남기고 멈춘다."""
    reason = ""
    for attempt in range(ATTEMPTS):
        try:
            r = _session.request(method, url, timeout=timeout, **kwargs)
            if r.status_code == 200:
                return r
            reason = f"HTTP {r.status_code}"
        except requests.RequestException as e:
            reason = type(e).__name__
        if attempt < ATTEMPTS - 1:
            time.sleep(5 * (attempt + 1))
    raise SystemExit(f"홈페이지 접속 실패 ({reason}): {url}")
