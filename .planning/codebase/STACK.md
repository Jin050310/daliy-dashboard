---
last_mapped_commit: 3b3c85edda38a57a806408b9d0d4b866e51418af
last_mapped_at: 2026-11-06
---
# Technology Stack

**Analysis Date:** 2026-11-06

## Languages

**Primary:**
- Python 3.13 (CI, `.github/workflows/daily-update.yml`) - all pipeline and build code in `nps_tracker/*.py`
- Local interpreter observed: Python 3.14.10 (not pinned locally; no `.python-version` file)

**Secondary:**
- HTML/CSS/JavaScript (inline, generated) - the dashboard page is emitted as a single `site/index.html` string template inside `nps_tracker/build_dashboard.py` (CSS around lines 100-300, client JS from ~line 400 onward)
- Markdown - documentation in `nps_tracker/README.md` and `aleph-state/README (2).md`
- YAML - CI definition in `.github/workflows/daily-update.yml`
- CSV - data store under `nps_tracker/data/` (cp949 encoded raw input, UTF-8 outputs)
- JSON - fixtures in `nps_tracker/fixtures/*.json`, `aleph-state/*.json`

## Runtime

**Environment:**
- CPython 3.13 on `ubuntu-latest` GitHub-hosted runners (set via `actions/setup-python@v5`, `python-version: "3.13"`)
- Timezone forced to `Asia/Seoul` via `env: TZ` in the workflow; `record_daily.py` and `config.py` also reason in KST (`Asia/Seoul`)

**Package Manager:**
- pip (no lockfile)
- Dependency manifest: `nps_tracker/requirements.txt` (`pandas>=2.0`, `requests>=2.31`)
- Lockfile: missing - versions are lower bounds only, so CI resolves the latest compatible releases on each run (pip cache keyed on `nps_tracker/requirements.txt`)

**Not present:** no `package.json`, no Node toolchain, no Dockerfile, no `pyproject.toml`, no `setup.py`.

## Frameworks

**Core:**
- None. The project is a plain Python script collection (no web framework, no ORM, no CLI framework). Entry points are `if __name__ == "__main__"` scripts run directly.

**Data processing:**
- pandas (>=2.0) - CSV read/write, merges, aggregation across `step*.py`, `bases.py`, `roll_year.py`, `record_daily.py`, `fetch_*.py`
- numpy - imported directly in `nps_tracker/step7_daily_value.py` (line 23) but NOT listed in `requirements.txt`; it is installed only as a transitive dependency of pandas

**Standard library notable usage:**
- `zipfile`, `xml.etree.ElementTree` - hand-rolled XLSX reader in `nps_tracker/roll_year.py` (`read_sheet`) so no `openpyxl` dependency is needed
- `ssl`, `requests.adapters.HTTPAdapter` - custom TLS adapter in `nps_tracker/nps_http.py`
- `difflib`, `unicodedata` - name matching in `nps_tracker/step4_map_codes.py`
- `hashlib` - record hashing in `nps_tracker/record_daily.py`
- `html` - unescaping in `nps_tracker/roll_year.py` and `nps_tracker/fetch_votes.py`

**Testing:**
- No test framework detected. Fixture-based replay is used instead: `nps_tracker/fixtures/` (JSON scenarios such as `rate-429.json`, `timeout.json`, `auth-401.json`, `schema-break.json`, `recover-d2.json`) are replayed by the dashboard, not by a test runner.

**Build/Dev:**
- No build tool. `nps_tracker/build_dashboard.py` generates `nps_tracker/site/index.html` (self-contained, embeds data as JSON).
- VS Code: `.vscode/settings.json` sets `"python.terminal.useEnvFile": true` (loads `.env` into terminals; the `.env` file is gitignored).

## Key Dependencies

