---
last_mapped_commit: 3b3c85edda38a57a806408b9d0d4b866e51418af
last_mapped_at: 2026-11-06
---
# Codebase Concerns

**Analysis Date:** 2026-11-06

Scope: the whole repository. The only code is the Python pipeline in `nps_tracker/`, the daily GitHub Actions workflow in `.github/workflows/daily-update.yml`, and committed data under `nps_tracker/data/`. `aleph-state/` holds a public fixture kit and a graded spec for a separate exercise and is not part of the runtime pipeline. Items marked "local" refer to generated files that are gitignored and only exist on a machine that has run the pipeline.

## Tech Debt

**No automated tests anywhere in the repository:**
- Issue: `git ls-files` contains no test files. The only test-like artifacts are the synthetic fixtures in `nps_tracker/fixtures/*.json`, which drive the replay UI in `nps_tracker/build_dashboard.py`, not a test harness. Correctness of the valuation math rests on manual review of console output.
- Files: `nps_tracker/step7_daily_value.py`, `nps_tracker/record_daily.py`, `nps_tracker/roll_year.py`, `nps_tracker/step5_shares.py`
- Impact: Any change to the adjustment logic (`offsets`, `find_adjustments`, merger handling in `evaluate`) can silently change the published total. The daily job publishes whatever it computes.
- Fix approach: Add a `tests/` folder with pytest cases built from the fixtures and from a small hand-computed holdings sample. Start with `offsets()`, `find_adjustments()`, `apply_reading()`, `validate()` in `record_daily.py`, and `parse_holdings()` in `roll_year.py`.

**Duplicated valuation logic between `step5_shares.py` and `roll_year.py`:**
- Issue: The shares formula (`평가액 * 1e8 / 종가`), the cross-check, and the `CONFIRMED` set are implemented twice. `roll_year.build_shares()` and `roll_year.validate()` mirror `step5_shares.main()`. The same `CONFIRMED = {"manual", "exact", "normalized"}` set is also defined in `nps_tracker/step4_map_codes.py` and `nps_tracker/roll_year.py`. `CHECK_MIN_EOK` and `CHECK_TOL` are defined in both `step5_shares.py` and `roll_year.py`.
- Files: `nps_tracker/step5_shares.py`, `nps_tracker/roll_year.py`, `nps_tracker/step4_map_codes.py`
- Impact: A fix made in one copy will not reach the other. The 2025 base is built by `step5_shares.py`, while every later base is built by `roll_year.py`, so the two paths can diverge.
- Fix approach: Move the shared formula and constants into one module (for example `nps_tracker/valuation.py`) and call it from both scripts. Delete `step5_shares.py` once the 2025 base is confirmed to be reproducible by `roll_year.build_shares()`.

**Stale committed snapshot of the project:**
- Issue: `nps_tracker.zip` at the repository root is a full copy of an earlier version of the code, committed alongside the live `nps_tracker/` folder.
- Files: `nps_tracker.zip`, `nps_tracker/`
- Impact: Two sources of truth. Readers may open the zip and assume it is current.
- Fix approach: Remove the zip from the repository (`git rm nps_tracker.zip`) if it is not needed as a delivery artifact, or document it as a frozen archive in `nps_tracker/README.md`.

**`build_dashboard.py` mixes Python generation with about 500 lines of inline HTML, CSS, and JavaScript:**
- Issue: `TEMPLATE` is a raw string in `nps_tracker/build_dashboard.py` (roughly lines 146 to the end). It contains the layout, styles, and all client-side rendering, including the replay state machine (`sequence`, `runFixture`, `applyFail`, `applyGood`).
- Files: `nps_tracker/build_dashboard.py`
- Impact: Front-end changes cannot be linted, type-checked, or tested separately. The `sequence()` helper is hard to read (`id === 'T04-NORMAL-D1-B' ? [] : [id]`), and a small error there changes replay output silently.
- Fix approach: Move the template to `nps_tracker/templates/index.html` and the JavaScript to a separate file that the builder inlines. Keep the Python side to data shaping only.

