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
