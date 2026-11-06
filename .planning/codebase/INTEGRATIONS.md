---
last_mapped_commit: 3b3c85edda38a57a806408b9d0d4b866e51418af
last_mapped_at: 2026-11-06
---
# External Integrations

**Analysis Date:** 2026-11-06

## APIs & External Services

**Public data portal (data.go.kr) - Financial Commission KRX listing and price APIs:**
- `금융위원회_KRX상장종목정보` (GetKrxListedInfoService_V2) - listed-stock master for the base date
  - Endpoint: `https://apis.data.go.kr/1160100/GetKrxListedInfoService_V2/getItemInfo_V2` (`nps_tracker/config.py`, `KRX_LISTED_URL`)
  - Called from: `nps_tracker/fetch_listed.py` via `krx_api.fetch_all`
- `금융위원회_주식시세정보` (GetStockSecuritiesInfoService_V2) - daily stock closing prices
  - Endpoint: `https://apis.data.go.kr/1160100/GetStockSecuritiesInfoService_V2/getStockPriceInfo_V2` (`config.py`, `STOCK_PRICE_URL`)
  - Called from: `nps_tracker/fetch_prices.py` (base date `20251230`), `nps_tracker/step6_daily_prices.py` (one call per trading day, `basDt=YYYYMMDD`, 5000 rows/page), `nps_tracker/roll_year.py` (price lookup for new-year rebasing), `nps_tracker/record_daily.py` (today's recorded value, up to a 10-day lookback)
  - SDK/Client: none; raw `requests.get` in `nps_tracker/krx_api.py`
  - Auth: `DATA_GO_KR_KEY` query parameter `serviceKey` (Decoding key; `krx_api.py` warns that Encoding keys double-encode)
  - Request params: `resultType=json`, `numOfRows`, `pageNo`, `basDt`
  - Error classification: HTTP 401/403 -> `auth`, 429 -> `rate_limit`, body text matched for `LIMITED_NUMBER_OF_SERVICE_REQUESTS` / `SERVICE_KEY_IS_NOT_REGISTERED` / `SERVICE_ACCESS_DENIED`; timeouts -> `timeout`; connection failures -> `offline`
- Failure codes are written to `nps_tracker/data/collect_error.txt` (gitignored) for the dashboard status display

**National Pension Service Fund Management Headquarters website (fund.nps.or.kr) - scraped public pages:**
- Holdings file index (annual "투자종목" download page): `https://fund.nps.or.kr/oprtprcn/ivsmprcn/getOHED0003M0.do` (`config.HOLDINGS_PAGE_URL`), parsed with regex in `nps_tracker/roll_year.py` (`available_files`); files downloaded from `https://fund.nps.or.kr/fileDown.do?...` (`config.HOLDINGS_FILE_BASE`) and read as XLSX via `zipfile` + ElementTree
  - Called from: `nps_tracker/roll_year.py`
- Asset-class size chart (domestic equity AUM, 십억 원 per year): `POST https://fund.nps.or.kr/oprtprcn/ivsmprcn/chartOHED0016P0.do` with JSON body `{"searchGbu": "5", "cartMngSn": "1"}` (`config.OFFICIAL_SIZE_URL`)
  - Called from: `nps_tracker/fetch_official.py`, `nps_tracker/roll_year.py`
- "Month-end basis" label page: `GET https://fund.nps.or.kr/oprtprcn/ivsmprcn/getOHED0016M0.do` (`config.OFFICIAL_MONTH_URL`), regex for `YYYY년 M월 말 기준`
  - Called from: `nps_tracker/fetch_official.py`
- Domestic shareholder voting disclosures:
  - List: `https://fund.nps.or.kr/impa/edwmpblnt/empty/getOHEF0007M0.do` (`config.VOTES_LIST_URL`)
  - Detail: `https://fund.nps.or.kr/impa/edwmpblnt/getOHEF0010M0.do` (`config.VOTES_DETAIL_URL`)
  - Called from: `nps_tracker/fetch_votes.py` (POST, HTML parsed with regex and `html.unescape`)
  - Only meetings from `config.VOTES_START` (`2026-01-01`) onward are collected
- Client helper: `nps_tracker/nps_http.py` - shared `requests.Session` with a tolerant TLS adapter (`ssl.OP_IGNORE_UNEXPECTED_EOF`, certificate verification kept on), up to 4 attempts with 5/10/15 s backoff, 30 s default timeout. Fails with `SystemExit` after exhausting attempts.

**Google Fonts-equivalent CDN (jsDelivr):**
- Pretendard variable font CSS: `https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css`
  - Referenced in the generated page `<link rel="stylesheet">` inside `nps_tracker/build_dashboard.py` (around line 151)
  - Falls back to system fonts if unavailable (per `nps_tracker/README.md`)

**Manual / reference data (not fetched at runtime):**
- `OFFICIAL_MONTHLY` in `nps_tracker/config.py` - hand-entered reference values with source citations (NPS portfolio page, Money Today news reports, fund-management HQ portfolio status)
- `MERGERS` in `nps_tracker/config.py` - merger/share-exchange parameters entered by hand from disclosures

## Data Storage

**Databases:**
- None. No database server, ORM, or migration tool.
- Persistence is flat CSV files under `nps_tracker/data/`:
  - Inputs: `data/raw/nps_domestic_stock_20251231.csv` (cp949, from the public data portal)
  - Committed by the bot: `data/shares.csv`, `data/prices_20251230.csv`, `data/daily/YYYYMM.csv`, `data/daily_record.csv`, `data/source_records/YYYY-MM-DD.csv`, `data/votes_meetings.csv`, `data/votes_items.csv`, `data/official_monthly.csv`, `data/bases/YYYY/`
  - Gitignored intermediates: `holdings_clean.csv`, `listed_*.csv`, `mapping*.csv`, `manual_map.csv` (human-authored, committed when present), `daily_value.csv`, `share_events.csv`, `monthly_check.csv`, `latest_holdings.csv`, `collect_error.txt`
- Written in CI by `git add -A data` followed by commit `data: 자동 갱신 YYYY-MM-DD` and `git push` (after `git pull --rebase --autostash`)

**File Storage:**
- Local filesystem only (plus the repository itself as versioned storage for `data/`)

**Caching:**
- None at the service level. `actions/setup-python` caches the pip download cache keyed on `nps_tracker/requirements.txt`.
- Incremental fetch logic acts as a data-level cache: `step6_daily_prices.py` skips dates already present in `data/daily/`.

## Authentication & Identity

**Auth Provider:**
- No end-user authentication. The dashboard is a public static page.
- Upstream API auth: data.go.kr service key (`DATA_GO_KR_KEY`), passed as the `serviceKey` query parameter.
- GitHub Actions authentication to the repo: built-in `GITHUB_TOKEN` (write scopes `contents`, `pages`, `id-token`); the workflow uses `actions/checkout@v4` default credentials for the push step.
- Commit identity: `github-actions[bot] <41898282+github-actions[bot]@users.noreply.github.com>`.

**Secret handling rules (from code comments):**
- Key is read only from the environment (`krx_api.get_key`); never written to files, logs, or fixtures.
- Error output is passed through `krx_api.redact`, which masks the raw, URL-quoted, and `quote_plus` forms of the key before printing server responses.
- `record_daily.py` stores only the query-free endpoint path in source records.
- `.gitignore` excludes `.env`.

## Monitoring & Observability

**Error Tracking:**
- None (no Sentry or similar).

**Logs:**
- Plain `print` to stdout inside GitHub Actions job logs.
- Per-step outcomes are recorded in `site/status.json` (generated in the workflow, from `steps.<id>.outcome`) and displayed on the dashboard.
- Collection failure codes are persisted in `nps_tracker/data/collect_error.txt` (gitignored).
- Alerting: the `report` job in the workflow fails deliberately when any collection step fails, which triggers GitHub's default workflow-failure email notification.

## CI/CD & Deployment

**Hosting:**
- GitHub Pages, deployed via `actions/configure-pages@v5`, `actions/upload-pages-artifact@v3` (path `nps_tracker/site`), and `actions/deploy-pages@v4` (environment `github-pages`). Pages Source must be set to "GitHub Actions" in repository settings.
- Repository: `https://github.com/Jin050310/daliy-dashboard` (git remote `origin`).

**CI Pipeline:**
- GitHub Actions, single workflow `.github/workflows/daily-update.yml` named `daily-update`
- Triggers: `schedule` cron `30 6 * * 1-5` (UTC, weekdays 15:30 KST) and `workflow_dispatch`
- Jobs: `build` (ubuntu-latest, all collection and build steps; `continue-on-error` on roll, prices, votes, official, record), `deploy` (needs build), `report` (needs build and deploy; fails only if `collect_failed == 'true'`)
- Step order: roll_year -> step6 daily prices -> fetch_votes -> fetch_official -> step7 daily value -> record_daily (only if prices succeeded) -> step8 monthly check + build_dashboard -> status.json -> commit and push data -> Pages upload

**Local development:**
- Manual runs follow `nps_tracker/README.md`; `git pull` is required before local work because the bot commits `data/`.

## Environment Configuration

**Required env vars:**
- `DATA_GO_KR_KEY` - required by `roll_year.py`, `step6_daily_prices.py`, `fetch_prices.py`, `fetch_listed.py`, `record_daily.py` (via `krx_api.get_key`). Not required by `step1_load_holdings.py`, `fetch_votes.py`, `fetch_official.py` (these hit fund.nps.or.kr only).

**Optional env vars:**
- `NPS_DATA_DIR` - alternate data directory for testing
- `PRICES_OUTCOME`, `RECORD_OUTCOME` - set by the workflow for `build_dashboard.py`
- `TZ` - `Asia/Seoul` in CI

**Secrets location:**
- GitHub repository secret `DATA_GO_KR_KEY` (Settings > Secrets and variables > Actions)
- Local: operator-defined shell environment variable (PowerShell `$env:DATA_GO_KR_KEY`, or `export` on POSIX), per `nps_tracker/README.md`
- No `.env` file is committed; `.env` is gitignored. Do not record key values in any tracked file.

## Webhooks & Callbacks

**Incoming:**
- None. The only triggers are the GitHub Actions cron schedule and manual `workflow_dispatch`.

**Outgoing:**
- None from application code. Outbound HTTP is limited to the data.go.kr API and fund.nps.or.kr pages listed above.
- Failure notifications are indirect (GitHub email on failed workflow run).

## Other Repository-Hosted Integrations

- `aleph-state/` contains a public synthetic fixture bundle (`public-contract (1).json`, `asset-manifest (1).json`, `README (2).md`, and a zipped board package) for a separate "T04" exercise. Its README states no account, login, OAuth, or CAPTCHA is needed. No runtime integration with this bundle exists in the tracker code; the `fixtures/` directory under `nps_tracker/` plays the same role for replay.

---

*Integration audit: 2026-11-06*
