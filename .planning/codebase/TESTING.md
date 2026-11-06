---
last_mapped_commit: 3b3c85edda38a57a806408b9d0d4b866e51418af
last_mapped_at: 2026-11-06
---
# Testing Patterns

**Analysis Date:** 2026-11-06

## Test Framework

**Runner:**
- None. No test framework is installed or configured.
- `nps_tracker/requirements.txt` lists only `pandas>=2.0` and `requests>=2.31`.
- No `pytest.ini`, `tox.ini`, `setup.cfg`, `pyproject.toml`, or `conftest.py` exists in the repository.
- No file named `test_*.py`, `*_test.py`, or `tests/` directory exists in the tracked files.

**Assertion Library:**
- None. The codebase contains no `assert` statements in committed code.

**Run Commands:**
```bash
# There is no test command. The closest equivalents are:
cd nps_tracker
python step1_load_holdings.py       # Self-check of the 2025 holdings CSV (prints totals, coverage, concentration)
python step8_monthly_check.py       # Compares computed daily value with published monthly figures
python build_dashboard.py           # Rebuilds site/index.html; reads fixtures/*.json for replay data
```

## What "Testing" Means in This Repo

Verification is done by runtime validation gates inside the pipeline rather than by a test suite. Each gate either passes and lets the run continue, or raises `SystemExit` and writes nothing.

**Validation gates that act as tests:**
- `nps_tracker/step1_load_holdings.py`: checks the raw CSV has 5 columns and prints total value, coverage, and concentration against `config.OFFICIAL_TOTAL_JO`.
- `nps_tracker/roll_year.py`: runs a validation list before saving a new year's holdings. Checks include matching year in file, minimum row count (`MIN_ROWS = 500`), mapped value ratio (`MIN_MAPPED_PCT = 99.5`), coverage against the official total (`COVER_RANGE = (95, 105)`), and consistency of implied shares with `지분율 x 상장주식수`. Failure raises `SystemExit` listing every failed check and leaves `data/bases/` unchanged.
- `nps_tracker/record_daily.py` `validate(reading)`: checks a normalized reading against the schema keys, `signal_id` regex, finite numeric value, HTTPS `source_url`, ISO timestamps, `record_timezone == "Asia/Seoul"`, and that `record_date` equals the Asia/Seoul date of `fetched_at`. Raises `ValueError`.
- `nps_tracker/step7_daily_value.py`: detects share-count events (`EVENT_RATIO = 1.3`) and flags unexplained ones as `미반영(확인 필요)` in `data/share_events.csv`.
- `nps_tracker/step8_monthly_check.py`: compares computed month-end values with `config.OFFICIAL_MONTHLY` and `data/official_monthly.csv`. Entries with trust level `참고` are excluded from judgment.
- `nps_tracker/krx_api.py` `classify()`: turns server error text into reason codes so a failed run is explainable.

## Fixtures

**Location:**
- `nps_tracker/fixtures/` holds nine synthetic JSON responses for the T04 replay contract. These are the only test-data files in the repo.
- `config.FIXTURES_DIR` points to this folder. `nps_tracker/build_dashboard.py` documents that it reads `fixtures/*.json` for synthetic replay.

**Files:**
- `normal-d1-a.json`, `normal-d1-b.json`, `normal-d2.json`: successful responses on virtual days 1 and 2.
- `recover-d2.json`: recovery after a failure.
- `auth-401.json`, `rate-429.json`, `timeout.json`, `offline.json`, `schema-break.json`: error scenarios that map to the reason codes in `krx_api.fail`.

**Structure of each fixture (observed in `fixtures/normal-d1-a.json`):**
```json
{
  "fixture_id": "T04-NORMAL-D1-A",
  "contract_version": "1.1.0",
  "description_ko": "가상 1일차 첫 정상 조회: 새 일별 행을 만든다.",
  "virtual_now": "2026-08-24T00:00:00.000Z",
  "transport": { "mode": "http", "status": 200, "delay_ms": 20, "deadline_ms": 1500, "headers": {...} },
  "payload": { "signal_id": "...", "normalized_value": 100, "unit": "pt", "source_name": "...", "source_url": "https://...invalid/...", "source_time": "...", ... }
}
```
- `virtual_now` replaces the wall clock, so replays are deterministic.
- `transport` describes how the adapter should behave (status, delay, deadline). A replay adapter reads these fields instead of calling the network.
- `payload` has the same keys as a live response and is checked by the same `validate()` used for live data.
- The `.invalid` TLD in `source_url` is deliberate: the fixture cannot accidentally hit a real host.

