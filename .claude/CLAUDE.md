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

### Package: `customer_api_engine`

This package is the framework's **driver layer** — one self-contained package for the whole
customer API (account + wallets + quotes share one `BaseClient` + auth). Not split
per-resource. Folder name, import name, and distribution name are all `customer_api_engine`,
kept identical everywhere (no `package-dir` remapping) for consistency. It sits flat at the
repo root alongside `tests/` (no `src/` layout).

- `base.py` — `BaseClient` (one `Session`, auth, logging, `.send()`); `ApiError`;
  `ApiResponse` (internal transport: `status_code`, `json`, `as_model(model)`,
  `raise_for_status(expected)`); the `@endpoint` decorator.
- `client.py` — `ApiClient` facade composing resources over ONE `BaseClient` (dependency
  injection → auth defined in one place).
- `config.py` — base URL (from `API_BASE_URL`) and timeouts (env-overridable).
- `models/` — pydantic v2 (`Wallet`, `AccountWallets`, `Quote`, `QuoteCreateRequest`,
  `QuoteStatus`). Response models own their own selection: `AccountWallets` is a
  `RootModel[list[Wallet]]` (the `/api/wallet` response) exposing
  `AccountWallets.by_currency(code) -> Wallet`.
- `resources/` — pure endpoint clients: `AccountApi`, `WalletApi`, `QuoteApi`.
- `flows/` — composites: `new_account()`, `wait_for_settlement()`, `convert()`.

### Naming

- Facade = `ApiClient`; resources = `WalletApi` / `QuoteApi` / `AccountApi` (OpenAPI codegen
  convention). Do **not** use `Controller` (a server-side term).
- **No `helpers/` folder.** If something doesn't fit a layer, name the layer, don't dump it in
  helpers.

## Coding standards

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
  (`models/account.py`, `models/wallets.py`, `models/quotes.py`, `models/common.py`).
- **Contract enforcement via `@endpoint(model=..., expected_status=...)`.** Every endpoint method
  is wrapped by the decorator, which enforces BOTH the status code AND the data contract
  (pydantic) by default. The endpoint body just returns `send()`'s `ApiResponse`.
  - One per-call backdoor: **`check=False`** skips both checks (for negative tests), returning the
    raw `ApiResponse` to assert against.
  - Single `check` flag only — no split status/schema flags, no `no_checks()` context manager
    (avoids hidden global state).
  - Strict path raises `ApiError`; return type is `Model | ApiResponse`.
  - `expected_status` is declared per endpoint (e.g. `201` for quote create, `200` for
    accept and the rest).

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
