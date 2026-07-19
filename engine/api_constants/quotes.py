# Domain facts of the quote lifecycle (observed, .docs/API_BEHAVIOR.md), not deployment
# config — plain constants, unlike the env-tunable settlement timings.

# acceptanceExpiryDate = create time + 20s.
ACCEPTANCE_WINDOW = 20.0

# A "late but valid" accept fires this long before expiry — enough margin that network
# latency cannot push the accept past the boundary (a literal last-second accept would
# race the wall clock and flake).
LATE_ACCEPT_MARGIN = 5.0

# Waiting for the EXPIRED status flip: the window itself plus grace for the flip and polling.
EXPIRY_TIMEOUT = ACCEPTANCE_WINDOW + 15.0