**Rules for fixtures (from `aleph-state/README (2).md` and the fixture README):**
- Fixtures are described as public, synthetic inputs (`config.py`: "과제 공개 합성 fixture (원본 그대로)").
- Keep them unchanged from the published bundle ("원본 그대로"). Add new scenarios as new files rather than editing existing ones.

## Test Data Used by the Pipeline

Real data acts as regression input. Keep these files in git, because each daily run recomputes from them:
- `nps_tracker/data/raw/nps_domestic_stock_20251231.csv`: original public holdings file (cp949). Do not edit; see the README.
- `nps_tracker/data/shares.csv`, `nps_tracker/data/prices_20251230.csv`: baseline for 2025 holdings and prices.
- `nps_tracker/data/daily/YYYYMM.csv`: daily closing prices, one file per month.
- `nps_tracker/data/source_records/YYYY-MM-DD.csv`: raw API responses saved per day (`record_daily.py`), useful for reproducing a past run.

Generated outputs (`daily_value.csv`, `share_events.csv`, `monthly_check.csv`, `latest_holdings.csv`, `holdings_clean.csv`, `mapping*.csv`) are listed in `nps_tracker/.gitignore` and are regenerated, not tested against.

## Test Structure (if tests are added)

No test files exist, so there is no suite organization to copy. If tests are introduced, use this layout so they fit the existing flat-module imports:

```
nps_tracker/
├── tests/
│   ├── conftest.py          # sets NPS_DATA_DIR to a temp folder; adds nps_tracker/ to sys.path
│   ├── test_record_daily.py # validate(), apply_reading() on fixtures/*.json
│   ├── test_step7.py        # offsets(), find_adjustments()
│   └── test_krx_api.py      # classify(), redact(), parse_items()
```

Recommended patterns, matching current code:
- Import modules by bare name (`import record_daily`) after adding `nps_tracker/` to `sys.path`, because the code has no package structure.
- Use `config.NPS_DATA_DIR` (environment variable) or monkeypatch `config.DATA` to a temp folder. Never write into the real `data/` tree from a test.
- Inject time: call `record_daily.record(now=datetime(...))` instead of relying on the wall clock. `record()` already accepts `now`.
- Pass `now` as an aware datetime in `Asia/Seoul` to match production behavior.

## Mocking

**Framework:** None in use. If HTTP is mocked, use `unittest.mock` (standard library) or `responses`/`requests-mock` added to requirements.

**What to Mock:**
- `krx_api.requests.get` and `nps_http._session.request` for network calls. Return objects with `status_code`, `text`, and `json()`.
- `krx_api.time.sleep` and `nps_http.time.sleep` to keep retry tests fast.
- Real-world failures can be replayed with the `fixtures/*.json` error files: map `transport.status` and `transport.mode` to a fake response.

**What NOT to Mock:**
- pandas CSV reading and writing. Use real small temp CSVs; the `cp949` vs `utf-8-sig` distinction is one of the things that breaks in practice.
- `validate()` and `offsets()`. These are pure and should be tested directly with real values.
- `os.replace` in atomic-write tests. Use a temp directory instead.

**Example pattern for a pure function (no mocking needed):**
```python
# nps_tracker/tests/test_step7.py  (proposed)
import numpy as np
import step7_daily_value as s7

def test_offsets_accepts_split_that_price_cancels():
    # 2:1 split with price halving the same day offsets each other
    assert s7.offsets(sr=2.0, pr=0.5) is True

def test_offsets_rejects_rights_issue_without_price_drop():
    # new shares listed but price unchanged: not a cancellation
    assert s7.offsets(sr=1.2, pr=1.0) is False
```

## Fixtures and Factories

