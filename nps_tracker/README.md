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
인증키는 **Decoding(일반) 인증키**를 씁니다. 아래 둘 중 하나로 설정하세요(환경변수가 `.env`보다 우선).

- `.env` 파일(이 폴더, git에서 제외됨): `DATA_GO_KR_KEY=여기에키`
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

## 아직 없는 단계
5~8단계(보유 주식 수 계산, 일별 종가 수집, 일별 시가 계산, 월별 검증)는 시세 API의 실제 응답
(종목코드·상장주식수 항목, 수정주가 여부, 조회 가능 기간)을 확인한 뒤 추가합니다.

## 주의
- 인증키를 코드, 채팅, 깃에 올리지 마세요. `.gitignore`에 `.env`와 결과 파일이 들어 있습니다.
- 지표 이름과 화면 설명에는 항상 "2025년 말 공시 보유분 기준"이라고 적으세요.