**Hard-coded numbers and dates in `config.py`:**
- Issue: `OFFICIAL_TOTAL_JO = 263.737`, `PRICE_DATE = "20251230"`, `BASE_DATE`, `VOTES_START = "2026-01-01"`, and the `MERGERS` list (six entries with effective dates such as `"20260811"`) are edited by hand. The `OFFICIAL_MONTHLY` list is also manual.
- Files: `nps_tracker/config.py`
- Impact: Every new merger, every new official monthly figure, and every new year requires a manual edit to config, with no check that the edit is complete. The README (`nps_tracker/README.md`, section 8) states this is still manual.
- Fix approach: Add a consistency check in `step7_daily_value.py` that compares `MERGERS` with the `share_events.csv` entries marked "미반영" for the same stock and prints a warning when a likely merger is unlisted. Keep the manual list but validate it.

## Known Bugs and Data-Accuracy Issues

**Votes scraper can record a meeting with zero items and never retry it:**
- Symptoms: If the detail page layout changes, or a single request returns an unexpected page, `fetch_items()` returns an empty list. `main()` still appends that meeting to `new_m` with `안건수 = "0"`, and the next run treats it as already fetched (the `have` set is built from `old_m`). No error is raised and the workflow step succeeds.
- Files: `nps_tracker/fetch_votes.py` (`fetch_items`, `main`), `nps_tracker/build_dashboard.py` (`votes_payload`)
- Trigger: A transient or structural HTML change on `fund.nps.or.kr` during the run.
- Workaround: Delete the affected rows from `nps_tracker/data/votes_meetings.csv` and `nps_tracker/data/votes_items.csv` and re-run `python fetch_votes.py`.

**Silent success when the vote list page changes shape:**
- Symptoms: `list_meetings()` returns an empty frame if `DETAIL_RE` matches nothing. `main()` then prints "새로 받을 주총 0건" and exits 0. The dashboard keeps showing old vote data and no failure is flagged.
- Files: `nps_tracker/fetch_votes.py` (`list_meetings`, `main`)
- Trigger: Any change to the list page markup or its `fnc_goDetail(...)` call.
- Workaround: Compare `홈페이지 목록 N건` in the job log with the expected count.

**Price collection accepts an incomplete trading day permanently:**
- Symptoms: `step6_daily_prices.py` marks a date as done as soon as it has saved any rows for held stocks (`have = set(old["basDt"])`). If the API returned a partial page for a trading day, that day is never refetched. `step7_daily_value.py` then forward-fills the missing closes from the previous day (`price.ffill()`), so the published daily total is flat for those stocks without any warning.
- Files: `nps_tracker/step6_daily_prices.py` (`main`, `save`), `nps_tracker/step7_daily_value.py` (`evaluate`)
- Trigger: A short or empty page from the price API on a day that does have trading data. `fetch_all` only checks `totalCount` on the first page and does not compare the number of rows received with the number of held stocks expected.
- Workaround: Remove that date's rows from `nps_tracker/data/daily/YYYYMM.csv` and re-run `step6_daily_prices.py`.

**Holidays are re-requested on every run:**
- Symptoms: Dates with no data are not recorded, so `todo` contains them again on every run. Each daily run makes one extra API call per holiday since the day after the 2025 base date (2025-12-31). This is wasteful and uses up the daily quota that `record_daily.py` also needs.
- Files: `nps_tracker/step6_daily_prices.py` (`main`, `holidays` list, `todo` comprehension)
- Trigger: Every run.
- Workaround: None needed for correctness. Record non-trading dates in a small `data/non_trading_days.csv` and exclude them from `todo`.

**Unreflected share changes are not surfaced in the dashboard:**
- Symptoms: The local `nps_tracker/data/share_events.csv` contains 24 rows marked "미반영(확인 필요)" for the 2025 base, with a combined 2025-base valuation of roughly 10,000 억 원. The largest include 한화솔루션 (about 2,605 억 원), SKC (about 2,590 억 원), and SNT다이내믹스 (about 1,281 억 원). These stocks keep the 2025 share count, so the published daily total may be overstated or understated. `build_dashboard.py` does not read `share_events.csv`, so no page visitor sees this.
- Files: `nps_tracker/step7_daily_value.py` (`find_adjustments`, `main`), `nps_tracker/build_dashboard.py` (`main`, inputs list in the docstring)
- Trigger: Any capital change that is not a split, merger, or bonus issue. The code keeps the share count unchanged, which is correct for a non-participating rights issue but wrong for a capital reduction (감자) or a participating holder.
- Workaround: Review `share_events.csv` after each run and add manual overrides to `config.MERGERS`, or extend `find_adjustments` with explicit rules.

