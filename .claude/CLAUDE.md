# CLAUDE.md

Coding standards and design rules for the currency conversion API automation project.
These are **binding rules** — follow them exactly. Rationale lives in `.docs/`; step-by-step
design lives in `.plans/PLAN.md`. This file is the rulebook; append new decisions here as they
are made. **Record only what is — no dates, no "we considered/rejected X".**

## Project

API test framework for a customer API simulator (account, wallets, quotes/conversions).
Stack: **Python + pytest + requests**, pydantic v2 models, pytest-html report.
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
3. **Composites live in `flows/`.** Multi-step / orchestrated operations (account setup,
   settlement polling, full conversion) live in a separate `flows/` layer — never on resources.

### Package: `engine`

`engine` is the framework's **driver layer**, importable as `engine` (folder name = import
name). The repo is a test suite, not a distributable package: there is no build backend and
nothing is `pip install`ed. It sits flat at the repo root alongside `tests/` (no `src/` layout);
pytest's `pythonpath` (in `pyproject.toml`) puts the repo root on `sys.path` so tests import the
engine directly.

Only the **shared, API-agnostic** pieces sit at the `engine/` root — `base_client.py` (the
transport core) and `constants/` (config + domain values). **Everything specific to one customer
API lives under that API's folder** (`wallet_payments_api/`): its models, resources, facade
(`wallet_payments_api/client.py`), and composites (`wallet_payments_api/flows/`). A future second
API becomes a sibling folder next to `wallet_payments_api/`, self-contained and reusing
`base_client.py`/`constants/` — so nothing API-specific is ever stranded at the root where a
second API's facade/flows would collide with it.

- `base_client.py` (root, shared) — `BaseClient` (one `Session`, auth, logging, `.send()`);
  `ApiError`; `ApiResponse` (internal transport: `status_code`, `json`, `as_model(model)`,
  `raise_for_status(expected)`); the `@endpoint` decorator. Shared across APIs.
- `constants/` (root, shared) — the single home for config/domain values (no magic literals; see
  `CODING_STYLE.md`): `settings.py` (env-sourced base URL + timeouts), `currencies.py`
  (`Currency` StrEnum), `http.py` (`Header`, `MediaType`, `AuthScheme`). HTTP methods/statuses
  come from stdlib `http.HTTPMethod` / `http.HTTPStatus`.
- `wallet_payments_api/client.py` — `ApiClient` facade composing resources over ONE `BaseClient`
  (dependency injection → auth defined in one place). Hand-written composition, so it lives at the
  `wallet_payments_api/` root beside the codegen-shaped `models/` + `resources/`, not inside them.
- `wallet_payments_api/models/` — pydantic v2 (`Wallet`, `AccountWallets`, `Quote`,
  `QuoteCreateRequest`, `QuoteStatus`, `PaymentStatus`, `PayMethod`). Response models own their
  own selection: `AccountWallets` is a `RootModel[list[Wallet]]` (the `/api/wallet` response)
  exposing `AccountWallets.by_currency(code) -> Wallet`.
- `wallet_payments_api/resources/` — pure endpoint clients: `AccountApi`, `WalletApi`, `QuoteApi`.
  Endpoint paths are named constants in each resource module.
- `wallet_payments_api/flows/` — composites: `new_account()`, `wait_for_settlement()`,
  `convert()`. Multi-step orchestration is **not** a step/endpoint — the name stays `flows`,
  guarding the boundary against single-endpoint wrappers (those belong on resources).

### Naming

- Facade = `ApiClient`; resources = `WalletApi` / `QuoteApi` / `AccountApi` (OpenAPI codegen
  convention). Do **not** use `Controller` (a server-side term).
- **No `helpers/` folder.** If something doesn't fit a layer, name the layer, don't dump it in
  helpers.

## Coding standards

- **Code style is enforced by Ruff and documented in `CODING_STYLE.md`** (import grouping,
  exploded signatures, no magic string literals → `constants/` + enums, minimal comments). Read
  it before writing code.
- **All money is `Decimal`.** Money fields arrive as strings — parse to `Decimal`, never
  `float`. Two comparison rules: (1) the API's own reported numbers, and wallet deltas vs. the
  reported `amountIn`/`amountOut`, are compared **exactly**; (2) values we recompute (fee,
  `amountOut`) are compared after quantizing to the target currency's `quantityPrecision`
  (ROUND_HALF_UP, matching the API), never against a hard-coded rate or an arbitrary float epsilon.
- **Request boilerplate lives on the model, not the resource.** Use pydantic defaults + aliases
  (`populate_by_name=True`, `from_` aliased to `"from"`, money as `str`,
  `model_dump(by_alias=True)`).
- **Model only the fields tests assert on.** Response models declare the asserted +
  contract-critical fields and rely on `extra="ignore"` (set on the `ApiModel` base) to drop the
  simulator's many unmodeled fields silently rather than hand-modeling noise (e.g. `Wallet.currency`
  exposes `code`, not its ~12 other fields). Model files are split **per resource**
  (`wallet_payments_api/models/account.py`, `wallet_payments_api/models/wallets.py`,
  `wallet_payments_api/models/quotes.py`, `wallet_payments_api/models/common.py`).
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
  - Asserters are currently **deferred** — extract them from repeating patterns rather than
    building upfront; keep them as classes and inject via fixtures.
- `tests/conftest.py` provides an `api` fixture built via `flows.new_account()`.
- **Settlement is asynchronous.** Accept returns 200 immediately with balances unchanged; funds
  settle ~5–8s later. E2E tests must POLL `GET /quote/{uuid}` until `paymentStatus=SUCCESS`
  (timeout ~30s) BEFORE asserting balances.
- **Fee math:** `fee = amountIn × 0.0001` (0.01%, in source currency);
  `amountOut = (amountIn − fee) × price`.
