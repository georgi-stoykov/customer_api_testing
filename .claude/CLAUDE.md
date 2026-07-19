# CLAUDE.md

Coding standards and design rules for the currency conversion API automation project.
These are **binding rules** — follow them exactly. Rationale lives in `.docs/`; step-by-step
design lives in `.plans/PLAN.md`. This file is the rulebook; append new decisions here as they
are made. **Record only what is — no dates, no "we considered/rejected X".**

## Project

API test framework for a customer API simulator (account, wallets, quotes/conversions).
Stack: **Python + pytest + requests**, pydantic v2 models, Allure report (`allure-pytest`),
published to GitHub Pages by CI.
The target host is configured via the `API_BASE_URL` env var and kept out of version control
(local `.env`, gitignored). Swagger at `/docs`, OpenAPI spec at `/openapi.json`.

## Collaboration & process

- **The maintainer is the architect; Claude is the main implementer.** The maintainer steers
  every design decision and reviews all output.
- **Discuss design before writing code.** Confirm the approach for each component and get
  approval before implementing. Never ship a large unilateral change.
- **Implement vertically.** Build the thinnest happy-path slice across all layers first, then
  stop for a file-by-file review before extending. No unplanned scope without explicit approval.
- **Never run `git commit` / `merge` / branch creation / `push`, or open PRs, without explicit
  approval.** Enforced by `.claude/settings.json` permission rules, not just this note.
- **Explain rationale as you go.** Every decision must be clearly reasoned and defensible.
- When a design or standards decision is settled, **record it here** as a concise rule.

## Architecture — layering (strict separation of concerns)

The framework is split into an **engine** (drivers) and thin **tests**. Three governing
principles for the client layer:

1. **Resources hold only endpoints.** Each API resource method maps to one endpoint and returns
   parsed data (models). No filtering, selection, composition, or orchestration on resources.
2. **No duplicate classes.** The class that models a response IS the class used to work with that
   data. Filtering/selection lives on the response model, not a second class.
3. **Composites live in `api_flows/`.** Multi-step / orchestrated operations (account setup,
   settlement polling, full conversion) live in a separate `api_flows/` layer — never on resources.

### Package: `engine`

`engine` is the framework's **driver layer**, importable as `engine` (folder name = import
name). The repo is a test suite, not a distributable package: there is no build backend and
nothing is `pip install`ed. It sits flat at the repo root alongside `tests/` (no `src/` layout);
pytest's `pythonpath` (in `pyproject.toml`) puts the repo root on `sys.path` so tests import the
engine directly.

The `engine/` tree is **flat**: every package/module is a direct child of `engine/`, with no
per-API parent folder. The **shared, API-agnostic** pieces sit unprefixed — `base_client.py` (the
transport core), `constants/` (transport/config values), and `utils/` (API-agnostic utility
modules). **Everything specific to the customer API carries the `api_` prefix** — `api_client.py`
(facade), `api_constants/` (domain values), `api_models/`, `api_resources/`, `api_asserters/`,
`api_flows/`. The prefix marks API-specific code and keeps it visually distinct from the shared
root pieces.

- `base_client.py` (root, shared) — `BaseClient` (one `Session`, auth, logging, `.send()`);
  `ApiError`; `ApiResponse` (internal transport: `status_code`, `json`, `as_model(model)`,
  `raise_for_status(expected)`); the `@endpoint` decorator. Shared across APIs.
- `constants/` (root, shared) — transport/config values, no magic literals (see
  `CODING_STYLE.md`): `settings.py` (env-sourced base URL + request timeout, plus the `env_float`
  helper), `http.py` (`Header`, `MediaType`, `AuthScheme`). HTTP methods/statuses come from stdlib
  `http.HTTPMethod` / `http.HTTPStatus`.