**`source_time` is synthesized and presented as an observed time:**
- Symptoms: `record_daily.py` sets `source_time` to the trading date plus `15:30:00+09:00` (`CLOSE_TIME`), because the API does not return a time. The dashboard shows this as "출처 시각" with "Asia/Seoul" appended, which reads as a real observation timestamp.
- Files: `nps_tracker/record_daily.py` (`CLOSE_TIME`, `record`), `nps_tracker/build_dashboard.py` (JavaScript `add('출처 시각', ...)`)
- Trigger: Every successful run.
- Workaround: Label the field as an assumed close time, or change the displayed label to "거래일 장 마감 시각(추정)".

**Same-day re-run overwrites the raw source snapshot:**
- Symptoms: The docstring and the README say the raw response is preserved and the first record is kept. In `record()`, `os.replace(tmp_raw, source)` overwrites `data/source_records/YYYY-MM-DD.csv` on every successful run that day. `raw_sha256`, `response_rows`, and `trade_date` in `daily_record.csv` are then updated to the latest response, so the earlier response is lost.
- Files: `nps_tracker/record_daily.py` (`record`, `apply_reading`)
- Trigger: A second successful run on the same Asia/Seoul date.
- Workaround: Keep the first snapshot by writing `source_records/YYYY-MM-DD.first.csv` only when the file does not yet exist.

**Official monthly figures are labelled inconsistently:**
- Symptoms: `nps_tracker/config.py` marks the 2026-05 figure (543.635 조) as "공식", but its source is a newspaper report ("머니투데이 2026.7.30 보도"). The 2026-02 figure (395.1 조) is "참고" with no original source. Values for the 2026 months also do not follow a smooth series: 263.7 (Dec 2025), 395.1 (Feb), 543.6 (May), 418.6 (Jul), 433.8 (Aug). Between May and July the figure falls by about 23%, and June is missing. The config comments say press figures for 5% holders are excluded, but the trust label does not show whether scope was checked.
- Files: `nps_tracker/config.py` (`OFFICIAL_MONTHLY`), `nps_tracker/step8_monthly_check.py` (`official_list`), `nps_tracker/build_dashboard.py` (JavaScript `o.trust === '공식'`)
- Trigger: Any new monthly figure added by hand.
- Workaround: Mark press figures as "참고" in `OFFICIAL_MONTHLY` and keep them out of the "공식" comparison.

**Auto-collected official value is always labelled "공식":**
- Symptoms: `step8_monthly_check.official_list()` gives every row in `data/official_monthly.csv` the trust value "공식", regardless of origin.
- Files: `nps_tracker/step8_monthly_check.py` (`official_list`)
- Trigger: Every run.
- Workaround: Keep the label but read it from the source column, or treat homepage values as "공식" only after confirming the page text.

**Collect error file is never cleared on success:**
- Symptoms: `krx_api.fail()` writes `data/collect_error.txt`, but no code deletes it on a successful run. In CI the file is never committed (it is gitignored) and each run starts with a fresh checkout, so this does not affect the published page. On a local machine, a stale code can remain after a successful run and be read by `run_status()` if the next local build sees a failure outcome.
- Files: `nps_tracker/krx_api.py` (`fail`), `nps_tracker/build_dashboard.py` (`run_status`), `nps_tracker/config.py` (`COLLECT_ERROR_FILE`)
- Trigger: A failed local run followed by a successful run, then a local build with the outcome environment variables set to failure.
- Workaround: Delete `nps_tracker/data/collect_error.txt` before a local build, or clear it at the start of `step6_daily_prices.py`.

**Failed push leaves the published page one day behind the data:**
- Symptoms: The data commit step runs `git pull --rebase --autostash -q` and `git push` without checking the result. If the push fails after the pages artifact is produced, the job fails, but the Pages deploy job (`needs: build`) does not run, so the public page keeps the previous day's content while `data/` in the repository is one day behind the artifact.
- Files: `.github/workflows/daily-update.yml` (step "새 데이터 커밋", jobs `build` and `deploy`)
- Trigger: A concurrent push to `main` during the run.
- Workaround: Re-run the workflow from the Actions tab. The `concurrency` group already prevents two daily runs from overlapping.

## Security Considerations

