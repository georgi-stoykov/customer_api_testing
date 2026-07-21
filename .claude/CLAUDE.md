# CLAUDE.md

Coding standards and design rules for the currency conversion API automation project.
These are **binding rules** — follow them exactly. Rationale lives in `.docs/`; step-by-step
design lives in `.plans/PLAN.md`. This file is the rulebook; append new decisions here as they
are made. **Record only what is — no dates, no "we considered/rejected X".**

> ⚠️ **`.docs/API_BEHAVIOR.md` is NOT trusted evidence.** It was generated in a past session.
> Treat every claim in it as an unverified hypothesis: re-probe the live simulator before
> relying on it for design, asserters, or rulings. (Already-disproved example: it claimed the
> `amountIn` echo rounds HALF_UP; live tie probes show ROUND_HALF_EVEN.)

## Project

API test framework for a customer API simulator (customer, wallets, quotes/conversions).
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
3. **Composites live in `api_flows/`.** Multi-step / orchestrated operations (customer setup,
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
  `compute_max_rounding_error`, `assert_equal`, `assert_equal_with_tolerance`), imported as the module
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
- `api_models/` — pydantic v2 (`Wallet`, `CustomerWallets`, `Quote`, `QuoteCreateRequest`,
  `QuoteStatus`, `PaymentStatus`, `PayMethod`). Response models own their own selection:
  `CustomerWallets` is a `RootModel[list[Wallet]]` (the `/api/wallet` response) exposing
  `CustomerWallets.by_currency(code) -> Wallet`, `by_id(wallet_id) -> Wallet`, iteration, and
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
- **The tenant `/init` provisions is a `customer` — never an `account`.** The API names neither
  (it exposes only wallets and quotes; `/init` returns just a token), so the term is ours and is
  standardized on `customer` everywhere the **entity** is named: models (`CustomerWallets`,
  `CustomerQuotes`), flows (`new_customer`), fixtures (`customer_api`), Allure titles/steps, and
  docs. The relationship is strictly 1:1 — one `/init` yields one tenant owning one wallet set —
  so a second noun for the balance-bearing side would be two words for one entity.
- **Asserter methods are named for what they check, not for who owns it** — hence
  `assert_wallets_unchanged` (the wallet set), not `assert_customer_unchanged`, sitting
  alongside `assert_wallet_deltas` / `assert_wallets_equal`. Likewise, prose about money
  movement says **wallet** (`source wallet`/`target wallet`): a conversion debits and credits
  specific wallets. `customer` is for the tenant, not for its balances.
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
  (`amountIn × 0.0001`) is compared **exactly and unrounded** — the API reports the fee at full
  precision and never quantizes it to the source currency's `quantityPrecision` (probed with an
  `amountIn` sitting exactly at `quantityPrecision`: the fee came back at 12 dp). Do **not**
  round the expected side: clean amounts yield an exactly-representable fee, so rounding looks
  harmless there while silently corrupting any `amountIn` finer than 4 dp;
  (3) `expected_amount_out` (`(amountIn − fee) × price`) **cannot** be compared exactly:
  the API rounds `price` (to `pricePrecision`) and `amountOut` (to the target's
  `quantityPrecision`) independently from an internal full-precision rate it never exposes
  (`netPrice`/`grossPrice` are equally rounded). It is compared within
  `(amountIn − fee) × compute_max_rounding_error(pricePrecision)
  + compute_max_rounding_error(quantityPrecision)`
  — never a hard-coded rate or an arbitrary float epsilon.
- **Request boilerplate lives on the model, not the resource.** Use pydantic defaults + aliases
  (`populate_by_name=True`, `from_` aliased to `"from"`, money as `str`,
  `model_dump(by_alias=True)`).
