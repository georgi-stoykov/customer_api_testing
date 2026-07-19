# customer_api_testing

API test automation suite for a customer/wallet conversion service (quotes, currency conversion, settlement). Built with `requests`, `pydantic`, and `pytest`.

## Stack

- **Python 3.13**
- `requests` — HTTP client
- `pydantic` — request/response models
- `pytest` + `pytest-xdist` — test runner, parallel by default
- `allure-pytest` — reporting
- `ruff` + `pre-commit` — linting/formatting

## Project structure

```
engine/
  api_client.py        # low-level HTTP client
  api_resources/        # endpoint wrappers (customer, quotes, system, wallets)
  api_models/            # pydantic request/response models
  api_flows/             # higher-level flows (e.g. conversion, customer setup)
  api_asserters/         # reusable assertion helpers
  api_constants/         # currencies, fees, settlement, error messages
  constants/             # HTTP constants and settings
  utils/                 # checks, monetary helpers
tests/
  smoke/                 # basic liveness checks
  integration/           # validation, error handling, parity checks
  e2e/                   # full quote/conversion lifecycle flows
```

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # set API_BASE_URL and any overrides
pre-commit install       # optional, runs ruff on commit
```

## Running tests

```bash
pytest                        # full suite, parallel (-n auto by default)
pytest tests/smoke             # smoke tests only
pytest tests/integration        # integration tests only
pytest tests/e2e                # end-to-end tests only
pytest -n 0                      # run serially for debugging
pytest --alluredir=allure-results  # generate Allure results
```

## Code style

Enforced via Ruff (absolute imports, full type annotations, no magic strings/floats for money, etc.). See [CODING_STYLE.md](./CODING_STYLE.md) for the full ruleset.

## CI/CD pipeline

`.github/workflows/ci.yml` runs on push to `main`, on PRs, on schedule, and manually:

1. **code_analysis** — ruff lint + format check, `pytest --collect-only`
2. **smoke** — runs `tests/smoke`
3. **integration** / **e2e** — run in parallel after smoke passes
4. **report** — merges Allure results and publishes to GitHub Pages (`gh-pages`)

A separate manual workflow (`cleanup-pr-reports.yml`) deletes stale PR report previews from `gh-pages`.
