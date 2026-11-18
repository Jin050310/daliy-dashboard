# 목표

`nps_tracker` 대시보드에 날짜 범위를 입력해 평가액, 변동률, 최고·최저일, 거래일 수를 조회하는 기능을 이어서 관리한다. 휴장일 보정과 최신 거래일 초과 안내는 `period.mjs`가 계산한다.

# 현재 상태

이 작업은 커밋 `22b8191`에 반영되어 있다. `period.mjs` 계산을 화면에 포함하도록 `build_dashboard.py`가 생성 HTML을 만들며, 화면 데이터는 `daily_value.csv`의 전체 정밀도 값을 쓴다. 생성된 `site/index.html`은 `.gitignore` 대상이다.

# 실행 명령

Windows PowerShell 기준. Python 3.10 이상, Node.js 22 이상, Git이 필요하다. Python 의존성은 `requirements.txt`에 있으며 설치 패키지 없이 기간 검사만 실행할 수 있다. 빈 폴더에서 다음을 실행한다.

```powershell
git clone https://github.com/Jin050310/daliy-dashboard.git
cd daliy-dashboard\nps_tracker
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
node --test tests/period.test.mjs
.\.venv\Scripts\python.exe step7_daily_value.py
.\.venv\Scripts\python.exe step8_monthly_check.py
.\.venv\Scripts\python.exe build_dashboard.py
```

작업 디렉터리는 clone 안의 `nps_tracker`다. 새 clone에는 `.gitignore`된 `data/daily_value.csv`, `data/latest_holdings.csv`, `data/monthly_check.csv`가 없으므로 대시보드 빌드 전에 7~8단계를 실행해야 한다. 위 재생성은 저장소에 포함된 `data/daily/*.csv`와 기준 파일을 사용하며 API 키가 필요 없다. API 수집을 할 때만 `$env:DATA_GO_KR_KEY = "발급받은 키"`를 설정하고 키를 파일에 저장하지 않는다. 별도 데이터 경로를 쓸 경우 `$env:NPS_DATA_DIR = "D:\\nps-data"`를 설정하되, 해당 폴더에 단계별 입력 데이터가 있어야 한다.

# 통과 검사

`node --test tests/period.test.mjs`: 10/10 통과. 새 임시 clone에서도 같은 결과를 확인했다. `step7_daily_value.py`, `step8_monthly_check.py`, `build_dashboard.py`도 clone에서 순서대로 실행되어 `site/index.html` 생성까지 확인했다.

# 남은 문제

대시보드 기간 조회 결과에서 날짜가 `2026.-1.0-`처럼 깨져 보인다. 기간 결과의 `YYYY-MM-DD`를 기존 `fmtDate`가 `YYYYMMDD`로 가정해 잘못 자르는 표시 문제다. 고정 검사는 계산 함수만 확인해 이 화면 문제를 잡지 못한다.

# 다음 작업

기간 결과 렌더링에서 `YYYY-MM-DD`를 올바르게 표시하도록 날짜 포맷을 수정하고, 고정 검사 10개와 실제 화면 조회를 각각 확인한다. 빌드 전에는 위 실행 명령으로 무시된 입력 산출물을 재생성한다.

# 변경 금지 범위

`tests/period.test.mjs`와 `tests/fixtures/period_sample.csv`는 고정 자료다. 검사 삭제, 조건 완화, 기대값 변경 없이 구현을 수정한다. API 키와 매일 생성되는 데이터 산출물은 저장소에 추가하지 않는다.
