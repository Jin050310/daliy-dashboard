---
last_mapped_commit: 3b3c85edda38a57a806408b9d0d4b866e51418af
last_mapped_at: 2026-11-06
---
# Codebase Structure

**Analysis Date:** 2026-11-06

## Directory Layout

```
daliy-dashboard/                       # git repo root (branch main)
├── .github/
│   └── workflows/
│       └── daily-update.yml           # Scheduled pipeline + Pages deploy
├── .vscode/
│   └── settings.json                  # Editor settings
├── aleph-state/                       # Separate task material (not part of the NPS pipeline)
│   ├── README (2).md
│   ├── asset-manifest (1).json
│   ├── public-contract (1).json
│   └── t04-real-information-board-public-v1 (3).zip
├── nps_tracker/                       # The whole application (Python pipeline + dashboard)
│   ├── *.py                           # Pipeline scripts, flat (no package)
│   ├── data/                          # CSV state of record and generated results
│   │   ├── raw/                       # Original disclosure CSV (cp949), do not edit
│   │   ├── daily/                     # Monthly daily-close files YYYYMM.csv (committed)
│   │   ├── source_records/            # Raw API responses per date YYYY-MM-DD.csv (committed)
│   │   └── bases/                     # Future-year baselines YYYY/ (created by roll_year.py)
│   ├── fixtures/                      # Public synthetic JSON for dashboard replay
│   ├── site/                          # Build output (gitignored), contains index.html
│   ├── .gitignore
│   ├── README.md
│   └── requirements.txt
├── nps_tracker.zip                    # Archived copy of nps_tracker/ (not used by code)
└── .planning/                         # GSD planning docs (this file lives here)
    └── codebase/
```

## Directory Purposes

**`.github/workflows/`:**
- Purpose: GitHub Actions definitions. Only one workflow exists.
- Contains: `daily-update.yml`.
- Key files: `.github/workflows/daily-update.yml` (cron, job order, commit and deploy logic).

**`nps_tracker/`:**
- Purpose: the entire project. All Python scripts are at this level with no subpackages.
- Contains: 18 Python modules, `config.py`, `requirements.txt`, `README.md`, `.gitignore`.
- Key files: `config.py`, `bases.py`, `step7_daily_value.py`, `build_dashboard.py`.
- Working directory: all workflow steps and commands run from here (`defaults.run.working-directory: nps_tracker`).

**`nps_tracker/data/`:**
- Purpose: all persisted data. Committed files are the record; some are regenerated.
- Contains: CSV files at the top level plus subdirectories listed below.
- Key files:
  - `shares.csv`: 2025 year-end holdings converted to share counts (committed).
  - `prices_20251230.csv`: 2025-12-30 close prices for all stocks (committed).
  - `daily_value.csv`: daily total valuation (regenerated, gitignored).
  - `daily_record.csv`: one row per recorded Asia/Seoul date (committed, append-only).
  - `official_monthly.csv`: monthly official totals scraped from the fund site (committed, append-only).
  - `votes_meetings.csv`, `votes_items.csv`: AGM and vote-result records (committed, append-only).
  - `manual_map.csv`: human-verified name-to-code corrections (referenced by `step4_map_codes.py`; not present in the working tree).
  - `share_events.csv`, `latest_holdings.csv`, `monthly_check.csv`, `collect_error.txt`: regenerated (gitignored).

**`nps_tracker/data/raw/`:**
- Purpose: original government file, never modified.
- Contains: `nps_domestic_stock_20251231.csv` (encoding cp949, read via `config.CSV_ENCODING`).

**`nps_tracker/data/daily/`:**
- Purpose: daily closing prices for every held stock, one file per month.
- Contains: `202601.csv` through `202611.csv` (committed). The current month file grows daily.
- Written by: `step6_daily_prices.py`.

**`nps_tracker/data/source_records/`:**
- Purpose: audit trail. Raw API response for each day `record_daily.py` successfully fetched.
- Contains: one `YYYY-MM-DD.csv` per recorded date.
- Written by: `record_daily.py`. Do not delete.