- `utils/` (root, shared) — API-agnostic utility modules, one named module per concern.
  `monetary.py`: stateless money math + comparison primitives (`round_half_up`,
  `rounding_tolerance`, `assert_equal`, `assert_equal_with_tolerance`), imported as the module
  (`from engine.utils import monetary`). `checks.py`: the generic equality assertion
  (`assert_equal(actual, expected, context)`) — single source of the
  `context: expected X, got Y` failure-message format; `monetary.assert_equal` delegates to
  it, and asserters use `checks.assert_equal` for all non-monetary field comparisons (no
  hand-rolled `assert x == y, f"..."` messages). `checks.py` also holds `SoftAssertions`,
  the soft-assertion collector used by composite asserters.
- `api_constants/` — the customer API's domain values (no magic literals): `currencies.py`
  (`Currency` StrEnum), `fees.py` (`CONVERSION_FEE_RATE`), `settlement.py` (settlement timeout +
  poll interval, via `settings.env_float`).
- `api_client.py` — `ApiClient` facade composing resources over ONE `BaseClient` (dependency
  injection → auth defined in one place).
- `api_models/` — pydantic v2 (`Wallet`, `AccountWallets`, `Quote`, `QuoteCreateRequest`,
  `QuoteStatus`, `PaymentStatus`, `PayMethod`). Response models own their own selection:
  `AccountWallets` is a `RootModel[list[Wallet]]` (the `/api/wallet` response) exposing
  `AccountWallets.by_currency(code) -> Wallet`, `by_id(wallet_id) -> Wallet`, iteration, and
  `len()` — set traversal/pairing lives on the model, so asserters sweep the wallets the API
  actually returned (paired before/after by `id`), never a hand-maintained currency list.
  `Wallet.label` (e.g. `wallet (ETH)`) is the single source of the wallet failure-message
  prefix used by asserters.
- `api_resources/` — pure endpoint clients: `CustomerApi`, `WalletApi`, `QuoteApi`,
  `SystemApi` (`/health`, `/echo` — service/system endpoints live on their own resource, never
  on `CustomerApi`; models in `api_models/system.py`). Endpoint paths are inline string
  literals in the endpoint methods (f-strings for parametrized paths): each path is used
  exactly once, and the one-method-per-endpoint rule already makes the method the single home
  of its path — a module-level constant would just duplicate the name. This is the sanctioned
  exception to the no-magic-literals rule.
- `api_flows/` — composites: `new_customer()`, `wait_for_settlement()`, `send_quote()`.
  Multi-step orchestration is **not** a step/endpoint — the `flows` name guards the boundary
  against single-endpoint wrappers (those belong on resources).

### Naming

- Facade = `ApiClient`; resources = `WalletApi` / `QuoteApi` / `CustomerApi` (OpenAPI codegen
  convention). Do **not** use `Controller` (a server-side term).
- **Shared utilities live in `engine/utils/`, one named module per concern** (`monetary.py`), not
  in a catch-all `helpers/`. A module earns a place there only if it is API-agnostic (no API
  contract, no domain state) and reused — or clearly reusable — beyond a single caller. If a thing
  fits an existing layer, it goes there; `utils/` is named layers, not a dumping ground.

## Coding standards

- **Code style is enforced by Ruff and documented in `CODING_STYLE.md`** (import grouping,
  exploded signatures, no magic string literals → `constants/`/`api_constants/` + enums, minimal
  comments). Read
  it before writing code.
- **All money is `Decimal`.** Money fields arrive as strings — parse to `Decimal`, never
  `float`. Three comparison rules: (1) the API's own reported numbers, and wallet deltas vs. the
  reported `amountIn`/`amountOut`, are compared **exactly**; (2) `expected_fee`
  (`amountIn × 0.0001`) is compared exactly after rounding the expected side to the **source**
  currency's `quantityPrecision` (ROUND_HALF_UP, matching the API; only the expected side is
  rounded — `Decimal` equality is numeric, and rounding the API's side would mask a mis-rounded
  value); (3) `expected_amount_out` (`(amountIn − fee) × price`) **cannot** be compared exactly:
  the API rounds `price` (to `pricePrecision`) and `amountOut` (to the target's
  `quantityPrecision`) independently from an internal full-precision rate it never exposes
  (`netPrice`/`grossPrice` are equally rounded). It is compared within
  `(amountIn − fee) × rounding_tolerance(pricePrecision) + rounding_tolerance(quantityPrecision)`
  — never a hard-coded rate or an arbitrary float epsilon.
