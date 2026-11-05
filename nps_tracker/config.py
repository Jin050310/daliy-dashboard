"""프로젝트 공통 설정. 경로와 기준값은 여기서만 바꾼다."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = Path(os.environ.get("NPS_DATA_DIR") or ROOT / "data")  # 시험할 때만 환경변수로 다른 폴더를 쓴다

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
DAILY_RECORD_CSV = DATA / "daily_record.csv"  # 호출일(Asia/Seoul) 기준 하루 한 건 기록
SHARE_EVENTS_CSV = DATA / "share_events.csv"  # 7단계 결과: 주식 수 변동 사건과 처리 여부
LATEST_HOLDINGS_CSV = DATA / "latest_holdings.csv"  # 7단계 결과: 종목별 기준일·최근일 평가액
SITE_DIR = ROOT / "site"  # 대시보드 출력 폴더 (GitHub Pages로 배포)

# 연말 공시 자동 교체 (roll_year.py). 새 연도 공시는 data/bases/YYYY/에 쌓인다.
BASES_DIR = DATA / "bases"
HOLDINGS_PAGE_URL = "https://fund.nps.or.kr/oprtprcn/ivsmprcn/getOHED0003M0.do"  # 연도별 '투자종목' 다운로드 버튼
HOLDINGS_FILE_BASE = "https://fund.nps.or.kr"

# 주식으로 교부되는 합병·포괄적 주식교환: (소멸 종목코드, 존속 종목코드, 소멸 1주당 존속 주식 수, 신주 상장일)
# 신주 상장일부터 소멸 종목 보유분을 존속 종목 주식으로 바꿔 평가한다.
# 현금으로 끝난 경우(더존비즈온 12만 원, 에코마케팅 1만6천 원)는 넣지 않는다. 마지막 종가로 고정되며 그 값이 지급액과 같다.
MERGERS = [
    # HD현대인프라코어 -> HD건설기계(구 HD현대건설기계). 합병비율 1 : 0.1621707 (2025.7.1 이사회 결의)
    ("042670", "267270", 0.1621707, "20260126"),
    # 세아특수강 -> 세아홀딩스. 포괄적 주식교환 1 : 0.1348985. 세아홀딩스 상장주식수가 2026.2.12에 늘어남
    ("019440", "058650", 0.1348985, "20260212"),
    # 코오롱ENP -> 코오롱인더스트리. 합병비율 1 : 0.1919531. 신주 상장 2026.4.16
    ("138490", "120110", 0.1919531, "20260416"),
    # 현대홈쇼핑 -> 현대지에프홀딩스. 포괄적 주식교환 1 : 6.3571040. 신주 상장 2026.7.20
    ("057050", "005440", 6.357104, "20260720"),
    # 신세계푸드 -> 이마트. 포괄적 주식교환 1 : 0.5031313. 이마트 자기주식으로 교부되어 상장주식수 변화 없음. 교부일 2026.8.11
    ("031440", "139480", 0.5031313, "20260811"),
    # 동양생명 -> 우리금융지주. 포괄적 주식교환 1 : 0.2521056. 신주 상장 2026.8.31
    ("082640", "316140", 0.2521056, "20260831"),
]

# 기준일: 이 날짜 기준 상장 종목 목록을 받아 매핑한다
BASE_DATE = "20251230"  # 상장 목록 기준일 = 연말 마지막 거래일 (12월 31일은 휴장)

# 종가 기준일: 12월 31일은 증시 휴장일이라 종가가 없다. 연말 마지막 거래일(12월 30일)을 쓴다.
PRICE_DATE = "20251230"

# 검증 기준값 (조 원). 2025년 말 국내주식 평가액 263,737십억 원
# (기금운용본부 '자산군별 운용규모', fetch_official.py로 확인).
OFFICIAL_TOTAL_JO = 263.737

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

# 기금운용본부 홈페이지의 국내주식 평가액 자동 수집 (fetch_official.py)
# 홈페이지는 올해 값이 최신 달 값으로 매달 덮어써지므로, 매일 읽어 새 달이 나오면 기록해 둔다.
OFFICIAL_SIZE_URL = "https://fund.nps.or.kr/oprtprcn/ivsmprcn/chartOHED0016P0.do"  # 연도별 자산군 규모(십억 원)
OFFICIAL_MONTH_URL = "https://fund.nps.or.kr/oprtprcn/ivsmprcn/getOHED0016M0.do"   # 'YYYY년 M월 말 기준' 표시
OFFICIAL_AUTO_CSV = DATA / "official_monthly.csv"  # 자동 수집 결과. OFFICIAL_MONTHLY보다 우선한다

# 국내 의결권 행사내역 (기금운용본부 > 기금공시 > 주주권 행사내역 > 국내)
VOTES_START = "2026-01-01"  # 이 날짜 이후 주주총회만 모은다
VOTES_LIST_URL = "https://fund.nps.or.kr/impa/edwmpblnt/empty/getOHEF0007M0.do"
VOTES_DETAIL_URL = "https://fund.nps.or.kr/impa/edwmpblnt/getOHEF0010M0.do"
VOTES_MEETINGS_CSV = DATA / "votes_meetings.csv"  # 주총 목록 (회사·일자·구분·안건 수)
VOTES_ITEMS_CSV = DATA / "votes_items.csv"        # 안건별 행사내용 (찬성·반대 등)

# 인증키는 파일에 쓰지 말고 환경변수로만 읽는다
API_KEY_ENV = "DATA_GO_KR_KEY"

# 금융위원회_KRX상장종목정보 요청 주소.
# 기본 주소(GetKrxListedInfoService_V2)와 오퍼레이션 이름(/getItemInfo_V2)은
# 포털 상세 페이지의 활용명세(Swagger)에서 직접 확인한 값이다.
KRX_LISTED_URL = "https://apis.data.go.kr/1160100/GetKrxListedInfoService_V2/getItemInfo_V2"

# 금융위원회_주식시세정보 요청 주소 (포털 활용명세에서 확인한 값)
STOCK_PRICE_URL = "https://apis.data.go.kr/1160100/GetStockSecuritiesInfoService_V2/getStockPriceInfo_V2"