**`nps_tracker/data/bases/`:**
- Purpose: year-end baselines after 2025, automatically added.
- Contains: `YYYY/shares.csv` and `YYYY/prices.csv` per year. Currently empty in the working tree; created by `roll_year.py` when a new disclosure is published.
- Read by: `bases.list_bases()`.

**`nps_tracker/fixtures/`:**
- Purpose: synthetic JSON responses used for the dashboard's replay feature (IDs such as `T04-TIMEOUT`, `T04-RECOVER-D2`, `T04-AUTH-401`, `T04-OFFLINE`, `T04-RATE-429`, `T04-SCHEMA-BREAK`, `T04-NORMAL-D1-A`, `T04-NORMAL-D1-B`, `T04-NORMAL-D2`).
- Contains: 9 `*.json` files. Loaded as-is by `build_dashboard.fixtures_payload()`.
- Generated: no (provided material). Committed: yes.

**`nps_tracker/site/`:**
- Purpose: deployable static site.
- Contains: `index.html` (generated), `status.json` (written by the workflow shell step).
- Generated: yes. Committed: no (gitignored; uploaded as a Pages artifact).

**`.planning/codebase/`:**
- Purpose: codebase analysis documents consumed by GSD planning commands.
- Generated: yes (by `/gsd-map-codebase`). Committed: per team policy.

## Key File Locations

**Entry Points:**
- `.github/workflows/daily-update.yml`: scheduled run and manual dispatch.
- `nps_tracker/build_dashboard.py`: writes `site/index.html`.
- `nps_tracker/step7_daily_value.py`: daily valuation.
- `nps_tracker/step8_monthly_check.py`: monthly comparison.

**Configuration:**
- `nps_tracker/config.py`: all paths, baseline date, `MERGERS`, `OFFICIAL_MONTHLY`, endpoint URLs, vote start date.
- `nps_tracker/requirements.txt`: `pandas>=2.0`, `requests>=2.31`.
- `nps_tracker/.gitignore`: ignores `.venv/`, `__pycache__/`, `.env`, and regenerated outputs.
- `.vscode/settings.json`: editor configuration.

**Core Logic:**
- `nps_tracker/bases.py`: baseline registry.
- `nps_tracker/step7_daily_value.py`: adjustment and valuation.
- `nps_tracker/roll_year.py`: annual disclosure ingestion and validation.
- `nps_tracker/record_daily.py`: daily record with validation.
- `nps_tracker/build_dashboard.py`: HTML generation (template and vote classification).

**External Access:**
- `nps_tracker/krx_api.py`: public data portal client.
- `nps_tracker/nps_http.py`: fund site HTTP client.
- `nps_tracker/fetch_votes.py`, `nps_tracker/fetch_official.py`, `nps_tracker/roll_year.py`: fund site scrapers.

**Diagnostics:**
- `nps_tracker/diagnose_key.py`: API key check (manual).

**Testing:**
- No test directory or test framework. `nps_tracker/fixtures/` holds replay data only.

## Naming Conventions

**Files:**
- Pipeline stages use a numeric prefix matching the original design numbering: `step1_load_holdings.py`, `step4_map_codes.py`, `step5_shares.py`, `step6_daily_prices.py`, `step7_daily_value.py`, `step8_monthly_check.py`. There is no `step2` or `step3` file; steps 1 to 3 are in `step1_load_holdings.py`.
- Data-fetching scripts use a `fetch_` prefix: `fetch_listed.py`, `fetch_prices.py`, `fetch_votes.py`, `fetch_official.py`.
- Other scripts use descriptive snake_case: `roll_year.py`, `record_daily.py`, `build_dashboard.py`, `krx_api.py`, `nps_http.py`, `bases.py`, `diagnose_key.py`.
- Data files: lowercase snake_case, with a date suffix `_YYYYMMDD` when tied to a single base date (`prices_20251230.csv`, `listed_20251230.csv`) and `YYYYMM.csv` for monthly partitions.
- Raw government file names keep their original form (`nps_domestic_stock_20251231.csv`).