- **Request boilerplate lives on the model, not the resource.** Use pydantic defaults + aliases
  (`populate_by_name=True`, `from_` aliased to `"from"`, money as `str`,
  `model_dump(by_alias=True)`).
- **Model only the fields tests assert on.** Response models declare the asserted +
  contract-critical fields and rely on `extra="ignore"` (set on the `ApiModel` base) to drop the
  simulator's many unmodeled fields silently rather than hand-modeling noise (e.g. `Wallet.currency`
  exposes `code`, not its ~12 other fields). Model files are split **per resource**
  (`api_models/customer.py`, `api_models/wallets.py`, `api_models/quotes.py`,
  `api_models/common.py`).
- **Contract enforcement via `@endpoint(model=..., expected_status=...)`.** Every endpoint method
  is wrapped by the decorator, which enforces BOTH the status code AND the data contract
  (pydantic) by default. The endpoint body just returns `send()`'s `ApiResponse`.
  - One per-call backdoor: **`check=False`** skips both checks (for negative tests), returning the
    raw `ApiResponse` to assert against.
  - Single `check` flag only — no split status/schema flags, no `no_checks()` context manager
    (avoids hidden global state).
  - Strict path raises `ApiError`; return type is `Model | ApiResponse`.
  - `expected_status` is declared per endpoint as a stdlib `http.HTTPStatus` (e.g.
    `HTTPStatus.CREATED` for quote create, `HTTPStatus.OK` for accept and the rest).

## Testing

- **Tests stay thin.** All drivers/validation live in the engine. No API-construction or parsing
  logic in test bodies.
- **No bare inline assertions for domain rules.** Business-math assertions belong in named,
  reusable asserter classes (per domain concept, e.g. wallet/conversion) so a contract change is a
  one-class edit. Schema validation is handled by pydantic; asserters cover business math.
  - Asserters live in `api_asserters/` (`ConversionAsserter`: atomic assertion methods
    composed into bigger ones, e.g. `assert_settled_conversion`), injected via fixtures. Extract
    new ones from repeating patterns rather than building upfront.
  - **Composite asserters are soft.** A composite wraps each atomic call in a
    `checks.SoftAssertions` `with` block and ends with `soft.assert_all()`, so one run reports
    every failing check as one combined numbered failure. Atomic methods stay fail-fast plain
    asserts (soft only at the composition level); only `AssertionError` is collected —
    structural errors (e.g. `by_id` on a vanished wallet) abort immediately. Allure still marks
    each failing `@allure.step` red: the step records the failure before the block suppresses
    it.
  - **All monetary calculation/comparison goes through the `monetary` module**
    (`engine/utils/monetary.py`: stateless functions `round_half_up`,
    `rounding_tolerance`, `assert_equal`, `assert_equal_with_tolerance`, imported as the module and called
    as `monetary.assert_equal(...)`). Asserters never compare or quantize `Decimal`s inline — one
    module guarantees every field follows the same comparison principle and failure-message format.
- `tests/conftest.py` provides a `new_customer` fixture (a fresh `ApiClient` per test, built via
  `flows.new_customer()`; the fixture shares the flow's name, so conftest imports the `api_flows`
  module aliased as `flows` rather than the function).
- **Tests run in parallel by default** (`pytest-xdist`, `-n auto` in `addopts`) — every test
  must be parallel-safe: provision its own customer via the `new_customer` fixture, never
  share account state across tests. Debug serially with `pytest -n 0`.
- **Test levels are folders, not markers.** `tests/smoke/` (liveness: `/health` + `/echo`)
  and `tests/e2e/` (full conversions); a file's location IS its level, selected by path
  (`pytest tests/smoke`). No level markers — `--strict-markers` is on so any custom mark
  fails loudly as a typo. Shared fixtures (`new_customer`) live in the root
  `tests/conftest.py`; level-specific fixtures (`conversion_asserter`) in the level's own
  conftest. Smoke checks are contract + trivial presence/equality only (via
  `checks.assert_equal`) — no asserter class.