**API key is passed in the query string:**
- Risk: `krx_api.fetch_all()` sends `serviceKey` as a URL parameter. Any library-level logging, proxy log, or unhandled exception that prints the request URL would expose the key. The code avoids this by printing only exception class names (`type(e).__name__`) and by redacting response bodies with `redact()`, but the protection depends on every caller following that rule.
- Files: `nps_tracker/krx_api.py` (`fetch_all`, `redact`, `fail`), `nps_tracker/diagnose_key.py` (prints `키 길이`, `% 포함`, and the response message)
- Current mitigation: The key comes only from the `DATA_GO_KR_KEY` environment variable and GitHub Actions secrets. `redact()` strips the key in three encodings. A search of the repository found no key values in `nps_tracker/data/` or the source files (only code references to the variable name).
- Recommendations: Send the key in a request header if the provider supports it. Otherwise, wrap `requests` calls so that `requests` logging is set to WARNING at most, and add a test that checks `redact()` on a sample URL.

**TLS truncation detection is disabled for the official site:**
- Risk: `nps_tracker/nps_http.py` sets `ssl.OP_IGNORE_UNEXPECTED_EOF` on the context used for `fund.nps.or.kr`. This accepts connections closed without a TLS close-notify, so a truncated response is no longer reported as an error at the transport layer. The downloaded holdings workbook (`roll_year.py`) and the JSON and HTML responses rely on later parsing to catch truncation.
- Files: `nps_tracker/nps_http.py` (`_TolerantTLS`)
- Current mitigation: The module comment explains the reason (the site drops connections from GitHub-hosted runners). Certificate verification is still on. The xlsx reader requires a valid zip structure, and `roll_year.py` checks for the `PK` signature.
- Recommendations: After download, verify the workbook's size against the `Content-Length` header when it is present, and verify the zip end-of-central-directory record before parsing.

**Integrity of the holdings workbook is not checked:**
- Risk: `roll_year.py` accepts whatever workbook the homepage serves for a year, provided it passes the structural checks (year label, row count, 99.5% mapping, 95 to 105% of the official total, share cross-check). A wrong but well-formed file would pass only if it also matched the total, which limits but does not remove the risk.
- Files: `nps_tracker/roll_year.py` (`available_files`, `main`)
- Current mitigation: Multi-step validation before anything is written.
- Recommendations: Store the SHA-256 of each accepted workbook in `data/bases/YYYY/source.json` so later runs can detect a changed file.

**Third-party font loaded from a mutable CDN tag without Subresource Integrity:**
- Risk: `nps_tracker/build_dashboard.py` links a Pretendard stylesheet from `cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/...` with no `integrity` attribute. A tag can be re-pointed, and the page would load changed CSS on every visit.
- Files: `nps_tracker/build_dashboard.py` (`<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/...">`)
- Current mitigation: The README says the page falls back to system fonts if the CDN is unreachable.
- Recommendations: Add an `integrity="sha384-..."` attribute and `crossorigin="anonymous"`, or self-host the subset.

**Actions are pinned to major tags only:**
- Risk: `.github/workflows/daily-update.yml` uses `actions/checkout@v4`, `actions/setup-python@v5`, `actions/configure-pages@v5`, `actions/upload-pages-artifact@v3`, and `actions/deploy-pages@v4`. Tags can be moved by the publisher. The job also has `contents: write`, `pages: write`, and `id-token: write` permissions.
- Files: `.github/workflows/daily-update.yml`
- Current mitigation: The workflow runs only on schedule and manual dispatch, not on pull requests from forks.
- Recommendations: Pin each action to a full commit SHA, and grant `id-token: write` only to the deploy job.

## Performance Bottlenecks

**Repository growth from committed raw snapshots:**
- Problem: Every successful run commits a full raw response to `nps_tracker/data/source_records/YYYY-MM-DD.csv`. One sample file, `2026-11-05.csv`, is about 332 KB. Trading days run about 250 times a year, so this adds roughly 80 MB of git history per year on top of the daily CSVs.
- Files: `nps_tracker/record_daily.py` (`record`), `nps_tracker/data/source_records/`, `.github/workflows/daily-update.yml` (step "새 데이터 커밋")
- Cause: `record_daily.py` stores the entire KRX-wide response (about 2,900 rows) rather than only the held stocks.
- Improvement path: Store only the held stocks' rows in the committed snapshot and keep the full response out of git (for example in a release asset), keeping its SHA-256 in `daily_record.csv`.