**Test Data (for new tests):**
- Build small DataFrames inline with the same Korean column names used in production (`종목코드`, `보유주식수`, `평가액_조`, `basDt`, `srtnCd`, `clpr`). Keep the dtype rules: strings for codes and dates.
- For `record_daily.apply_reading()`, a dict shaped like `fixtures/normal-d1-a.json` `payload` plus `fetched_at` and `record_date` is enough.

**Location:**
- Put fixture-style data for new tests under `nps_tracker/tests/data/` (does not exist yet). Keep the public `nps_tracker/fixtures/` folder unchanged.

## Coverage

**Requirements:** None enforced. No coverage tool is configured.

**View Coverage:** Not applicable. If `pytest-cov` is added:
```bash
pytest --cov=. --cov-report=term-missing
```

## Test Types

**Unit Tests:**
- Not present. Strong candidates: `offsets()`, `find_adjustments()`, `validate()`, `apply_reading()`, `classify()`, `redact()`, `parse_items()`, `list_bases()`. All are pure or nearly pure.

**Integration Tests:**
- Not present as code. Running the full pipeline with `NPS_DATA_DIR` pointed at a copy of `data/` is the manual equivalent.
- Live APIs are not called by any test. Live runs require `DATA_GO_KR_KEY` in the environment and are only executed by the GitHub Actions job `daily-update` (`.github/workflows/daily-update.yml`).

**Replay/Contract Tests:**
- The T04 contract (aleph-state) defines 35 criteria checked against the fixtures. The fixture set is the contract's test input; the live and replay adapters must call the same normalization and storage functions so that error handling is not duplicated.

**E2E Tests:**
- Not used. The "end-to-end" check is the daily workflow run plus the GitHub Pages deploy of `site/index.html`.

## Manual Verification Checklist

When changing a pipeline step, run the step and inspect its printed summary:
1. `python step7_daily_value.py`: check printed event list and that `data/share_events.csv` has no new `미반영(확인 필요)` rows you did not expect.
2. `python step8_monthly_check.py`: confirm the difference column is in the expected range for months already in `config.OFFICIAL_MONTHLY`.
3. `python record_daily.py`: confirm one row per `signal_id + record_date` in `data/daily_record.csv` (same day re-runs must update, not append).
4. `python build_dashboard.py`: open `site/index.html` and confirm the page loads and shows the latest date.

Use `NPS_DATA_DIR=<temp copy>` for steps 1 to 3 so the committed `data/` is not modified during experiments.

## Common Patterns

**Async Testing:**
- Not applicable. The code is synchronous.

**Error Testing (pattern for new tests):**
```python
import pytest
import krx_api

def test_classify_maps_quota_message_to_rate_limit():
    assert krx_api.classify("LIMITED_NUMBER_OF_SERVICE_REQUESTS EXCEEDS") == "rate_limit"

def test_fail_writes_reason_code_then_exits(tmp_path, monkeypatch):
    import config
    monkeypatch.setattr(config, "COLLECT_ERROR_FILE", tmp_path / "collect_error.txt")
    with pytest.raises(SystemExit, match="\\[auth\\]"):
        krx_api.fail("auth", "키 확인")
    assert (tmp_path / "collect_error.txt").read_text(encoding="utf-8") == "auth"
```

**Validation Error Testing:**
```python
import pytest
import record_daily

def test_validate_rejects_non_https_source():
    reading = {...}  # valid reading with source_url="http://example.com"
    reading["source_url"] = "http://example.com"
    with pytest.raises(ValueError, match="HTTPS"):
        record_daily.validate(reading)
```

**Atomic-Write Testing:**
- Verify that when the writer raises before `os.replace`, the original file is unchanged and no `.tmp` remains. Use `replace_file()` from `nps_tracker/record_daily.py` with a `write` callback that raises.

## Gaps

- No automated tests of any kind run in CI. `.github/workflows/daily-update.yml` only installs requirements and runs the production pipeline.
- Share-event detection (`find_adjustments`, `offsets`) carries the most numerical risk and has no tests.
- Scraping code (`fetch_official.py`, `fetch_votes.py`, `roll_year.py`) depends on HTML/Excel layouts that have no fixture files; layout changes are only caught at runtime by the validation gates.
- Adding a minimal `tests/` directory with pytest for the pure functions listed above is the highest-value first step.

---

*Testing analysis: 2026-11-06*