- **Settlement is asynchronous.** Accept returns 200 immediately with balances unchanged; funds
  settle ~5–8s later. E2E tests must POLL `GET /quote/{uuid}` until `paymentStatus=SUCCESS`
  (timeout ~30s) BEFORE asserting balances.
- **Fee math:** `fee = amountIn × 0.0001` (0.01%, in source currency);
  `amountOut = (amountIn − fee) × price`.
- **A settled conversion asserts the account's total impact**, via
  `ConversionAsserter.assert_settled_conversion`:
  - **Both `balance` AND `available`** move by exactly `amountIn` (source) / `amountOut`
    (target) — settlement must release reservations, not just move balance.
  - **Wallet set is stable:** wallet count unchanged; every wallet keeps its `id` and
    `address` and stays `ACTIVE`; uninvolved wallets keep `balance`/`available` untouched.
  - **`approxBalance`/`approxAvailable` mirror `balance`/`available` exactly** (probed:
    not rounded or lagged, even post-settlement) — asserted on every wallet in both
    snapshots.
  - **Potential issue (unconfirmed):** `convertedAvailable`/`approxConvertedAvailable` are
    a static `"10000"` on every wallet in every observed capture, never reflecting balance
    changes — suspected simulator misbehaviour, to be confirmed with the API owner.
    Unmodeled and unasserted until confirmed (details in `.docs/API_BEHAVIOR.md`).
    `AccountWallets.by_currency` raises on zero OR multiple matches (a duplicate-currency
    wallet must fail loudly, never a silent first-match).
  - **Quote echoes the request:** `from`/`to`/`amountIn` plus the requested wallet ids
    (`usePayInMethod.id`/`usePayOutMethod.id` == `fromWallet`/`toWallet`).
  - **Settled-quote consistency (exact):** `amountInGross == amountInNet == amountIn`
    (`amountInNet` does NOT subtract the service fee), `amountDue == 0` (it is the
    *outstanding* amount — equals `amountIn` until settlement), `fees.value.service == fee`,
    `processingFee == 0`, `netPrice == grossPrice == price`.
- **`price` is a pair-level rate; the asserter assumes the *target* currency's
  `pricePrecision`** for the `amountOut` bound — unverifiable while all currencies use 8 dp
  (noted in `.docs/API_BEHAVIOR.md`).

## CI

- **Gated pipeline in `.github/workflows/ci.yml`:** `lint` → `smoke` → `e2e` → `report`,
  chained with `needs:`. `lint` = Ruff (`check` + `format --check`) plus the build gate
  (`pytest --collect-only` with a placeholder `API_BASE_URL` — there is no build backend, so
  install + collect IS the build). `smoke` = liveness gate (`pytest tests/smoke`); `e2e` =
  `pytest tests/e2e`. No CodeQL — evaluated and removed as too heavy for this repo's needs.
- **Report publishing:** the `report` job runs even when tests fail, builds the Allure report
  with run history (`simple-elf/allure-report-action`), and deploys to GitHub Pages
  (`gh-pages` branch): main pushes go to the site root (with trend history), PR runs go to
  `pr-<PR>/` on the same site (standalone preview, no effect on root history; fork PRs
  excluded — no token push rights). Every run also uploads the `allure-report` artifact.
  The run summary links the applicable report URL. The `gh-pages` branch was
  bootstrapped once as an empty orphan commit — the report job requires it to exist (its
  checkout fails loudly rather than half-initializing the publish dir).
- **The published report is world-readable — the API host must never appear in it.**
  `--allure-no-capture` is mandatory in CI pytest invocations; `BaseClient` logs
  `method + path` only and converts `requests` transport exceptions to `ApiError` with
  `from None` so the full URL never reaches a traceback.
- **Allure decorators (`@allure.step` / `@allure.title`) are allowed on `api_flows/`,
  `api_asserters/`, and tests only** — never on `base_client.py`, `api_resources/`, or
  `api_models/` (transport and contract layers stay report-agnostic).
