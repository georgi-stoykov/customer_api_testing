from decimal import ROUND_HALF_UP, Decimal
from engine.constants.currencies import Currency
from engine.constants.fees import CONVERSION_FEE_RATE
from engine.customer_api.models.quotes import PaymentStatus, Quote, QuoteStatus
from engine.customer_api.models.wallets import AccountWallets


def _quantized(value: Decimal, precision: int) -> Decimal:
    return value.quantize(Decimal(1).scaleb(-precision), rounding=ROUND_HALF_UP)


def _half_quantum(precision: int) -> Decimal:
    return Decimal(5).scaleb(-precision - 1)


class ConversionAsserter:
    def assert_wallet_deltas(
        self,
        *,
        quote: Quote,
        wallets_before: AccountWallets,
        wallets_after: AccountWallets,
        from_currency: Currency,
        to_currency: Currency,
    ) -> None:
        source_delta = (
            wallets_before.by_currency(from_currency).balance
            - wallets_after.by_currency(from_currency).balance
        )
        target_delta = (
            wallets_after.by_currency(to_currency).balance
            - wallets_before.by_currency(to_currency).balance
        )
        assert source_delta == quote.amount_in, (
            f"source delta ({from_currency}): expected {quote.amount_in}, got {source_delta}"
        )
        assert target_delta == quote.amount_out, (
            f"target delta ({to_currency}): expected {quote.amount_out}, got {target_delta}"
        )

    def assert_fee_recomputed(
        self,
        *,
        quote: Quote,
        wallets: AccountWallets,
        from_currency: Currency,
    ) -> None:
        precision = wallets.by_currency(from_currency).currency.quantity_precision
        expected_fee = _quantized(quote.amount_in * CONVERSION_FEE_RATE, precision)
        assert quote.fee == expected_fee, (
            f"fee ({from_currency}): expected amountIn x {CONVERSION_FEE_RATE} = {expected_fee}, "
            f"got {quote.fee}"
        )

    def assert_amount_out_recomputed(
        self,
        *,
        quote: Quote,
        wallets: AccountWallets,
        to_currency: Currency,
    ) -> None:
        target = wallets.by_currency(to_currency).currency
        net_amount = quote.amount_in - quote.fee
        recomputed = net_amount * quote.price
        tolerance = net_amount * _half_quantum(target.price_precision) + _half_quantum(
            target.quantity_precision,
        )
        deviation = abs(recomputed - quote.amount_out)
        assert deviation <= tolerance, (
            f"amountOut ({to_currency}): expected (amountIn - fee) x price = {recomputed} "
            f"within {tolerance}, got {quote.amount_out} (off by {deviation})"
        )

    def assert_quote_echoes_request(
        self,
        *,
        quote: Quote,
        from_currency: Currency,
        to_currency: Currency,
        amount_in: str | Decimal,
    ) -> None:
        requested_amount = Decimal(str(amount_in))
        assert quote.from_ == from_currency, (
            f"quote from: expected {from_currency}, got {quote.from_}"
        )
        assert quote.to == to_currency, f"quote to: expected {to_currency}, got {quote.to}"
        assert quote.amount_in == requested_amount, (
            f"quote amountIn: expected {requested_amount}, got {quote.amount_in}"
        )

    def assert_terminal_statuses(self, quote: Quote) -> None:
        assert quote.quote_status == QuoteStatus.PAYMENT_OUT_PROCESSED, (
            f"quoteStatus: expected {QuoteStatus.PAYMENT_OUT_PROCESSED}, got {quote.quote_status}"
        )
        assert quote.payment_status == PaymentStatus.SUCCESS, (
            f"paymentStatus: expected {PaymentStatus.SUCCESS}, got {quote.payment_status}"
        )

    def assert_untouched_balance(
        self,
        *,
        wallets_before: AccountWallets,
        wallets_after: AccountWallets,
        currency: Currency,
    ) -> None:
        balance_before = wallets_before.by_currency(currency).balance
        balance_after = wallets_after.by_currency(currency).balance
        assert balance_after == balance_before, (
            f"untouched balance ({currency}): expected {balance_before}, got {balance_after}"
        )

    def assert_settled_conversion(
        self,
        *,
        quote: Quote,
        wallets_before: AccountWallets,
        wallets_after: AccountWallets,
        from_currency: Currency,
        to_currency: Currency,
        amount_in: str | Decimal,
    ) -> None:
        self.assert_quote_echoes_request(
            quote=quote,
            from_currency=from_currency,
            to_currency=to_currency,
            amount_in=amount_in,
        )
        self.assert_terminal_statuses(quote)
        self.assert_fee_recomputed(
            quote=quote,
            wallets=wallets_after,
            from_currency=from_currency,
        )
        self.assert_amount_out_recomputed(
            quote=quote,
            wallets=wallets_after,
            to_currency=to_currency,
        )
        self.assert_wallet_deltas(
            quote=quote,
            wallets_before=wallets_before,
            wallets_after=wallets_after,
            from_currency=from_currency,
            to_currency=to_currency,
        )
        for currency in Currency:
            if currency not in (from_currency, to_currency):
                self.assert_untouched_balance(
                    wallets_before=wallets_before,
                    wallets_after=wallets_after,
                    currency=currency,
                )