**Every monthly price file is rewritten on each run:**
- Problem: `step6_daily_prices.save()` rewrites every `data/daily/YYYYMM.csv` file on every run, even when only the current month changed. Git sees a full-file diff for each month touched.
- Files: `nps_tracker/step6_daily_prices.py` (`save`)
- Cause: `save()` groups all rows and writes every month.
- Improvement path: Write only months that received new rows, by comparing against the rows already on disk.

**Full-history recomputation in step 7:**
- Problem: `step7_daily_value.py` reloads all of `data/daily/*.csv` and recomputes every base from its base date on each run. It also runs `find_adjustments`, which scans the whole series per stock with a nested loop over up to `BONUS_LOOKBACK` rows.
- Files: `nps_tracker/step7_daily_value.py` (`load_daily`, `evaluate`, `find_adjustments`)
- Cause: No caching of results between runs.
- Improvement path: Acceptable at the current size (about 1,200 holdings and about 210 trading days). Revisit if the series grows, by evaluating only dates after the last stored row.

## Fragile Areas

**Scraping of the official homepage:**
- Files: `nps_tracker/roll_year.py` (`available_files`, regex on `fileDown.do`), `nps_tracker/fetch_official.py` (regex on `YYYY년 M월 말 기준`), `nps_tracker/fetch_votes.py` (`DETAIL_RE`, `fnc_goDetail(...)`, `<tr>` parsing)
- Why fragile: Each parser depends on exact markup and Korean labels. `fetch_votes.py` fails silently when a pattern does not match (see Known Bugs). `roll_year.py` uses `re.search(r"(20\d\d)\s*년\s*말\s*기준", ...)` on the first six rows, so a relabelled header stops the year roll.
- Safe modification: Change one parser at a time and run it against a saved HTML copy. Add a minimum-result check (for example, fail if the list page returns zero meetings when the previous run had any).
- Test coverage: None.

**Event detection in step 7:**
- Files: `nps_tracker/step7_daily_value.py` (`EVENT_RATIO`, `LIMIT_MOVE`, `BONUS_LOOKBACK`, `offsets`, `find_adjustments`)
- Why fragile: Splits, mergers, bonus issues, and rights issues are distinguished only by the ratio of share count change to price change, with fixed thresholds. The 0.5 and 0.05 constants in `offsets()` and the 1.3 event ratio determine which events are auto-applied. A change in these values changes published totals with no test to show the effect.
- Safe modification: Change one constant at a time, re-run `step7_daily_value.py`, and compare `data/share_events.csv` before and after.
- Test coverage: None. This is the highest-risk module for silent numerical error.

**Merger handling depends on a manual list:**
- Files: `nps_tracker/config.py` (`MERGERS`), `nps_tracker/step7_daily_value.py` (merger loop in `evaluate`)
- Why fragile: A merger that is not in `MERGERS` is treated as a delisting and frozen at the last close (`stale` flag), which is wrong when shares were exchanged. The `stale` count appears on the page as "종가 고정" but does not say why.
- Safe modification: Add the entry to `MERGERS` with the same ratio and date used in the company's notice. Check `data/latest_holdings.csv` afterwards for `종가고정 = True`.
- Test coverage: None.

**`parse_holdings()` percent detection:**
- Files: `nps_tracker/roll_year.py` (`parse_holdings`, `number`)
- Why fragile: The stake column is rescaled by a heuristic (`df["지분율"].max() <= 1`) because some years store 7.76% as 0.0776. A year where every stake is below 1% would be mis-scaled, and the mismatch would only show in the cross-check.
- Safe modification: Read the header cell's number format from the workbook instead of inferring it from values.
- Test coverage: None.

## Scaling Limits

**Single-run, single-machine pipeline:**
- Current capacity: About 1,200 holdings in `data/latest_holdings.csv`, about 210 trading days from 2026-01-02, one daily job.
- Limit: The job's total time and API quota (`공공데이터포털` daily limits) are not documented. The `LIMITED_NUMBER_OF_SERVICE_REQUESTS` error is detected in `krx_api.classify()`, but no retry-after logic exists for it, unlike the homepage fetcher.
- Scaling path: Add a rate-limit backoff with a longer wait for `rate_limit`, and record the daily request count in the collect status.

