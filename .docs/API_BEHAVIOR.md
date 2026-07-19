# Simulator API — Observed Behaviour

Reference notes from probing the live simulator.
These document *observed* behaviour (verified against real responses), which drives the
test design, models, and asserters. Raw sanitized samples are in `docs/api-samples/`.

> **Host gotcha:** the live API host (set via `API_BASE_URL` in the local `.env`) carries
> an extra **`api`** segment in its hostname. The host printed in the task PDF (without
> `api`) is dead ("Coming Soon"). Swagger UI at `/docs`, OpenAPI spec at `/openapi.json`.

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
- `fee` → exact: `amountIn × 0.0001` at the source currency's `quantityPrecision` — but see
  "Excess input precision" below: for inputs finer than `quantityPrecision`, the fee is
  computed from the **unrounded** requested amount, not the quote's own echoed `amountIn`.

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
`(amountIn − fee) × rounding_tolerance(pricePrecision) + rounding_tolerance(quantityPrecision)`
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
| >20s, never accepted | `EXPIRED` | `EXPIRED` | unchanged |

Probed accept-path outcomes:
- **Re-accepting** an already-accepted quote — while `PROCESSING` *or* after `SUCCESS` — returns
  `400 {"detail": "Bad Request"}` and the conversion is applied **exactly once** (no double
  spend on the re-accept path).
- **Accepting an expired quote** returns `412 {"detail": "Precondition Failed"}`; the quote
  stays `EXPIRED`/`EXPIRED` and balances stay untouched. The status flip to `EXPIRED` happens
  server-side (observed on a plain GET ~25s after create, no accept attempt needed).

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

## Error contract (probed)

Every error response is a single-field body `{"detail": "<message>"}`. Observed statuses:

| Status | Trigger | `detail` |
|---|---|---|
| 400 | zero / missing / both `amountIn`+`amountOut` | `One of 'amountIn' or 'amountOut' must be specified but not both.` |
| 400 | `from` currency ≠ source wallet's currency (incl. unknown codes like `XYZ`) | `Request to trade {from} for {to} but source wallet has currency {wallet currency}.` |
| 400 | `fromWallet` id not visible to the account (another account's id, or bogus) | `Source wallet with ID #{id} not found.` |
| 400 | re-accepting an accepted/settled quote | `Bad Request` |
| 404 | GET/accept unknown quote uuid; GET unknown wallet id | `Not Found` |
| 412 | `amountIn` exceeds source wallet `available` (checked at **create**) | `Insufficient funds available in source wallet #{id}.` |
| 412 | accepting an expired quote | `Precondition Failed` |

Notes:
- **Zero `amountIn` is treated as "not specified"** (falsy), so the rejection message is the
  misleading amountIn/amountOut one, not a "must be positive" validation — cosmetic quirk.
- There is no dedicated currency whitelist error: an unknown `from` code surfaces as the
  wallet-currency mismatch message.

## Amount validation (probed)

- **Insufficient funds are rejected at quote create** (`412`), checked against the source
  wallet's `available`. Create/accept of an exact-full-balance amount works: the fee is
  skimmed *inside* `amountIn`, and after settlement the source wallet lands on exactly `0`
  (reported as `"0E-8"` — a zero `Decimal` at the currency's precision).
- **Creating a quote reserves nothing**: after a pending quote for 0.5 of 3.7 ETH, both
  `balance` and `available` still read the full 3.7. Multiple live quotes can therefore
  collectively promise more than the balance (see the concurrency bug below).
- **Excess input precision** (`amountIn` finer than the source `quantityPrecision`, e.g.
  `0.123456789012` ETH): the quote's `amountIn` echo is rounded HALF_UP to
  `quantityPrecision` (`0.12345679`), but **`fee` is computed from the unrounded requested
  amount** (`0.0000123456789012`, 16 dp) — the quote is internally inconsistent
  (`fee ≠ amountIn × 0.0001` for its own reported `amountIn`). Suspected bug; the fee
  consistency test is `xfail`-documented.

### ⚠️ Confirmed bug — negative `amountIn` settles in reverse

`amountIn = -1` (ETH→TRX) is **accepted** (`201`) with negative `fee` and `amountOut`,
accepts normally, and **settles**: the source wallet is *credited* `+1 ETH` and the target
*debited* `-12350 TRX`. A negative amount effectively runs the conversion backwards at the
forward rate and *earns* the fee — no validation anywhere in the lifecycle. The rejection
test is `xfail`-documented until the simulator is fixed.

## Request amount modes (probed)

- `useMaximum: true` is a **no-op**: with `amountIn` present the flag is ignored; without
  `amountIn` the request is rejected with the amountIn/amountOut 400. There is no working
  "convert everything" mode. (Untested against `useMinimum`, presumed symmetric.)
- **`amountOut`-only quotes are supported**: the API computes `amountIn` and returns
  `price` as the *inverse* rate (source per unit of target, e.g. `0.00007957` ETH/TRX
  instead of ~12500 TRX/ETH). `fee` comes back in scientific notation at full precision
  (e.g. `7.956989247311827956989247313E-7`). Out of scope for Goal 3 — candidate for a
  future test category.
- Specifying **both** `amountIn` and `amountOut` → the same 400.

### ⚠️ Confirmed bug — concurrent settlements lose updates

Two quotes accepted back-to-back (~1s apart, both `SUCCESS` at the end) settle by applying
their deltas to a **stale balance snapshot** — the last settlement wins and the first
one's wallet impact vanishes (classic lost update). Observed with 2+2 ETH quotes on a
3.7 ETH wallet: both quotes report `SUCCESS`/`amountDue: 0`, but final balances reflect
only the second quote (`ETH 1.7`, one credit on TRX). This also silently masks the
overdraw the two accepts should have produced. **Sequential** conversions (settle, then
accept the next) accumulate correctly. The combined-deltas test is `xfail`-documented
(non-strict — the race's determinism is unverified).

## Transport — idle keep-alive sockets are dropped

The host silently drops keep-alive connections left idle for ~10s+; the next request on
the stale socket fails with a transport `ConnectionError` (observed: a single 15s
`sleep` before an accept). Requests spaced ≤ the settlement poll interval never hit
this. Any wait longer than a few seconds must **poll** (keeping the socket warm — see
`flows.hold_quote` / `wait_for_expiry`), never sleep in one block.

## Parity & identifiers (probed)

- `GET /api/wallet/{id}` returns the identical object to that wallet's entry in
  `GET /api/wallet`; the quote list `GET /api/v1/quote` is a **plain JSON array** of full
  quote objects (no pagination wrapper), insertion-ordered.
- A quote fetched immediately after create is **byte-identical** to the create response
  (zero field drift while `PENDING`) — create-vs-get parity can compare all fields.
- **Wallet ids are globally sequential across accounts** (one account got 550/551/552, the
  next 553/554/555), so another account's id is a *real, existing* id — yet quote create
  with it is properly rejected (`400 Source wallet ... not found.`) and the other account
  is untouched: cross-account isolation holds.
