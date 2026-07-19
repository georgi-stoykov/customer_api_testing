AMOUNT_NOT_SPECIFIED = "One of 'amountIn' or 'amountOut' must be specified but not both."


def insufficient_funds(wallet_id: int) -> str:
    return f"Insufficient funds available in source wallet #{wallet_id}."


def source_wallet_not_found(wallet_id: int) -> str:
    return f"Source wallet with ID #{wallet_id} not found."


def currency_mismatch(
    *,
    from_currency: str,
    to_currency: str,
    wallet_currency: str,
) -> str:
    return (
        f"Request to trade {from_currency} for {to_currency} "
        f"but source wallet has currency {wallet_currency}."
    )