- **Request models are wire-typed.** Currency fields are `str`, not the `Currency` enum, so
  negative tests can push invalid codes through the same model; happy-path type safety lives
  on the flow signatures (`create_quote` takes `Currency | str`, and its wallet-id override
  exists for ids the customer cannot resolve).
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
  - Asserters live in `api_asserters/`, split per domain concept: `QuoteAsserter`
    (quote-level atomics — statuses, echoes-request, settled consistency, fee/amountOut math,
    amountIn rounding — plus the `assert_settled_quote` composite: settled statuses +
    settled-quote consistency + fee/amountOut math), `ConversionAsserter` (wallet atomics +
    customer-impact composites, e.g. `assert_settled_conversion`; its only quote knowledge is
    the settled-status guard, delegated to an internal `QuoteAsserter`), `ErrorAsserter`
    (status + error detail). All injected via fixtures. Extract new ones from repeating
    patterns rather than building upfront.
  - **Composite asserters are soft.** A composite wraps each atomic call in a
    `checks.SoftAssertions` `with` block and ends with `soft.assert_all()`, so one run reports
    every failing check as one combined numbered failure. Atomic methods stay fail-fast plain
    asserts (soft only at the composition level); only `AssertionError` is collected —
    structural errors (e.g. `by_id` on a vanished wallet) abort immediately. Allure still marks
    each failing `@allure.step` red: the step records the failure before the block suppresses
    it.
  - **All monetary calculation/comparison goes through the `monetary` module**
    (`engine/utils/monetary.py`: stateless functions `round_half_up`,
    `compute_max_rounding_error`, `assert_equal`, `assert_equal_with_tolerance`, imported as the
    module and called
    as `monetary.assert_equal(...)`). Asserters never compare or quantize `Decimal`s inline — one
    module guarantees every field follows the same comparison principle and failure-message format.
- `tests/conftest.py` provides a `customer_api` fixture (a fresh `ApiClient` per test, built via
  `flows.new_customer()`). The fixture is named for what it hands the test — an API client bound
  to its own freshly provisioned customer — not for the flow that builds it.
- **Tests run in parallel by default** (`pytest-xdist`, `-n auto` in `addopts`) — every test
  must be parallel-safe: provision its own customer via the `customer_api` fixture, never
  share customer state across tests. Debug serially with `pytest -n 0`.
- **Test levels are folders, not markers.** Three levels, split by whether a test drives
  the quote state machine over time — which is also what makes it slow:
  - `tests/smoke/` — liveness (`/health` + `/echo`).
  - `tests/integration/` — single request → assert response. Validation, error contracts,
    and read-parity; never accepts a quote, so nothing waits.
  - `tests/e2e/` — full quote lifecycles: create → accept → poll → assert balances,
    plus the timing tests that wait on the acceptance window.

  A file's location IS its level, selected by path (`pytest tests/integration`). No level
  markers — `--strict-markers` is on so any custom mark fails loudly as a typo. **Test
  filenames must be unique across levels**: there is no `__init__.py` under `tests/`, so
  two same-named files collide with an import-file-mismatch error.
  Fixtures used by more than one level (`customer_api`, the asserters) live in the root
  `tests/conftest.py`; level-specific fixtures (`pending_quote`) in the level's own
  conftest. Smoke checks are contract + trivial presence/equality only (via
  `checks.assert_equal`) — no asserter class.
- **Settlement is asynchronous.** Accept returns 200 immediately with balances unchanged; funds
  settle ~5–8s later. E2E tests must POLL `GET /quote/{uuid}` until `paymentStatus=SUCCESS`
  (timeout ~30s) BEFORE asserting balances.
- **Waits must poll, never sleep in one block.** The simulator silently drops keep-alive
  sockets idle ~10s+, and the next request on the stale socket dies with a transport error;
  requests spaced at the poll interval keep the socket warm. `flows._poll_quote` backs every
  wait (settlement, expiry, `hold_quote`) and returns the last fetched quote whether or not
  the condition was met — callers decide how to fail.
