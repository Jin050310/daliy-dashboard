"""프로젝트 공통 설정. 경로와 기준값은 여기서만 바꾼다."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"

# 입력 파일 (공공데이터포털 '국민연금공단_국내주식 투자정보_20251231' CSV)
RAW_CSV = DATA / "raw" / "nps_domestic_stock_20251231.csv"
CSV_ENCODING = "cp949"  # 이 파일은 UTF-8이 아니라 cp949라 지정이 필요하다

# 중간·결과 파일
HOLDINGS_CLEAN = DATA / "holdings_clean.csv"
LISTED_CSV = DATA / "listed_20251231.csv"
MANUAL_MAP_CSV = DATA / "manual_map.csv"  # 사람이 확인한 매핑 (종목명, 종목코드)
MAPPING_CSV = DATA / "mapping.csv"
MAPPING_REVIEW_CSV = DATA / "mapping_review.csv"

# 기준일: 이 날짜 기준 상장 종목 목록을 받아 매핑한다
BASE_DATE = "20251231"

# 검증 기준값 (조 원). 보도 기준 약 264조 원이므로,
# 기금운용본부 월간 공시(2025년 12월 말)에서 정확한 값을 확인해 교체할 것.
OFFICIAL_TOTAL_JO = 264.0

# 인증키는 파일에 쓰지 말고 환경변수로만 읽는다
API_KEY_ENV = "DATA_GO_KR_KEY"

# 금융위원회_KRX상장종목정보 요청 주소.
# 아래 값은 기억에 의존한 것이라 확인이 필요하다.
# 활용신청 후 API 상세 페이지의 '요청 주소'와 다르면 그 값으로 바꿀 것.
KRX_LISTED_URL = "https://apis.data.go.kr/1160100/service/GetKrxListedInfoService/getItemInfo"
