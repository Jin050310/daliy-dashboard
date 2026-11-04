# 국민연금 공시 보유분 일별 시가 (국내주식)

## 이 프로젝트가 만드는 것
국민연금이 2025년 말 기준으로 공시한 국내주식 보유분을, 매일 종가로 평가한 금액입니다.

- 입력은 모두 실제 값입니다(공시 파일, 거래소 종가). 통계적 추정은 쓰지 않습니다.
- 국민연금의 **실제 오늘 보유분이 아닙니다.** 2025년 말 이후의 매매는 반영하지 않습니다.
- 국내주식만 다루며, 기금 전체 자산이 아닙니다.
- 종가는 다음 영업일 오후에 올라오므로 하루 늦게 반영됩니다.

## 폴더 구성
```
config.py              경로, 기준일, 검증 기준값
step1_load_holdings.py 1~3단계: CSV 정리, 합계·커버율·집중도 점검 (API 불필요)
krx_api.py             공공데이터포털 호출 도우미 (인증키는 환경변수로만 읽음)
fetch_listed.py        기준일 상장 종목 목록 내려받기 (API 키 필요)
step4_map_codes.py     4단계: 종목명 -> 종목코드 매핑
data/raw/              원본 CSV (수정하지 말고 보관)
data/                  중간·결과 파일
```

## VS Code에서 처음 한 번
1. VS Code에서 `파일 > 폴더 열기`로 이 폴더를 엽니다.
2. 터미널(`Ctrl + ~`)에서 가상환경을 만듭니다.
   - 윈도우: `python -m venv .venv` 후 `.venv\Scripts\activate`
   - 맥/리눅스: `python3 -m venv .venv` 후 `source .venv/bin/activate`
3. `pip install -r requirements.txt`
4. VS Code 오른쪽 아래(또는 `Ctrl+Shift+P` > `Python: Select Interpreter`)에서 `.venv`를 선택합니다.

## 실행 순서
### 1) 지금 바로 (API 키 불필요)
```
python step1_load_holdings.py
```
합계(약 261.6조 원), 커버율(약 99%), 집중도, 데이터 품질을 출력하고 `data/holdings_clean.csv`를 만듭니다.
`config.py`의 `OFFICIAL_TOTAL_JO`는 국민연금공단 공시(2025년 12월 말 국내주식 평가액) 기준 263.7조 원입니다.

### 2) 인증키가 생긴 뒤
공공데이터포털에서 `금융위원회_KRX상장종목정보`와 `금융위원회_주식시세정보`에 활용신청하고 승인받습니다.
인증키는 **Decoding(일반) 인증키**를 씁니다. 파일에 쓰지 말고 환경변수로만 설정하세요.

- 윈도우 PowerShell: `$env:DATA_GO_KR_KEY="여기에키"`
- 맥/리눅스: `export DATA_GO_KR_KEY="여기에키"`

그다음:
```
python fetch_listed.py
python step4_map_codes.py
```
`config.py`의 `KRX_LISTED_URL`은 기억에 의존한 값이라, API 상세 페이지의 요청 주소와 같은지 꼭 확인하세요.
`fetch_listed.py`가 출력하는 컬럼 이름이 `itmsNm`, `srtnCd`, `mrktCtg`가 아니어도 `step4_map_codes.py` 위쪽의 후보 목록에 추가하면 됩니다.

### 3) 매핑 결과 다듬기
`step4_map_codes.py`가 확정 매핑 평가액 비율을 출력합니다(목표 99.5% 이상).
`data/mapping_review.csv`에서 `review`, `unmatched`, `ambiguous`, `special` 항목을 확인하고,
정답을 `data/manual_map.csv`에 `종목명,종목코드` 형식으로 적은 뒤 다시 실행합니다.
평가액이 큰 종목부터 확인하면 됩니다. 괄호가 붙은 5개 특수 항목은 합쳐서 약 615억 원(0.02%)이라 매핑하지 않아도 됩니다.

### 4) 보유 주식 수 계산 (5단계)
```
python fetch_prices.py
python step5_shares.py
```
`fetch_prices.py`는 12/30 전 종목 종가(우선주 포함)를 받습니다. 이 파일이 있으면 `step4_map_codes.py`가 우선주까지 매핑합니다.
`step5_shares.py`는 `보유주식수 = 평가액 / 12/30 종가`로 계산하고, 공시 지분율 x 상장주식수와 교차 검증해 `data/shares.csv`를 만듭니다.

### 5) 일별 종가 수집과 일별 평가액 (6~7단계)
```
python step6_daily_prices.py
python step7_daily_value.py
```
`step6`은 2026-01-02부터 어제까지 하루 1회 호출로 보유 종목 종가를 모읍니다. 이미 받은 날짜는 건너뛰므로 매일 다시 실행하면 새 날짜만 추가됩니다.
`step7`은 `보유주식수 x 보정배율 x 그날 종가`로 일별 합계를 `data/daily_value.csv`에 만듭니다.
API 종가가 수정주가가 아니어서 액면분할·병합과 무상증자(권리락일 기준)는 자동 보정하고, 유상증자·합병 등은 `data/share_events.csv`에 남깁니다.
주식으로 교부되는 합병은 `config.py`의 `MERGERS`에 적어 두면 신주 상장일부터 존속 종목 주식으로 바꿔 평가합니다.
그 밖에 종가가 끊긴 종목(상장폐지·공개매수 등)은 마지막 종가로 고정합니다.

### 6) 월별 검증 (8단계)
```
python step8_monthly_check.py
```
`config.py`의 `OFFICIAL_MONTHLY`(공시·보도된 월말 국내주식 평가액)와 추적값을 비교해 `data/monthly_check.csv`를 만듭니다.
이 지표는 2025년 말 이후 매매를 반영하지 않으므로 차이가 나는 것이 정상입니다. 기준일 커버율(99.2%)에서 얼마나 벗어나는지로 매매 효과의 대략적인 크기를 봅니다.
새 월말 공시가 나오면 `OFFICIAL_MONTHLY`에 한 줄 추가하세요. 지분 5% 이상 종목만 합친 보도 수치는 기준이 달라 넣으면 안 됩니다.

## 주의
- 인증키를 코드, 채팅, 깃에 올리지 마세요. `.gitignore`에 `.env`와 결과 파일이 들어 있습니다.
- 지표 이름과 화면 설명에는 항상 "2025년 말 공시 보유분 기준"이라고 적으세요.