- **Read parity after a state change is asserted in the e2e happy path:** after settlement,
  the canonical conversion test fetches the source and target wallets via the single-wallet
  endpoint and compares them to their list entries — the integration parity suite covers only
  never-converted customers.
- **Fee math:** `fee = amountIn × 0.0001` (0.01%, in source currency);
  `amountOut = (amountIn − fee) × price`.
- **A settled conversion asserts the customer's total impact — and only that**, via
  `ConversionAsserter.assert_settled_conversion`. A check belongs in this composite only if
  it needs BOTH the quote and the wallet snapshots; quote-contract checks live on
  `QuoteAsserter` and are not re-run per conversion test. The composite opens with the
  settled-status guard (`quoteStatus=PAYMENT_OUT_PROCESSED`, `paymentStatus=SUCCESS`) — its
  premise, and not redundant with `wait_for_settlement`, which polls `paymentStatus` only.
  - **Both `balance` AND `available`** move by exactly `amountIn` (source) / `amountOut`
    (target) — settlement must release reservations, not just move balance.
  - **Wallet set is stable:** wallet count unchanged; every wallet keeps its `id` and
    `address` and stays `ACTIVE`; uninvolved wallets keep `balance`/`available` untouched.
  - **`approxBalance`/`approxAvailable` mirror `balance`/`available` exactly** (probed:
    not rounded or lagged, even post-settlement) — asserted on every wallet in both
    snapshots.
  - `convertedAvailable`/`approxConvertedAvailable` are unmodeled and unasserted — see
    "Known simulator issues" below.
    `CustomerWallets.by_currency` raises on zero OR multiple matches (a duplicate-currency
    wallet must fail loudly, never a silent first-match).
- **Quote-contract checks are asserted once, not per conversion:**
  - **Quote echoes the request** (`from`/`to`/`amountIn` plus the requested wallet ids,
    `usePayInMethod.id`/`usePayOutMethod.id` == `fromWallet`/`toWallet`) is a creation-time
    contract — asserted at create in the parity suite
    (`test_parity.py::test_quote_echoes_create_request`), not at settlement.
  - **`QuoteAsserter.assert_settled_quote`** (settled statuses + settled-quote consistency +
    fee math via `assert_fee` + amountOut math via `assert_amount_out`) is asserted by the
    canonical happy path (`test_conversion.py`) alongside
    `assert_settled_conversion`. Lifecycle/timing tests call the conversion composite only;
    a test adds `assert_settled_quote` explicitly when quote integrity IS its concern.
  - **Settled-quote consistency (exact):** `amountInGross == amountInNet == amountIn`
    (`amountInNet` does NOT subtract the service fee), `amountDue == 0` (it is the
    *outstanding* amount — equals `amountIn` until settlement), `fees.value.service == fee`,
    `processingFee == 0`, `netPrice == grossPrice == price`.
- **`price` is a pair-level rate; the asserter bounds the `amountOut` tolerance with the
  *coarser* of the two currencies' `pricePrecision`** (`min(source, target)`) — which side the
  API actually rounds to is unverifiable while all currencies use 8 dp, and the coarser side
  yields the larger rounding error, so the bound holds either way (noted in
  `.docs/API_BEHAVIOR.md`).

## Known simulator issues (unconfirmed — to be raised with the API owner)

The single home for every questionable API behaviour the suite has surfaced. All were
observed against the live simulator; evidence and raw captures live in
`.docs/API_BEHAVIOR.md`. None is confirmed as intended or as a bug by the API owner yet.

