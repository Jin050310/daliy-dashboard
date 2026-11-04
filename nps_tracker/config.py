"""프로젝트 공통 설정. 경로와 기준값은 여기서만 바꾼다."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"

# 입력 파일 (공공데이터포털 '국민연금공단_국내주식 투자정보_20251231' CSV)
RAW_CSV = DATA / "raw" / "nps_domestic_stock_20251231.csv"
CSV_ENCODING = "cp949"  # 이 파일은 UTF-8이 아니라 cp949라 지정이 필요하다

# 중간·결과 파일
HOLDINGS_CLEAN = DATA / "holdings_clean.csv"
LISTED_CSV = DATA / "listed_20251230.csv"
MANUAL_MAP_CSV = DATA / "manual_map.csv"  # 사람이 확인한 매핑 (종목명, 종목코드)
PRICES_CSV = DATA / "prices_20251230.csv"
MAPPING_CSV = DATA / "mapping.csv"
MAPPING_REVIEW_CSV = DATA / "mapping_review.csv"

# 기준일: 이 날짜 기준 상장 종목 목록을 받아 매핑한다
BASE_DATE = "20251230"  # 상장 목록 기준일 = 연말 마지막 거래일 (12월 31일은 휴장)

# 종가 기준일: 12월 31일은 증시 휴장일이라 종가가 없다. 연말 마지막 거래일(12월 30일)을 쓴다.
PRICE_DATE = "20251230"

# 검증 기준값 (조 원). 월간 공시에서 확인한 값이며,
# 출처가 불확실하면 기금운용본부 월간 공시(2025년 12월 말)로 다시 확인할 것.
OFFICIAL_TOTAL_JO = 263.7

# 인증키는 파일에 쓰지 말고 환경변수로만 읽는다
API_KEY_ENV = "DATA_GO_KR_KEY"

# 금융위원회_KRX상장종목정보 요청 주소.
# 기본 주소(GetKrxListedInfoService_V2)와 오퍼레이션 이름(/getItemInfo_V2)은
# 포털 상세 페이지의 활용명세(Swagger)에서 직접 확인한 값이다.
KRX_LISTED_URL = "https://apis.data.go.kr/1160100/GetKrxListedInfoService_V2/getItemInfo_V2"

# 금융위원회_주식시세정보 요청 주소 (포털 활용명세에서 확인한 값)
STOCK_PRICE_URL = "https://apis.data.go.kr/1160100/GetStockSecuritiesInfoService_V2/getStockPriceInfo_V2"
