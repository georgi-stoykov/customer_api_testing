# Simulator API — Observed Behaviour

Reference notes from probing the live simulator.
These document *observed* behaviour (verified against real responses), which drives the
test design, models, and asserters. Raw sanitized samples are in `docs/api-samples/`.

> **Host gotcha:** the live API is `https://[live-api-host]`
> (note the extra **`api`** in the hostname). The host printed in the task PDF,
> `[task-pdf-host]` (no `api`), is dead ("Coming Soon"). Swagger UI at
> `/docs`, OpenAPI spec at `/openapi.json`.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET  | `/init` | Create a fresh account with default balances; returns a bearer token |
| GET  | `/health` | System health metrics |
| POST | `/echo` | Auth check; echoes token expiry + request body |
| GET  | `/api/wallet` | List all wallets |
| GET  | `/api/wallet/{wallet_id}` | Get a single wallet |
| GET  | `/api/v1/quote` | List all quotes |
| POST | `/api/v1/quote` | Create a quote |
| GET  | `/api/v1/quote/{quote_uuid}` | Get a single quote |
| PUT  | `/api/v1/quote/accept/{quote_uuid}` | Accept a quote (execute the trade) |

Auth: all endpoints except `/init` require `Authorization: Bearer <token>`.
Note `accept` is **PUT**, not POST.

## Authentication

- `GET /init` returns `{ "access_token": "...", "token_type": "bearer", "expiry": <epoch> }`.
- Token is valid for 24 hours.
- Each `/init` call provisions a **new** account with default balances:
  **ETH 3.7, TRX 46500, USDT 10400**.

## Money representation

- **Every** monetary field is a JSON **string** (e.g. `"12404.164865"`), not a number.
  → Always parse with `Decimal(...)`, never `float`.
- Timestamps (`acceptanceExpiryDate`, `paymentExpiryDate`, `dateCreated`, `lastUpdated`,
  token `expiry`) are **epoch seconds (integers)**.

## Creating a quote

`POST /api/v1/quote` body (`QuoteRequest`) — required fields:

| Field | Type | Notes |
|---|---|---|
| `from` | string | source currency code, e.g. `"ETH"` |
| `to` | string | target currency code, e.g. `"TRX"` |
| `fromWallet` | int | **wallet id** of the source currency |
| `toWallet` | int | **wallet id** of the target currency |
| `useMaximum` | bool | `false` for a fixed amount |
| `useMinimum` | bool | `false` for a fixed amount |
| `reference` | string | free-text client reference |
| `payInMethod` | string | `"wallet"` |
| `payOutMethod` | string | `"wallet"` |
| `amountIn` / `amountOut` | string/number, optional | specify one; probes used `amountIn` |

> **Precondition for every conversion test:** the request needs integer **wallet ids**,
> not currency codes. So each E2E test must first `GET /api/wallet` and resolve the
> source/target currency to its wallet id.

## Fee model (confirmed by probe)

Service fee is **0.01%**, charged in the **source** currency and skimmed off the input
*before* conversion:

```
fee       = amountIn × 0.0001
amountOut = (amountIn − fee) × price
```

Worked example (1 ETH → TRX, `price = 12405.40540541`):
```
fee       = 1 × 0.0001            = 0.0001 ETH
amountOut = (1 − 0.0001) × price  = 12404.164865 TRX   ✓ matches response
```

Relevant response fields:
- `price` — exchange rate (here `netPrice == grossPrice == price`)
- `fee` — fee amount in source currency (`"0.0001"`)
- `fees.percentage.service` — the percentage as a number (`"0.01"` = 0.01%)
- `fees.value.service` — fee amount in source currency (`"0.0001"`)
- `processingFee` / `fees.*.processing` — `"0"` in observed trades

## Rounding of reported numbers — `amountOut` cannot be derived exactly ⚠️

The simulator prices the trade with an **internal full-precision rate it never exposes**, then
rounds the published fields **independently**:

- `price` → rounded to the currency's `pricePrecision` (8 dp for all three currencies);
  `netPrice` and `grossPrice` are the **same rounded value**, not the internal rate.
  `price` is a pair-level rate, and **which side's `pricePrecision` governs it is unverifiable**
  while every currency uses 8 dp — the asserter assumes the **target** side. Revisit if a
  currency with a different `pricePrecision` ever appears.
- `amountOut` → computed from the *internal* rate, rounded to the **target** currency's
  `quantityPrecision` (ROUND_HALF_UP).
- `fee` → exact: `amountIn × 0.0001` at the source currency's `quantityPrecision`.

Consequence: deriving `expected_amount_out = (amountIn − fee) × price` from the *reported* price
carries an error of up to `(amountIn − fee) × 5e-9` (the max rounding error of an 8-dp price),
which can exceed the last digit of `amountOut` whenever `amountIn` is large relative to the
price scale.

