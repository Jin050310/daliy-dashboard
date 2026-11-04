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
SHARES_CSV = DATA / "shares.csv"  # 5단계 결과: 종목별 보유 주식 수
DAILY_PRICES_DIR = DATA / "daily"  # 6단계 결과: 보유 종목의 일별 종가 (월별 파일 YYYYMM.csv)
DAILY_VALUE_CSV = DATA / "daily_value.csv"    # 7단계 결과: 일별 평가액 합계
SHARE_EVENTS_CSV = DATA / "share_events.csv"  # 7단계 결과: 주식 수 변동 사건과 처리 여부
LATEST_HOLDINGS_CSV = DATA / "latest_holdings.csv"  # 7단계 결과: 종목별 기준일·최근일 평가액
SITE_DIR = ROOT / "site"  # 대시보드 출력 폴더 (GitHub Pages로 배포)

# 일별 종가 수집 시작일 (2026년 첫 거래일)
DAILY_START = "20260102"

# 주식으로 교부되는 합병: (소멸 종목코드, 존속 종목코드, 소멸 1주당 존속 주식 수, 신주 상장일)
# 신주 상장일부터 소멸 종목 보유분을 존속 종목 주식으로 바꿔 평가한다.
MERGERS = [
    # HD현대인프라코어 -> HD건설기계(구 HD현대건설기계). 합병비율 1 : 0.1621707 (2025.7.1 이사회 결의)
    ("042670", "267270", 0.1621707, "20260126"),
]

# 기준일: 이 날짜 기준 상장 종목 목록을 받아 매핑한다
BASE_DATE = "20251230"  # 상장 목록 기준일 = 연말 마지막 거래일 (12월 31일은 휴장)

# 종가 기준일: 12월 31일은 증시 휴장일이라 종가가 없다. 연말 마지막 거래일(12월 30일)을 쓴다.
PRICE_DATE = "20251230"

# 검증 기준값 (조 원). 월간 공시에서 확인한 값이며,
# 출처가 불확실하면 기금운용본부 월간 공시(2025년 12월 말)로 다시 확인할 것.
OFFICIAL_TOTAL_JO = 263.7

# 8단계 월별 검증: 공시·보도된 국민연금 국내주식 월말 평가액 (조 원)
# (월, 금액, 출처, 신뢰). 신뢰가 "참고"인 값은 출처가 불분명해 판정에서 뺀다.
# 지분 5% 이상 종목만 합친 보도 수치(예: 6월 말 515.9조)는 기준이 달라 넣지 않는다.
OFFICIAL_MONTHLY = [
    ("202512", 263.7, "국민연금공단 포트폴리오(nps.or.kr)", "공식"),
    ("202602", 395.1, "머니투데이 2026.5.27 보도(원출처 미기재)", "참고"),
    ("202605", 543.635, "머니투데이 2026.7.30 보도(5월 말 자산별 평가액)", "공식"),
    ("202607", 418.6, "기금운용본부 포트폴리오 현황", "공식"),
    ("202608", 433.8, "기금운용본부 포트폴리오 현황", "공식"),
]
MONTHLY_CHECK_CSV = DATA / "monthly_check.csv"

# 인증키는 파일에 쓰지 말고 환경변수로만 읽는다
API_KEY_ENV = "DATA_GO_KR_KEY"

# 금융위원회_KRX상장종목정보 요청 주소.
# 기본 주소(GetKrxListedInfoService_V2)와 오퍼레이션 이름(/getItemInfo_V2)은
# 포털 상세 페이지의 활용명세(Swagger)에서 직접 확인한 값이다.
KRX_LISTED_URL = "https://apis.data.go.kr/1160100/GetKrxListedInfoService_V2/getItemInfo_V2"

# 금융위원회_주식시세정보 요청 주소 (포털 활용명세에서 확인한 값)
STOCK_PRICE_URL = "https://apis.data.go.kr/1160100/GetStockSecuritiesInfoService_V2/getStockPriceInfo_V2"
