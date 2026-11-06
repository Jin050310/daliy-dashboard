---
last_mapped_commit: 3b3c85edda38a57a806408b9d0d4b866e51418af
last_mapped_at: 2026-11-06
---
# Coding Conventions

**Analysis Date:** 2026-11-06

## Scope of the Codebase

All executable code lives in `nps_tracker/` (Python 3.13 in CI, see `.github/workflows/daily-update.yml`). The repo root holds only the workflow, `.vscode/settings.json`, the `aleph-state/` spec bundle (not project code), and the zipped snapshot `nps_tracker.zip`. Conventions below describe `nps_tracker/*.py`.

## Naming Patterns

**Files:**
- Pipeline steps use a numbered prefix: `step1_load_holdings.py`, `step4_map_codes.py`, `step5_shares.py`, `step6_daily_prices.py`, `step7_daily_value.py`, `step8_monthly_check.py`. Steps 2 and 3 have no file; their work is folded into step 1 (`step1_load_holdings.py`).
- External-API fetchers use `fetch_<thing>.py`: `fetch_listed.py`, `fetch_prices.py`, `fetch_official.py`, `fetch_votes.py`.
- Shared helpers use short nouns: `config.py`, `bases.py`, `krx_api.py` (API helper for data.go.kr), `nps_http.py` (HTTP helper for fund.nps.or.kr).
- Operational scripts use verbs: `record_daily.py`, `roll_year.py`, `build_dashboard.py`, `diagnose_key.py`.
- All file and module names are lowercase snake_case. Output CSVs are lowercase snake_case or `YYYYMM.csv` / `YYYY-MM-DD.csv` for dated data (`data/daily/202611.csv`, `data/source_records/2026-11-05.csv`).

**Functions:**
- snake_case verbs: `load_daily()`, `find_adjustments()`, `list_bases()`, `apply_reading()`, `fetch_all()`, `parse_items()`.
- Private helpers are prefixed with a single underscore: `_session` and `_TolerantTLS` in `nps_tracker/nps_http.py`.
- `main()` plus an `if __name__ == "__main__":` guard is the standard entry point (`nps_tracker/fetch_official.py`, `nps_tracker/step8_monthly_check.py`). Some scripts run top-level code instead (`nps_tracker/diagnose_key.py`, `nps_tracker/step1_load_holdings.py`); prefer `main()` for new scripts.

**Variables:**
- snake_case locals. Column-like variables often hold Korean-named DataFrame columns directly, e.g. `p.at[i, "보정배율"]`, `value["평가액_조"]`.
- Module-level constants are UPPER_SNAKE_CASE: `LOOKBACK_DAYS`, `CLOSE_TIME`, `EVENT_RATIO`, `LIMIT_MOVE`, `READING_KEYS`, `COLS`, `ATTEMPTS` (`nps_tracker/record_daily.py`, `nps_tracker/step7_daily_value.py`, `nps_tracker/nps_http.py`).
- Path and URL constants are defined only in `nps_tracker/config.py` and referenced as `config.<NAME>` (for example `config.DAILY_VALUE_CSV`, `config.STOCK_PRICE_URL`). Do not hard-code paths or URLs in step scripts.

**Types and data shapes:**
- Immutable records use `@dataclass(frozen=True)`: `Base` in `nps_tracker/bases.py`.
- Row-oriented data passed between functions is `list[dict]` (`nps_tracker/record_daily.py`), converted to a DataFrame only at I/O boundaries.
- Column names of the source data are Korean (`종목코드`, `보유주식수`, `평가액_조`, `보정배율`, `주식수배율`, `종가배율`). Keep these names exactly as they appear in the CSVs; do not translate them.
- Exchange/API field names keep their original English identifiers: `basDt`, `srtnCd`, `itmsNm`, `clpr`, `lstgStCnt`, `artclCn1`, `artclCn3`.

## Language of Comments and Messages

- Docstrings, comments, CLI messages, `SystemExit` text, and printed output are written in Korean. Keep new code consistent with this; English is used only for identifiers, API field names, and the reason-code strings (`"timeout"`, `"auth"`, `"rate_limit"`, `"offline"`, `"schema_error"`).
- Module docstrings are the primary documentation. Each script opens with a triple-quoted Korean docstring that shows the run command (`python step7_daily_value.py`), lists inputs and outputs, and states the rules the script enforces. See `nps_tracker/step7_daily_value.py`, `nps_tracker/record_daily.py`, `nps_tracker/roll_year.py`.

## Module Header Boilerplate

Every script begins with the same pattern, in this order:

```python
"""<한국어 docstring: 실행 방법, 입력, 출력, 규칙>"""
import sys                      # standard library first

import pandas as pd            # third-party next

import config                  # then project-local modules
import krx_api

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
```