**Policy: tests for these behaviours assert the CORRECT contract and are marked
`@pytest.mark.skip`** with a reason string from `engine/api_constants/general_messages.py` —
the shared `PENDING_OWNER_RULING` by default; a dedicated string where the question warrants
its own label in the report (item 7's `UNCONFIRMED_HALF_EVEN_ROUNDING`). The assertion stays written for the
correct contract: the skip parks the question with the API owner without deleting the bug
report or leaving the pipeline permanently red. Remove the marker once the owner rules —
if the behaviour is intended, rewrite the assertion instead.

1. **Negative `amountIn` settles in reverse.** `amountIn = -1` is accepted (`201`) with
   negative `fee`/`amountOut`, accepts, and settles: the source wallet is *credited* and
   the target debited — a conversion run backwards at the forward rate that also *earns*
   the fee. No validation anywhere in the lifecycle.
   Skipped test: `tests/integration/test_amount_validation.py::test_negative_amount_is_rejected`.
2. **Concurrent settlements lose updates.** Two quotes accepted back-to-back both reach
   `SUCCESS`/`amountDue: 0`, but each settlement applies its delta to a stale balance
   snapshot and the last write wins — one conversion's wallet impact vanishes (and any
   combined overdraw is silently masked). Sequential conversions accumulate correctly.
   Skipped test: `tests/e2e/test_quote_lifecycle.py::test_concurrent_conversions_apply_combined_impact`
   (failure depends on the settlement race; every observed run has lost the update). The loss
   is **permanent, not a read-too-early artifact**: re-reading balances for 18s after both
   quotes report `SUCCESS`/`amountDue: 0` shows the delta pinned at exactly one quote's
   impact.
3. **The `amountIn` echo is rounded while the trade is priced off the unrounded request.**
   An `amountIn` finer than the source `quantityPrecision` is echoed rounded (HALF_UP), but
   **both** `fee` and `amountOut` are computed from the *unrounded* request. Probed with
   `amountIn "0.123456789012"`: the echo reads `"0.12345679"`, `fee` reads
   `"0.0000123456789012"` (= unrounded × 0.0001), and `amountOut` matches
   `(unrounded − fee) × price` within tolerance while the echo-derived value is off by ~25×
   the tolerance. The quote is internally consistent everywhere *except* `amountIn`, which
   under-reports what the customer is charged — one root cause, two visible symptoms.
   Skipped test: `tests/integration/test_amount_validation.py::test_excess_precision_fee_matches_reported_amount_in`.
   ⚠️ `test_excess_precision_amount_is_rounded` currently **passes by asserting the rounded
   echo is the contract** — it enshrines this behaviour and must be revisited once the owner
   rules on which side is correct.
4. **`convertedAvailable`/`approxConvertedAvailable` are a static `"10000"`** on every
   wallet in every capture, never reflecting balance changes. Possibly an intentional
   stub — unmodeled and unasserted until the owner confirms; no test.
5. **`useMaximum` is a no-op.** Ignored when `amountIn` is present; without `amountIn` the
   request is rejected with the amount-not-specified 400 — there is no working
   "convert everything" mode. Untestable until the intended semantics are known; no test.
6. **Zero `amountIn` yields a misleading rejection.** Zero is treated as "amount not
   specified" (falsy), so the 400 detail is the amountIn/amountOut message rather than a
   must-be-positive validation. Cosmetic; `test_zero_amount_is_rejected` asserts the
   observed contract and stays green.