Probed evidence (987 TRX → ETH): reported `price = "0.00008085"`, reported
`amountOut = "0.07979202"` → implied internal rate `0.000080851063…`, which rounds back to the
reported price, while `expected_amount_out` derived from the rounded price is off by ~1.05e-6 —
about 105 units of ETH's 8th decimal (the derived bound allows up to `986.9 × 5e-9 ≈ 493`
units). The 420 TRX → USDT pair sits *on* the boundary — the expected value matched in some runs
and missed by one ulp in others (observed both). 1 ETH → TRX always matches because
`(amountIn − fee) × 5e-9 ≈ 5e-9` is far below the max rounding error of TRX's 6-dp amounts —
which is why the worked example above happens to reproduce the response exactly.

The inverse check (`price == round(amountOut / (amountIn − fee), 8)`) fails in the opposite
direction (e.g. ETH → TRX), where `amountOut`'s own rounding dominates. Neither direction is
exact for all pairs.

**Implication for asserters:** compare `expected_amount_out` within
`(amountIn − fee) × max_rounding_error(pricePrecision) + max_rounding_error(quantityPrecision)`
— not by exact rounded equality, and not with an arbitrary epsilon. (Rule recorded in
`.claude/CLAUDE.md`; implemented in `engine/api_asserters/conversion.py`.)
`expected_fee` **is** exact and stays an equality check.

## Quote lifecycle — settlement is ASYNCHRONOUS ⚠️

Accepting a quote returns `200` **immediately**, but the trade settles a few seconds
later. Balances are **not** updated at accept time.

| Stage | `quoteStatus` | `paymentStatus` | Wallet balances |
|---|---|---|---|
| after create | `PENDING` | `PENDING` | unchanged |
| after accept (immediate) | `ACCEPTED` | `PROCESSING` | **unchanged** |
| ~5–8s later (settled) | `PAYMENT_OUT_PROCESSED` | `SUCCESS` | **updated** |

At settlement the wallet deltas are exact:
- **source** wallet balance: `− amountIn` (the whole input, fee included)
- **target** wallet balance: `+ amountOut`

Lifecycle-dependent quote fields (probed across create → accept → settle):
- `amountDue` — the **outstanding** amount, not an echo of `amountIn`: equals `amountIn`
  while `PENDING`/`ACCEPTED`, drops to `"0"` at settlement.
- `amountInNet` / `amountInGross` — **both equal `amountIn` at every stage**. `amountInNet`
  does **not** subtract the service fee (the fee is only reflected in `amountOut`); plausibly
  it is net of the *processing* fee, which is `0` in all observed trades — unverifiable.

Other timing facts:
- `acceptanceExpiryDate` ≈ create time + **20s** (the quote-accept window from the PDF).
- `paymentExpiryDate` ≈ create time + **~6 min** (separate, longer payment window).
- `acceptanceDate` is set on accept; `paymentReceiptDate` was still `null` even at
  `SUCCESS` in probes.

### Implications for tests
1. **E2E flow:** create → accept → **poll** `GET /api/v1/quote/{uuid}` until
   `paymentStatus == SUCCESS` (timeout ~30s) → snapshot balances → assert deltas.
   Do **not** assert balances right after accept.
2. **Assert against the quote's own numbers** (`amountIn`, `amountOut`, `price`), because
   forex rates fluctuate between runs — never hard-code absolute rates/outputs.
3. Natural edge test: accept but don't wait → confirm balances have **not** moved yet
   (`paymentStatus == PROCESSING`).

## Wallet object (fields worth asserting)

`balance`, `available`, `convertedAvailable` (all Decimal strings), `currency` (nested
object with `.code`, `.name`, `.fiat`, precision, protocols), `id`, `status`, `address`.
In observed trades `balance` and `available` moved together; pick `balance` for delta
assertions unless a test specifically targets the available/pending distinction.

Probed invariants (single account, before vs. after a settled conversion):
- `approxBalance` / `approxAvailable` **mirror `balance` / `available` exactly** (identical
  strings), including after settlement — "approx" is not rounded or lagged in the simulator.
- `address` (simulated blockchain address, `simulated-address-<n>`) and `lsid` are **stable
  across conversions** within an account; addresses differ between accounts (each `/init`
  provisions fresh wallets).

### ⚠️ Potential issue (unconfirmed) — `convertedAvailable` / `approxConvertedAvailable`

Both read `"10000"` on **every** wallet in **every** capture, before and after conversion,
regardless of the wallet's actual balance. A fiat-equivalent value that never reflects
balance changes is **suspected simulator misbehaviour** — a real API would recompute it —
but it could also be an intentional stub. **Needs confirmation with the API owner** before
it can be classified as a bug or asserted as a contract. Left unmodeled and unasserted
until then; once confirmed as computed, it belongs in the wallet-impact assertions
(presumably as `balance × <some fiat rate>`-style bounds).