- The `sys.stdout.reconfigure(encoding="utf-8")` guard is required in every executable script, because Korean output fails on the default Windows console encoding. Copy it verbatim into any new script that prints.
- Imports are grouped: standard library, then third-party, then project modules, separated by blank lines. Project modules are imported by bare name (`import config`, `import bases`); there are no packages or `__init__.py` files, so scripts run from inside `nps_tracker/`.
- `from typing import NoReturn` and `from dataclasses import dataclass` are used where needed; `from __future__ import annotations` is not used. Modern builtins are used directly (`list[dict]`, `dict | None`, `tuple[list[dict], int]`).

## Type Annotations

- Public functions carry return annotations and most parameter annotations: `def fetch_all(url: str, params: dict, rows_per_page: int = 1000, pause: float = 0.2) -> list[dict]:` in `nps_tracker/krx_api.py`; `def record(now: datetime | None = None) -> list[dict]:` in `nps_tracker/record_daily.py`.
- Use `NoReturn` for functions that always exit (`krx_api.fail`).
- No type checker is configured (no mypy/pyright config). Annotations are documentation, not enforced.
- Scripts that take no arguments and are only run from the CLI may omit annotations (`def main() -> None:` is common, but some older helpers have none).

## Configuration

- All tunables, paths, URLs, and reference values live in `nps_tracker/config.py`, with a Korean comment on the same line or the line above explaining the value's source and why it exists. Example: `CSV_ENCODING = "cp949"  # 이 파일은 UTF-8이 아니라 cp949라 지정이 필요하다`.
- Environment variables are used for secrets and for test-time overrides only: `DATA_GO_KR_KEY` (`config.API_KEY_ENV`) and `NPS_DATA_DIR` (alternate data folder during testing). Never write API keys to files, logs, or outputs.
- Corporate actions are data, not code: add mergers to `config.MERGERS` as tuples `(소멸 종목코드, 존속 종목코드, 비율, 신주 상장일)` with a Korean comment citing the source decision.

## Encoding and File I/O

- Raw government input is read with `encoding="cp949"` (`config.CSV_ENCODING`).
- Output and intermediate CSVs are written with `encoding="utf-8-sig"` (BOM included) so Excel opens them correctly. Read them with `encoding="utf-8-sig"` too.
- Read identifiers as strings to keep leading zeros and avoid float coercion: `pd.read_csv(..., dtype=str, keep_default_na=False)` or `dtype={"종목코드": str}`.
- Use `Path` objects from `pathlib` everywhere; do not build paths with string concatenation.
- Write atomically when a file is replaced in a scheduled job: write to `<name>.tmp`, then `os.replace(tmp, path)`. See `replace_file()` in `nps_tracker/record_daily.py` and the tmp-then-rename in `nps_tracker/record_daily.py` for raw responses.
- Use `lineterminator="\n"` for CSVs that are committed to git from the Linux runner, as in `raw.to_csv(tmp_raw, index=False, encoding="utf-8-sig", lineterminator="\n")`.

## Error Handling

**Fail loudly with a Korean message, never silently:**
- Missing prerequisite file: `raise SystemExit(f"파일이 없습니다: {path} (먼저 step7을 실행하세요)")`. Each message names the command that must run first. See `nps_tracker/step8_monthly_check.py`, `nps_tracker/step6_daily_prices.py`.
- Validation failure: raise `SystemExit` with the list of failed checks joined by `"; "` (see `nps_tracker/roll_year.py` near the `errors` join). Validation must complete before any file is written.
- Pure validators raise `ValueError` with a short Korean message; the caller decides whether to convert it into `SystemExit`. See `validate()` in `nps_tracker/record_daily.py`.

**API failures use a reason code:**
- `krx_api.fail(code, message)` writes the code to `data/collect_error.txt` and then raises `SystemExit`. Allowed codes are `timeout`, `auth`, `rate_limit`, `offline`, `schema_error`. Add new codes only if the dashboard (`nps_tracker/build_dashboard.py`) is updated to show them.
- Classify server text with `krx_api.classify(text)` rather than inspecting strings inline.
- Never put a URL with the service key into an exception message. Use `redact(text, key)` before printing any server response, and avoid `raise_for_status()` because its message includes the URL (see the comment in `krx_api.fetch_all`).

**Retries:**
- Transient HTTP and connection errors are retried with linearly growing sleeps: `time.sleep(5 * (attempt + 1))` (`nps_tracker/nps_http.py`, `nps_tracker/krx_api.py`). Retry constants are module-level (`ATTEMPTS = 4`).
- Give up by calling `fail()` or `raise SystemExit(...)`, not by returning `None`.

