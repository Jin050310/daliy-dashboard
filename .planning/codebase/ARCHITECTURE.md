---
last_mapped_commit: 3b3c85edda38a57a806408b9d0d4b866e51418af
last_mapped_at: 2026-11-06
---
<!-- refreshed: 2026-11-06 -->
# Architecture

**Analysis Date:** 2026-11-06

## System Overview

```text
┌──────────────────────────────────────────────────────────────────────┐
│                GitHub Actions: `.github/workflows/daily-update.yml`   │
│          (cron 06:30 UTC weekdays, or workflow_dispatch)              │
└───────────────┬──────────────────────────────────────────────────────┘
                │ runs steps in `nps_tracker/` (working-directory)
                ▼
┌──────────────────────────────────────────────────────────────────────┐
│ Collection (external data -> CSV)                                      │
│  roll_year.py · step6_daily_prices.py · fetch_votes.py ·              │
│  fetch_official.py · record_daily.py                                   │
│  (helpers: krx_api.py, nps_http.py)                                    │
└───────────────┬──────────────────────────────────────────────────────┘
                │ writes `nps_tracker/data/**`
                ▼
┌──────────────────────────────────────────────────────────────────────┐
│ Computation (CSV -> CSV)                                               │
│  step7_daily_value.py  (uses bases.py for holdings baselines)          │
│  step8_monthly_check.py                                                │
│  (step1_load_holdings.py, step4_map_codes.py, step5_shares.py are      │
│   one-time / setup-stage builders for the 2025 baseline)               │
└───────────────┬──────────────────────────────────────────────────────┘
                │ reads `data/*.csv`
                ▼
┌──────────────────────────────────────────────────────────────────────┐
│ Presentation (CSV + JSON -> static HTML)                                │
│  build_dashboard.py -> `nps_tracker/site/index.html` (self-contained)  │
│  + `site/status.json` written by the workflow shell step               │
└───────────────┬──────────────────────────────────────────────────────┘
                ▼
        GitHub Pages deploy (`actions/deploy-pages@v4`)
```

## Pattern Overview

**Overall:** Batch ETL pipeline of standalone Python scripts. Each script is a `main()`-guarded CLI that reads CSV files from `nps_tracker/data/` and writes CSV or HTML back to the same tree. There is no server, no database, no long-running process, and no web framework. Orchestration is entirely the GitHub Actions YAML.

**Key Characteristics:**
- Scripts communicate only through files on disk (CSV, JSON, HTML). No script imports another script's runtime state except for shared modules `config.py`, `bases.py`, `krx_api.py`, and `nps_http.py`.
- All paths and reference values live in one module: `nps_tracker/config.py`. Scripts never hard-code data paths.
- Each stage is designed to be re-runnable and incremental: `step6_daily_prices.py` skips dates already present, `record_daily.py` upserts one row per Asia/Seoul date, `fetch_votes.py` skips meetings already fetched, `fetch_official.py` appends only new months.
- Failure is handled per stage, not per pipeline. The workflow marks collection steps `continue-on-error: true`, records each step's outcome, and still rebuilds and deploys the page using the last good data. A final `report` job fails the run so the owner gets a notification.
- Error codes (`timeout`, `auth`, `rate_limit`, `offline`, `schema_error`) are written to `data/collect_error.txt` by `krx_api.fail()` and read by `build_dashboard.run_status()` to show a stale-data state in the page.
- Public data only is fetched; the API key is read from the `DATA_GO_KR_KEY` environment variable (`nps_tracker/krx_api.py`, `config.API_KEY_ENV`).

## Layers

**Configuration:**
- Purpose: single source of truth for paths, baseline dates, reference totals, merger events, monthly official values, and API URLs.
- Location: `nps_tracker/config.py`
- Contains: `Path` constants (`DATA`, `DAILY_PRICES_DIR`, `DAILY_VALUE_CSV`, `SITE_DIR`, `BASES_DIR`, ...), `MERGERS` list, `OFFICIAL_MONTHLY` list, `OFFICIAL_TOTAL_JO`, `BASE_DATE`/`PRICE_DATE` (both `20251230`), `VOTES_START`, endpoint URLs.
- Depends on: standard library only (`os`, `pathlib`). Env var `NPS_DATA_DIR` can redirect `DATA` for testing.
- Used by: every other module in `nps_tracker/`.

**Shared Access Helpers:**
- Purpose: isolate external-network concerns.
- Location: `nps_tracker/krx_api.py` (public data portal JSON API, key from env), `nps_tracker/nps_http.py` (fund.nps.or.kr HTML/Excel requests with a tolerant TLS adapter and retries).
- Contains: `fetch_all()`, `parse_items()`, `classify()`, `fail()`, `get_key()`, `redact()` in `krx_api.py`; `fetch(method, url, ...)` in `nps_http.py`.
- Depends on: `config`, `requests`.
- Used by: `fetch_listed.py`, `fetch_prices.py`, `step6_daily_prices.py`, `record_daily.py` (through `krx_api`); `roll_year.py`, `fetch_official.py`, `fetch_votes.py` (through `nps_http`).

**Baseline Registry:**
- Purpose: model "one year-end disclosure" as a `Base` (year, last trading date, shares file, prices file) and enumerate all baselines in year order.
- Location: `nps_tracker/bases.py`
- Contains: `Base` frozen dataclass, `list_bases()`.
- Depends on: `config`, `pandas`.
- Used by: `step6_daily_prices.py` (which dates to fetch), `step7_daily_value.py` (which holdings apply from which date), `build_dashboard.py`.

**Collection (external -> data/):**
- Purpose: pull fresh public data into local CSV files.
- Location: `nps_tracker/roll_year.py`, `nps_tracker/step6_daily_prices.py`, `nps_tracker/record_daily.py`, `nps_tracker/fetch_votes.py`, `nps_tracker/fetch_official.py`, `nps_tracker/fetch_listed.py`, `nps_tracker/fetch_prices.py`.
- Contains: one `main()` per script. `roll_year.py` also validates a new disclosure before committing it into `data/bases/YYYY/`.
- Depends on: `config`, `bases`, `krx_api` or `nps_http`.
- Used by: the workflow (`daily-update.yml`) and by the owner for first-time setup.

**Computation (data/ -> data/):**
- Purpose: turn holdings and prices into daily valuations and monthly checks.
- Location: `nps_tracker/step7_daily_value.py`, `nps_tracker/step8_monthly_check.py`.
- Contains: `find_adjustments()` and `offsets()` in step7 (split, bonus-issue, merger adjustment logic); `official_list()` in step8 (merges manual `OFFICIAL_MONTHLY` with auto `official_monthly.csv`, auto wins).
- Depends on: `config`, `bases`, `pandas`, `numpy`.
- Used by: `build_dashboard.py` and the workflow.

**One-Time Baseline Builders (2025 setup, offline):**
- Purpose: produce the first baseline (`data/shares.csv`, `data/prices_20251230.csv`) from the raw cp949 CSV in `data/raw/`.
- Location: `nps_tracker/step1_load_holdings.py` (steps 1 to 3, no API), `nps_tracker/step4_map_codes.py` (name-to-code mapping, uses `data/manual_map.csv`), `nps_tracker/step5_shares.py` (shares = valuation / 12-30 close).
- Depends on: `config`, `pandas`. `step4` also needs `listed_20251230.csv`.
- Used by: run manually once; the output files are committed and treated as the 2025 baseline. Later baselines are produced automatically by `roll_year.py`, which reuses the same logic in `build_shares()` (`nps_tracker/roll_year.py`).

**Presentation:**
- Purpose: emit one static HTML file with all data embedded.
- Location: `nps_tracker/build_dashboard.py` (732 lines; the HTML/JS template is held inside this module).
- Contains: `decide()` (vote result classification), `votes_payload()`, `records_payload()`, `run_status()`, `fixtures_payload()`, `main()`.
- Depends on: `config`, `bases`, `pandas`, and the `fixtures/*.json` synthetic replay files.
- Used by: workflow step "월별 검증·대시보드 (step8, build)" and the Pages deploy.

## Data Flow

### Primary Request Path (scheduled daily run)

Each run is one linear job. The order is fixed in `.github/workflows/daily-update.yml`.

1. Checkout and install `nps_tracker/requirements.txt` (`pandas>=2.0`, `requests>=2.31`), Python 3.13, `TZ=Asia/Seoul`.
2. `roll_year.py` (`continue-on-error`): checks `fund.nps.or.kr` for a new year-end disclosure. Writes `data/bases/YYYY/shares.csv` and `prices.csv` only if validation passes, and deletes daily prices after the baseline date so step6 refetches them.
3. `step6_daily_prices.py` (`continue-on-error`): for each weekday from the first baseline date to yesterday, one API call for all stocks. Appends to `data/daily/YYYYMM.csv`.
4. `fetch_votes.py` (`continue-on-error`): appends new AGM meetings to `data/votes_meetings.csv` and `data/votes_items.csv`.
5. `fetch_official.py` (`continue-on-error`): appends a new monthly official total to `data/official_monthly.csv` when the site shows a new month.
6. `step7_daily_value.py` (no `continue-on-error`): reads all bases via `bases.list_bases()`, applies split and bonus-issue corrections and merger substitutions (`config.MERGERS`), writes `data/daily_value.csv`, `data/share_events.csv`, `data/latest_holdings.csv`.
7. `record_daily.py` (only if step6 succeeded, `continue-on-error`): calls the price API once more for today, keeps the raw response in `data/source_records/YYYY-MM-DD.csv`, and upserts a row in `data/daily_record.csv` keyed by Asia/Seoul date.
8. `step8_monthly_check.py` then `build_dashboard.py`: compare daily totals to official monthly values (`data/monthly_check.csv`), then write `site/index.html`. `run_status()` reads `PRICES_OUTCOME` and `RECORD_OUTCOME` env vars and `data/collect_error.txt`.
9. Workflow writes `site/status.json` from the step outcomes, uploads `nps_tracker/site` as the Pages artifact.
10. Commit step: `git add -A data`, commit as `github-actions[bot]` if changed, `git pull --rebase --autostash`, `git push`.
11. `deploy` job publishes Pages. `report` job exits 1 only when a collection step failed, to trigger the failure notification.

### Local Setup Path (one-time, 2025 baseline)

1. `step1_load_holdings.py` reads `data/raw/nps_domestic_stock_20251231.csv` (cp949) and writes `data/holdings_clean.csv`. No API.
2. `fetch_listed.py` then `step4_map_codes.py` map names to codes, using `data/manual_map.csv` for human corrections, writing `data/mapping.csv` and `data/mapping_review.csv`.
3. `fetch_prices.py` then `step5_shares.py` produce `data/prices_20251230.csv` and `data/shares.csv`.

### Secondary Flow: Ad-hoc Key Diagnostics

1. `diagnose_key.py` calls several portal endpoints with the same key and prints a redacted comparison. Independent of the pipeline; not called by the workflow.

**State Management:**
- Persistent state is entirely in CSV/JSON files under `nps_tracker/data/`. Committed files are the state of record. Files listed in `nps_tracker/.gitignore` (`daily_value.csv`, `share_events.csv`, `monthly_check.csv`, `latest_holdings.csv`, `collect_error.txt`, `site/`) are regenerated on every run.
- `data/daily_record.csv` and `data/source_records/` are append-or-upsert only and must never be deleted (per README).
- No in-memory state survives between runs.

## Key Abstractions

**`Base` (year-end holdings baseline):**
- Purpose: one disclosed holdings set and the close prices used to derive its share counts.
- Definition: `nps_tracker/bases.py` (`@dataclass(frozen=True) class Base`).
- Pattern: value object; `list_bases()` returns them sorted by year. Adding a year means adding `data/bases/YYYY/` files, no code change.

**Share-event adjustment:**
- Purpose: keep valuation correct when the stock count changes (split, bonus issue, merger) even though the price API is not split-adjusted.
- Definition: `nps_tracker/step7_daily_value.py` (`find_adjustments`, `offsets`, constants `EVENT_RATIO`, `LIMIT_MOVE`, `BONUS_LOOKBACK`).
- Pattern: heuristic classification. A share-count ratio and a price ratio that cancel each other are treated as a split; a price drop that precedes a bonus-issue listing by up to 60 trading days is treated as ex-rights. Other changes are logged to `share_events.csv` and not applied.

**Merger substitution:**
- Purpose: value a merged-away holding as the surviving company's shares from the listing date.
- Definition: tuples in `config.MERGERS` of `(delisted_code, survivor_code, ratio, listing_date)`.
- Pattern: manually maintained configuration list; edits go in `config.py` only.

**Official value resolution:**
- Purpose: a monthly reference total from the pension fund.
- Definition: `nps_tracker/step8_monthly_check.py::official_list()` merges `config.OFFICIAL_MONTHLY` (manual) with `data/official_monthly.csv` (automatic). Automatic values override manual ones for the same month.
- Pattern: manual defaults with auto-refreshed override.

**Vote decision classification:**
- Purpose: reduce four percentage lines per agenda item to one result.
- Definition: `nps_tracker/build_dashboard.py::decide()`. Both 찬성 and 반대 above zero means "분할" (split).

**Fixture replay:**
- Purpose: let the dashboard demonstrate failure and recovery states using public synthetic data, without touching real data.
- Definition: `nps_tracker/fixtures/*.json` loaded by `build_dashboard.fixtures_payload()`; the page selects them with a query parameter such as `?replay=T04-TIMEOUT`.

## Entry Points

**Scheduled pipeline:**
- Location: `.github/workflows/daily-update.yml`
- Triggers: cron `30 6 * * 1-5` (UTC) and `workflow_dispatch`.
- Responsibilities: runs all collection, computation, build, commit, and Pages deploy steps in order.

**Dashboard build:**
- Location: `nps_tracker/build_dashboard.py` (`if __name__ == "__main__": main()`)
- Triggers: workflow step, or manual `python build_dashboard.py`.
- Responsibilities: writes `nps_tracker/site/index.html`.

**Valuation engine:**
- Location: `nps_tracker/step7_daily_value.py`
- Triggers: workflow step, or manual `python step7_daily_value.py`.

**One-time setup scripts:**
- Location: `nps_tracker/step1_load_holdings.py`, `nps_tracker/fetch_listed.py`, `nps_tracker/step4_map_codes.py`, `nps_tracker/fetch_prices.py`, `nps_tracker/step5_shares.py`
- Triggers: manual, documented in `nps_tracker/README.md`.

**Key diagnostics:**
- Location: `nps_tracker/diagnose_key.py`
- Triggers: manual only.

## Architectural Constraints

- **Threading:** Single-threaded, synchronous. Requests use `time.sleep` pauses (`krx_api.fetch_all` `pause=0.2`, `nps_http.fetch` retry back-off, `fetch_votes.py` between requests).
- **Global state:** Module-level singletons in `nps_tracker/nps_http.py` (`_session`, a `requests.Session` with a custom TLS adapter) and module-level constants in `config.py`. `build_dashboard.py` and `step7_daily_value.py` call `sys.stdout.reconfigure(encoding="utf-8")` at import time.
- **Circular imports:** None detected. Dependency direction is `config` <- `bases` <- {`step7_daily_value`, `build_dashboard`, `step6_daily_prices`, `roll_year`}; `config` <- `krx_api` <- {`fetch_prices`, `fetch_listed`, `step6_daily_prices`, `record_daily`}.
- **Cross-stage contracts are implicit:** Column names in CSV files (for example `basDt`, `srtnCd`, `평가액_조`, `보유기준연도`) are shared string literals across `step7_daily_value.py`, `step8_monthly_check.py`, `build_dashboard.py`, and `record_daily.py`. Changing a column name requires updating every reader.
- **Workflow and code coupling:** `build_dashboard.run_status()` depends on the env vars `PRICES_OUTCOME` and `RECORD_OUTCOME` set in the YAML, and on the error code strings written by `krx_api.fail()`.
- **Data commit rules:** `daily-update.yml` commits `data/` directly to `main`. A local edit pushed without `git pull` first will conflict (the README asks for a pull before local work).
- **Data semantics:** Holdings are the 2025-12-30 disclosure, not current positions. Price API closes are not split-adjusted; adjustments are computed in step7.

## Anti-Patterns

### Hard-coded data schema in many scripts

**What happens:** Column names such as `basDt`, `srtnCd`, `clpr`, `lstgStCnt`, `평가액_조`, and `보유기준연도` are repeated as literals across `step6_daily_prices.py`, `step7_daily_value.py`, `step8_monthly_check.py`, `build_dashboard.py`, and `record_daily.py`.
**Why it's wrong:** A renamed or reordered API field breaks several stages at once, and the failure surfaces as a `KeyError` in a later stage.
**Do this instead:** Keep the column constant (`PRICE_COLS` in `step7_daily_value.py` is one example) in one module, and import it. Validate at read time, as `record_daily.validate()` already does for API readings.

### Stage scripts that call `SystemExit` for control flow

**What happens:** `nps_http.fetch()` and `krx_api.fail()` raise `SystemExit` with a message, and the workflow treats any non-zero exit as a step failure.
**Why it's wrong:** Callers cannot recover or fall back within the same process; only the YAML `continue-on-error` gate decides what happens next.
**Do this instead:** Follow the existing pattern for new collectors: write the error code to `config.COLLECT_ERROR_FILE` via `krx_api.fail()` so the dashboard can show the reason, and let the workflow fall back to the last good data.

### Scripts that duplicate logic from the setup path

**What happens:** `roll_year.py` contains `build_shares()` and `validate()` that repeat the 2025 setup logic from `step5_shares.py`.
**Why it's wrong:** Two copies can drift; a fix to one does not reach the other.
**Do this instead:** Put shared calculation in a module both can import (for example move `build_shares` into `bases.py` or a new `shares.py`) before changing it.

## Error Handling

**Strategy:** Fail-soft per collection stage, fail-loud at the end. Collection steps are `continue-on-error`. Computation and build steps are not, so a bug there fails the job and blocks deploy.

**Patterns:**
- HTTP retry with back-off in `nps_tracker/nps_http.py` (`ATTEMPTS = 4`, sleep `5 * n` seconds). Final failure raises `SystemExit` with the reason.
- API-level failures that arrive as HTTP 200 text are classified in `krx_api.classify()` into `rate_limit`, `auth`, or `schema_error`.
- Validation before commit in `roll_year.py` (`validate()`): if any check fails, nothing is written and the script exits with an error.
- Partial success in `fetch_votes.py` and `step6_daily_prices.py`: results are saved as they are fetched, so an interruption keeps the progress.
- Dashboard degradation: `build_dashboard.run_status()` marks the page `stale` and shows the last good values.

## Cross-Cutting Concerns

**Logging:** `print()` to stdout only. No logging framework. Korean-language messages are used throughout; stdout is forced to UTF-8.

**Validation:** Ad hoc, per script. `roll_year.validate()` (year, count, mapping ratio 99.5%, official total 95 to 105%, share cross-check), `record_daily.validate()` (API reading shape), step7 `LIMIT_MOVE` check (flags daily moves beyond ±30% after adjustment), step8 coverage percentage.

**Authentication:** Public Data Portal key via `DATA_GO_KR_KEY` env var, set as a GitHub Actions secret. The fund website (`fund.nps.or.kr`) requires no auth. Key is never written to files or logs (`krx_api.redact()`).

**Testing:** No automated test suite in the repository. Fixtures under `nps_tracker/fixtures/` are used for dashboard replay, not as unit-test inputs. Verification is by running the scripts and reading the printed checks (see `step7_daily_value.py` and `step8_monthly_check.py` output).

---

*Architecture analysis: 2026-11-06*