**Git as the database:**
- Current capacity: About 23 commits on `main`, with daily CSVs, source snapshots, and vote data stored in git.
- Limit: Repository size grows with the raw snapshots (see Performance). Clone and CI checkout time grow with it.
- Scaling path: Move `source_records/` out of git (see Performance), and consider storing the daily series in one append-only CSV rather than monthly files.

## Dependencies at Risk

**Public-data API version pinning:**
- Risk: The code uses `GetStockSecuritiesInfoService_V2/getStockPriceInfo_V2` and `GetKrxListedInfoService_V2/getItemInfo_V2`. `nps_tracker/diagnose_key.py` was written to compare against an older address, which suggests the endpoints have already changed once. `nps_tracker/README.md` states that `KRX_LISTED_URL` was recalled from memory and must be checked.
- Impact: If the provider retires the V2 path, `fetch_all()` gets an HTTP error or an unexpected body, `classify()` returns `schema_error`, and the daily totals stop updating. The page then shows "오래된 값" with no further detail.
- Migration plan: Keep `diagnose_key.py` as the first check after a failure, and record the endpoint version and the date it was last verified in `nps_tracker/config.py`.

**Python package versions unpinned:**
- Risk: `nps_tracker/requirements.txt` lists `pandas>=2.0` and `requests>=2.31` with no upper bound. CI installs whatever is newest and uses Python 3.13.
- Impact: A future pandas behaviour change (for example in `groupby(...).shift()` or CSV reading with `dtype=str`) could change published numbers without a code change.
- Migration plan: Pin exact versions in a lock file and run `step7_daily_value.py` against a known-good `data/daily` snapshot after every upgrade.

## Missing Critical Features

**No notification when a computed value is suspicious:**
- Problem: `step7_daily_value.py` prints warnings about unreflected events and implausible daily moves (`±30%` after adjustment), but the workflow does not read those warnings. Only collection failures make the job fail.
- Blocks: Detection of a wrong adjustment before it is published. The page shows the number as if it were verified.

**No record of which official workbook each base came from:**
- Problem: `data/bases/YYYY/` stores `shares.csv` and `prices.csv` but not the source file's URL, hash, or retrieval date.
- Blocks: Reproducing or auditing a base year after the homepage replaces the file.

**No user-facing statement on the page about unreflected events or press-sourced figures:**
- Problem: The dashboard shows the total and monthly comparisons, but does not say how many holdings are frozen, how many share events are pending, or which official figures came from newspapers beyond the "참고용" note in the table.
- Blocks: Readers cannot judge the accuracy of the total.

## Test Coverage Gaps

**Valuation logic (`step7_daily_value.py`):**
- What's not tested: `offsets()`, `find_adjustments()` (split, bonus issue, and rights issue paths), and the merger branch of `evaluate()`.
- Files: `nps_tracker/step7_daily_value.py`
- Risk: A wrong adjustment changes the published total for hundreds of billions of won without any error.
- Priority: High

**Daily record validation and idempotency (`record_daily.py`):**
- What's not tested: `validate()` rejects bad readings, `apply_reading()` updates the same day in place and creates a new row on a new day, and `replace_file()` leaves the previous file intact on failure.
- Files: `nps_tracker/record_daily.py`
- Risk: The public "daily record" contract (one row per Asia/Seoul date) can break silently.
- Priority: High

**Base rollover (`roll_year.py`):**
- What's not tested: `parse_holdings()` on a saved workbook, `number()` formats, and the validation thresholds in `validate()`.
- Files: `nps_tracker/roll_year.py`
- Risk: A malformed year file is rejected only if it trips a threshold. A correct file with an unexpected label can also be rejected, and the workflow then keeps the old base.
- Priority: High

**Scrapers (`fetch_votes.py`, `fetch_official.py`):**
- What's not tested: Parsing of saved copies of the list page, detail page, and asset-size JSON.
- Files: `nps_tracker/fetch_votes.py`, `nps_tracker/fetch_official.py`
- Risk: The silent-zero failures described under Known Bugs.
- Priority: Medium

**Dashboard data shaping (`build_dashboard.py`):**
- What's not tested: `decide()` for vote results, `votes_payload()` quarter grouping, and `run_status()` error-code mapping.
- Files: `nps_tracker/build_dashboard.py`
- Risk: Incorrect vote counts or error labels on the public page.
- Priority: Medium

---

*Concerns audit: 2026-11-06*