**Exception handling style:**
- Catch the narrowest exception that makes sense (`requests.RequestException`, `ValueError`, `(KeyError, TypeError)`).
- Broad `except Exception: pass` appears only around `sys.stdout.reconfigure` in the boilerplate. Do not add other broad catches.
- Use `raise ... from None` when converting an internal exception into a user-facing message (`nps_tracker/roll_year.py`).

**Failure side-effects:**
- A failed run must leave the previous good output untouched. Scheduled jobs (`.github/workflows/daily-update.yml`) continue with `continue-on-error: true` and rely on outputs not being overwritten. Preserve this: compute and validate first, then write.

## Logging and Output

- No `logging` module is used. Output is `print()` for progress and results, with Korean text and thousands separators where useful (`f"{len(api_rows):,}건"`).
- Print a one-line summary at the end of each step (see `nps_tracker/record_daily.py` `record()` and `nps_tracker/fetch_official.py` `main()`): what was written, where, and how many rows.
- Do not print secrets. Print key length or presence at most (`nps_tracker/diagnose_key.py`).

## Data Processing Conventions

- Use pandas for tabular work; use `numpy` for log/ratio math (`np.log`, `np.isnan`). Do not use `iterrows()` for heavy computation in new code, though `nps_tracker/step8_monthly_check.py` and `nps_tracker/fetch_official.py` use it on small tables.
- Explicit row-level state updates use `DataFrame.at[i, col]` inside loops (`nps_tracker/step7_daily_value.py`).
- Keep a run's derived results in named output files, and list the rules that produced them in the module docstring so a reviewer can reconstruct the logic.

## Comments

- Comments explain why, especially for data quirks and external-service behavior: `# API 종가가 수정주가가 아니므로...`, `# 12/31은 휴장일이라 종가가 없다`, `# 결과가 1건이면 dict로 오는 경우가 있다`.
- Inline magic numbers carry a Korean comment naming their source or meaning (`LIMIT_MOVE = 0.3    # 국내 가격제한폭(±30%)`).
- Section dividers and decorative banners are not used.
- No TODO/FIXME convention is in use.

## Function Design

- Functions are short and single-purpose, but several step scripts run long top-level flows; keep new logic inside functions so it can be imported and reused (`record(now=...)` accepts an injected clock for this reason).
- Accept an optional `now: datetime | None = None` (or similar) parameter instead of calling `datetime.now()` deep inside logic, so behavior can be driven from tests or fixtures.
- Return new lists or DataFrames rather than mutating inputs, except `find_adjustments(p)` which annotates the frame passed in; document such mutation in the docstring.

## Module Design

- No package structure and no `__init__.py`. Modules import each other by bare name.
- No barrel files and no re-exports.
- Each external system has one client module: `krx_api.py` (data.go.kr), `nps_http.py` (fund.nps.or.kr). Put new calls to these hosts there rather than calling `requests` directly. Only `krx_api.py`, `nps_http.py`, and the diagnostic script `diagnose_key.py` import `requests` today; the fetchers, `roll_year.py`, and `record_daily.py` go through the shared helpers.
- Scripts that other scripts need as a library expose their logic in functions and guard execution with `if __name__ == "__main__":`. Example: `step4_map_codes` is imported by `roll_year.py` (`import step4_map_codes as step4`).

## Formatting and Linting

- No formatter or linter configuration is committed (no `pyproject.toml`, `.flake8`, `ruff.toml`, `.pylintrc`, or `.editorconfig`). `.vscode/settings.json` only sets `python.terminal.useEnvFile`.
- Observed style: 4-space indentation, double quotes for strings, lines up to roughly 120 characters, trailing commas on multi-line literals.
- Follow the observed style. If a formatter is adopted later, record it here.

## Dependencies

- Runtime dependencies are pinned by lower bound only in `nps_tracker/requirements.txt`: `pandas>=2.0`, `requests>=2.31`.
- Standard library is preferred for everything else (`zipfile`, `xml.etree.ElementTree`, `dataclasses`, `pathlib`, `hashlib`).

## Do This, Not That

- Do: `pd.read_csv(path, dtype=str, encoding="utf-8-sig", keep_default_na=False)`. Not: `pd.read_csv(path)` (loses leading zeros and mangles Korean headers).
- Do: `raise SystemExit("<한국어 메시지>")` for expected failures. Not: a bare `assert` or `print` followed by a normal return.
- Do: `krx_api.fail("schema_error", ...)` when the API changes shape. Not: `KeyError` escaping to the user.
- Do: add new reference values to `config.py` with a source comment. Not: hard-code them in a step script.

---

*Convention analysis: 2026-11-06*
