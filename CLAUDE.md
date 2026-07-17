# CLAUDE.md

Coding standards and design rules for the BVNK Currency Conversion API automation project.
These are **binding rules** — follow them exactly. Rationale lives in `.docs/`; step-by-step
design lives in `.plans/PLAN.md`. This file is the rulebook; append new decisions here as they
are made.

## Project

API test framework for BVNK's customer API simulator (account, wallets, quotes/conversions).
Stack: **Python + pytest + requests**, pydantic v2 models, pytest-html report.
Live host: `https://bvnkapisimulator.pythonanywhere.com` (Swagger at `/docs`, spec at
`/openapi.json`).

## Collaboration & process

- **Georgi is the architect; Claude is the main implementer.** Georgi steers every design
  decision and reviews all output.
- **Discuss design before writing code.** Confirm the approach for each component and get
  Georgi's approval before implementing. Never surprise him with a large unilateral change.
- **Explain rationale as you go.** Every decision must be interview-defensible — the value is
  design ownership, not typing.
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

### Package: `bvnk_customer_api`

- `base.py` — `BaseClient` (one `Session`, auth, logging, `.send()`); `ApiError`;
  `ApiResponse` (internal transport only); the `@endpoint` decorator.
- `client.py` — `ApiClient` facade composing resources over ONE `BaseClient` (dependency
  injection → auth defined in one place).
- `config.py` — base URL, timeouts (env-overridable).
- `models/` — pydantic v2 (`Wallet`, `AccountWallets`, `Quote`, `QuoteCreateRequest`,
  `QuoteStatus`). Response models own their own selection (e.g.
  `AccountWallets.by_currency(code) -> Wallet`).
- `resources/` — pure endpoint clients: `AccountApi`, `WalletApi`, `QuoteApi`.
- `flows/` — composites: `new_account()`, `wait_for_settlement()`, `convert()`.

### Naming

- Facade = `ApiClient`; resources = `WalletApi` / `QuoteApi` / `AccountApi` (OpenAPI codegen
  convention). Do **not** use `Controller` (a server-side term).
- **No `helpers/` folder.** If something doesn't fit a layer, name the layer, don't dump it in
  helpers.

## Coding standards

- **All money is `Decimal`.** API money fields arrive as strings — parse to `Decimal`, never
  `float`. Assert internal consistency against the quote's own rate (rates fluctuate).
- **Request boilerplate lives on the model, not the resource.** Use pydantic defaults + aliases
  (`populate_by_name=True`, `from_` aliased to `"from"`, money as `str`,
  `model_dump(by_alias=True)`).
- **Contract enforcement via `@endpoint(model=..., expected_status=...)`.** Every endpoint method
  is wrapped by the decorator, which enforces BOTH the status code AND the data contract
  (pydantic) by default. The endpoint body just returns `send()`'s `ApiResponse`.
  - One per-call backdoor: **`check=False`** skips both checks (for negative tests), returning the
    raw `ApiResponse` to assert against.
  - Single `check` flag only — no split status/schema flags, no `no_checks()` context manager
    (hidden global state — rejected).
  - Strict path raises `ApiError`; return type is `Model | ApiResponse`.

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