7. **Exact-half ties round HALF_EVEN (banker's), not HALF_UP.** The `amountIn` echo
   resolves a bare-5 tie to the even neighbour: `0.123456785 → 0.12345678` (even digit
   stays), `0.123456775 → 0.12345678` and `0.123456795 → 0.12345680` (odd digit bumps to
   even; these two also rule out HALF_DOWN). The `…795` probe further rules out a float64
   artifact: its double sits *below* the tie, so any float-based rounding would echo `…79`,
   yet the API returned `…80` — consistent with decimal-string parsing under Python
   `Decimal`'s default context. Only exact ties are affected; any other dropped digit
   rounds identically under both modes, which is why earlier probes (first dropped digit 9)
   could not detect this. The tie test asserts HALF_UP until the owner rules which mode is
   the intended contract.
   Skipped test:
   `tests/integration/test_amount_validation.py::test_excess_precision_amount_is_rounded[tie-rounds-up]`
   (reason `UNCONFIRMED_HALF_EVEN_ROUNDING`).

Expected outcome while all of the above stand: **zero failures and exactly 4 skips** —
items 1, 3, and 7 in `tests/integration`, item 2 in `tests/e2e`.

## CI

- **Gated pipeline in `.github/workflows/ci.yml`:** `code analysis` → `smoke` →
  (`integration` ∥ `e2e`) → `report`, chained with `needs:`. **`integration` and `e2e` both
  depend on `smoke` only, so they run concurrently** — neither consumes the other's output,
  and every test provisions its own customer via `/init`, so the suites cannot collide on
  shared state. Serialising them would put a second checkout + `pip install` (~40s) on the
  critical path, which exceeds the integration level's whole runtime; the fail-fast this
  would buy is already covered by `code analysis` and `smoke`. Triggers: push to main, PRs (and pushes to them), a daily
  heartbeat schedule at **10:00 Europe/Sofia**, and manual dispatch. Cron is UTC and DST-blind,
  so the offset is encoded in the **month field** of two disjoint crons — `0 7 * 4-10 *`
  (UTC+3, summer) and `0 8 * 1-3,11,12 *` (UTC+2, winter). Exactly one fires per day, so this
  costs no gate job and produces no all-skipped runs. The days between each DST switch (last
  Sunday of March / October) and the month boundary fire an hour off — 11:00 in late March,
  09:00 in late October, ~10 days a year — which is accepted rather than corrected: a heartbeat
  has no consumer of the exact hour, and GitHub expressions have no date/timezone functions, so
  pinning it exactly would require a shell, hence a whole gate job on every run. Scheduled runs
  deploy the root report exactly like main pushes.
  `code analysis` = Ruff (`check` + `format --check`) plus the build gate
  (`pytest --collect-only` with a placeholder `API_BASE_URL` — there is no build backend, so
  install + collect IS the build). `smoke` = liveness gate (`pytest tests/smoke`);
  `integration` = `pytest tests/integration`; `e2e` = `pytest tests/e2e`. No CodeQL — evaluated and removed as too heavy for this repo's needs.
- **Report publishing:** the `report` job runs even when tests fail, builds the Allure report
  with run history (`simple-elf/allure-report-action`), and deploys to GitHub Pages
  (`gh-pages` branch): main pushes go to the site root (with trend history), PR runs go to
  `pr-<PR>/` on the same site (standalone preview, no effect on root history; fork PRs
  excluded — no token push rights). Every run also uploads the `allure-report` artifact.
  The run summary links the applicable report URL. PR preview dirs are cleaned up by the
  **manually triggered** `cleanup-pr-reports.yml` workflow (never automatic; scope input:
  `closed-prs` default, or `all`). The `gh-pages` branch was
  bootstrapped once as an empty orphan commit — the report job requires it to exist (its
  checkout fails loudly rather than half-initializing the publish dir).
- **Pages source is "deploy from a branch"** (`gh-pages`), so every push to that branch makes
  GitHub spawn its own `pages build and deployment` run. That run is GitHub infrastructure, not
  a second pipeline of ours, and cannot be folded into `ci` while the branch source is in use.
  The branch source is what lets `ci` mutate the site incrementally — Allure trend history, and
  PR previews that are written into `pr-<PR>/` without ever republishing the root.
- **The published report is world-readable — the API host must never appear in it.**
  `--allure-no-capture` is mandatory in CI pytest invocations; `BaseClient` logs
  `method + path` only and converts `requests` transport exceptions to `ApiError` with
  `from None` so the full URL never reaches a traceback.
- **Allure decorators (`@allure.step` / `@allure.title`) are allowed on `api_flows/`,
  `api_asserters/`, and tests only** — never on `base_client.py`, `api_resources/`, or
  `api_models/` (transport and contract layers stay report-agnostic).