**Directories:**
- Lowercase, single word: `data`, `raw`, `daily`, `bases`, `fixtures`, `site`.
- Baseline year folders: four-digit year, `data/bases/2026/`.

**Identifiers in code:**
- Functions and variables: snake_case in Python (`build_shares`, `list_bases`, `find_adjustments`).
- Constants: UPPER_SNAKE_CASE in `config.py` (`BASE_DATE`, `MERGERS`, `OFFICIAL_MONTHLY`) and at module top in scripts (`EVENT_RATIO`, `LIMIT_MOVE`).
- Dataframe columns and CSV headers: Korean or API field names as-is (`평가액_조`, `보유기준연도`, `basDt`, `srtnCd`). Do not translate them; other scripts and the dashboard depend on the exact strings.
- Output paths: always built from `config.py` constants, never literal strings in scripts.

## Where to Add New Code

**New data collector (external source -> CSV):**
- Implementation: new `nps_tracker/fetch_<thing>.py` with a `main()` and `if __name__ == "__main__":` guard.
- Use `krx_api` for the public data portal (key from env) or `nps_http.fetch` for fund site pages.
- Output path: add a constant to `nps_tracker/config.py`, then write to it.
- Wiring: add a step in `.github/workflows/daily-update.yml` with `continue-on-error: true`, an `id:`, and include its outcome in `collect_failed` and in `status.json`.

**New computation stage:**
- Implementation: `nps_tracker/step<N>_<name>.py`, reading from `config` paths and writing a CSV in `nps_tracker/data/`.
- Place it after the data it reads is produced in the workflow order.

**New dashboard section:**
- Implementation: add a payload function in `nps_tracker/build_dashboard.py` (follow `votes_payload()` or `records_payload()`), add its key to the `data` dict in `main()`, and render it in the HTML template inside the same file.

**New annual baseline or merger:**
- Annual disclosure: no code change; `roll_year.py` writes `nps_tracker/data/bases/YYYY/`.
- Merger: append a tuple to `MERGERS` in `nps_tracker/config.py`.
- Monthly official value: append to `OFFICIAL_MONTHLY` in `nps_tracker/config.py`.

**New test (none exists yet):**
- Suggested location: `nps_tracker/tests/` (create it). Use `NPS_DATA_DIR` (read in `config.py`) to point tests at a temporary data folder, so real `data/` is not touched.

**Shared helpers:**
- HTTP to the public data portal: extend `nps_tracker/krx_api.py`.
- HTTP to the fund site: extend `nps_tracker/nps_http.py`.
- Baseline handling: extend `nps_tracker/bases.py`.

## Special Directories

**`nps_tracker/data/`:**
- Purpose: pipeline state. Mix of committed history and regenerated outputs. See `nps_tracker/.gitignore`.
- Generated: partially (see gitignore).
- Committed: partially. The workflow commits `data/` with `git add -A data`.

**`nps_tracker/data/source_records/` and `nps_tracker/data/daily_record.csv`:**
- Purpose: append-only audit history.
- Generated: yes (by `record_daily.py`).
- Committed: yes. Never delete.

**`nps_tracker/site/`:**
- Purpose: static output.
- Generated: yes.
- Committed: no.

**`nps_tracker/fixtures/`:**
- Purpose: public synthetic data for replay mode.
- Generated: no.
- Committed: yes. Do not edit; `build_dashboard` embeds them unchanged.

**`nps_tracker.zip`:**
- Purpose: archive copy at repo root.
- Generated: no.
- Committed: yes. Not referenced by any code.

**`aleph-state/`:**
- Purpose: separate task material (README, JSON manifests, zipped board). Not imported by `nps_tracker/`.
- Committed: yes.

---

*Structure analysis: 2026-11-06*