**Critical (declared in `nps_tracker/requirements.txt`):**
- `pandas>=2.0` - all tabular logic; holdings, prices, daily value, monthly checks
- `requests>=2.31` - every HTTP call (KRX/data.go.kr APIs and fund.nps.or.kr scraping) via `krx_api.py` and `nps_http.py`

**Transitive / implicit:**
- `numpy` - used directly by `step7_daily_value.py`, arrives via pandas
- `urllib3` / `ssl` - underlying transport for `requests`

**Infrastructure (GitHub-hosted Actions, not pip packages):**
- `actions/checkout@v4`
- `actions/setup-python@v5` (pip cache enabled)
- `actions/configure-pages@v5`
- `actions/upload-pages-artifact@v3`
- `actions/deploy-pages@v4`

## Configuration

**Environment variables:**
- `DATA_GO_KR_KEY` - public-data portal (data.go.kr) Decoding API key. Read only via `os.environ` in `nps_tracker/krx_api.py` (`get_key`) and `nps_tracker/diagnose_key.py`. Supplied through GitHub Actions secrets in CI and set manually in a local shell for development. Never stored in files.
- `NPS_DATA_DIR` - optional override of the data directory (`nps_tracker/config.py`, line 6), used only for testing.
- `PRICES_OUTCOME`, `RECORD_OUTCOME` - set by the workflow for `build_dashboard.py` (line ~88) to decide whether to show "stale data" status.
- `TZ` - set to `Asia/Seoul` in the workflow.

**Project configuration file:**
- `nps_tracker/config.py` - single source for paths, base dates (`BASE_DATE`, `PRICE_DATE` = `20251230`), verification thresholds (`OFFICIAL_TOTAL_JO = 263.737`), `OFFICIAL_MONTHLY` reference values, `MERGERS` table, and all endpoint URLs. Designed to be the only file edited for routine updates.
- `nps_tracker/.gitignore` - excludes `.venv/`, `__pycache__/`, `.env`, generated intermediates (`holdings_clean.csv`, `mapping*.csv`, `daily_value.csv`, `monthly_check.csv`, `latest_holdings.csv`, `collect_error.txt`) and `site/`.

**Build / CI:**
- `.github/workflows/daily-update.yml` - the only CI definition. Runs on cron `30 6 * * 1-5` (UTC; 15:30 KST weekdays) and `workflow_dispatch`. Concurrency group `daily-update`, `cancel-in-progress: false`.
- Permissions granted to the workflow: `contents: write`, `pages: write`, `id-token: write`.

**Data layout:**
- `nps_tracker/data/raw/nps_domestic_stock_20251231.csv` - source file, cp949 encoded (`config.CSV_ENCODING`)
- `nps_tracker/data/` - committed outputs written by the bot (`shares.csv`, `prices_20251230.csv`, `daily/YYYYMM.csv`, `daily_record.csv`, `source_records/*.csv`, `votes_*.csv`, `official_monthly.csv`, `bases/YYYY/`)
- `nps_tracker/site/` - generated, gitignored, uploaded as the Pages artifact

## Platform Requirements

**Development:**
- Python 3.13+ recommended (CI version); pandas 2.x and requests 2.31+
- Windows, macOS, or Linux; README documents Windows PowerShell and POSIX shell variants for `.venv` creation and `DATA_GO_KR_KEY` setup
- VS Code optional (`.vscode/settings.json` present)
- Network access to `fund.nps.or.kr` and `apis.data.go.kr`

**Production:**
- GitHub Actions (`ubuntu-latest`) executes the daily pipeline
- GitHub Pages serves the static `site/` output (deployment via `actions/deploy-pages@v4`, environment `github-pages`)
- Repository: `https://github.com/Jin050310/daliy-dashboard` (remote `origin`)

**Other sibling assets (not executed by the pipeline):**
- `nps_tracker.zip` at repo root - archived copy of the tracker
- `aleph-state/` - public synthetic fixture bundle (JSON contracts and a zip); documentation/data only, no runtime code

---

*Stack analysis: 2026-11-06*
