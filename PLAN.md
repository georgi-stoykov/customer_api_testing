# BVNK QA Task — Currency Conversion API Test Project

## Context

Take-home task for a QA Engineer position at BVNK: build an API test project against
`http://bvnksimulator.pythonanywhere.com` covering 3 mandatory E2E currency conversion
flows plus ≥2 extra tests, with a report output, submitted as a Git repo. The code is
interview-discussion material — rationale and testing principles matter more than polish.

**Collaboration model (important):** Claude is the main writer; Georgi contributes by
writing occasionally and steers all design decisions. Discuss design before implementing
each component — planning and understanding matter more than speed. This is interview
prep material, so Georgi must be able to explain and defend every choice.

**Blocker:** As of 2026-07-16 the simulator returns PythonAnywhere's "Coming Soon" page
(no live web app). Re-check periodically; contact BVNK if it stays down. Final assertion
details (field names, fee semantics) must be confirmed against the live API before coding
assertions.

## Stack (agreed)

- Python + pytest, `requests` for HTTP
- `Decimal` for all money math (parse JSON amounts with `Decimal`, never float)
- `pytest-html` for the report (self-contained, no accounts/CLI needed — satisfies the
  licensing constraint; Allure needs a separate CLI)
- GitHub for hosting; optional GitHub Actions workflow as a bonus

## Project structure (agreed — Georgi's C# engine/tests convention)

```
CurrencyConversionApiAutomation/
├── README.md                  # setup, run instructions, testing rationale
├── requirements.txt
├── pytest.ini                 # markers, report config
├── engine/                    # the "framework" — no test logic here
│   ├── config.py              # base URL, timeouts (env-overridable)
│   ├── clients/               # API drivers
│   │   ├── base_client.py     # requests.Session, bearer auth, request/response logging
│   │   ├── auth_api.py        # GET /init, POST /echo
│   │   ├── wallet_api.py      # GET /api/wallet, GET /api/wallet/{id}
│   │   └── quote_api.py       # POST /api/v1/quote, accept, GET quote
│   ├── models/                # pydantic: Wallet, Quote — automatic schema validation
│   │                          #   on every deserialization (extra/strict types)
│   └── asserters/             # domain asserters — business-math validation
│       ├── conversion_asserter.py  # balance deltas vs quote rate + 0.01% fee
│       └── money.py                # Decimal helpers, tolerance comparison
└── tests/
    ├── conftest.py            # session-scoped /init fixture → authed client
    ├── e2e/
    │   └── test_conversions.py   # 3 mandatory tests, parametrized (from, to, amount)
    └── negative/                 # extra tests (choice TBD)
```

**Assertion strategy (agreed):** two-layer validation —
- **Schema layer:** pydantic models validate structure/types implicitly whenever a client
  parses a response. An API field change fails every test with no asserter edits.
- **Business layer:** named asserter classes (e.g. `ConversionAsserter`) hold the
  domain checks: source wallet debited by input amount, target credited per quoted rate
  minus 0.01% fee, all Decimal. Tests call specific well-named methods so the test body
  still reads as "what is verified" (BVNK grades test-code clarity).

## Key design decisions (agreed rationale)

1. **Rates fluctuate → assert internal consistency, not absolute values.** Capture rate
   from the quote response itself; assert
   `source_wallet_delta == -amount_in` and
   `target_wallet_delta == quoted_output − fee` (exact semantics TBD from live API).
2. **Fee is 0.01%** — probe live API first to learn whether fee is deducted from output,
   charged separately, or baked into rate; then assert exactly.
3. **20s quote expiry** — E2E flow accepts immediately after create; expiry is also a
   candidate negative test (uses ~21s wait).
4. **One `/init` per session** (session-scoped fixture): before/after balance deltas make
   shared account state safe; faster than per-test init. Defensible trade-off.
5. **Test scope: comprehensive, not minimal.** Georgi wants to cover the whole API, not
   just the 3+2 mandatory tests. The full test list is deliberately deferred to a
   dedicated test-design session held AFTER probing the live API (design against observed
   behavior, not guesses). Candidate pool discussed so far: auth negatives, expired-quote
   accept, double-accept idempotency, invalid pair / negative amount / insufficient
   balance, 404s on unknown wallet/quote, `/echo` sanity. Test design will likely produce
   a per-endpoint test matrix.

## Execution phases

Each phase starts with a short design discussion before code (per collaboration model).

1. **Scaffold the skeleton** (not blocked by the dead simulator): git init + add remote
   `git@github.com:georgi-stoykov/CurrencyConversionApiAutomation.git` (created by
   Georgi; push only when he says so), requirements,
   pytest.ini, `engine/` package layout (base client, client stubs, config), conftest
   skeleton, README skeleton, pytest-html wiring.
2. **Probe the live API** (once it's up): hit `/init`, `/docs`, create+accept a quote
   manually; capture real request/response JSON into `docs/api-samples/`. This determines
   pydantic model fields, fee semantics, and error formats.
3. **Test-design session**: build the per-endpoint test matrix from observed behavior;
   prioritize (3 mandatory E2E first, then breadth).
4. **Implement**: models + asserters, then E2E conversion tests, then the wider suite —
   design-discuss each component first, Georgi writes portions where he wants hands-on.
5. **Polish & submit**: README rationale section, verify report output, fresh-clone
   check, push to GitHub.

## Verification

- `pytest --html=reports/report.html` runs green against the live simulator.
- Manually cross-check one conversion's math (rate, fee, deltas) against captured API
  responses.
- Fresh-clone test: clone repo elsewhere, `pip install -r requirements.txt`, run — proves
  the README instructions work.
