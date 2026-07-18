from decimal import Decimal
from engine.api_constants.currencies import Currency
from engine.api_constants.fees import CONVERSION_FEE_RATE
from engine.api_models.quotes import PaymentStatus, Quote, QuoteStatus
from engine.api_models.wallets import AccountWallets, Wallet, WalletCurrency
from engine.utils import monetary


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
        source_balance_delta = (
            wallets_before.by_currency(from_currency).balance
            - wallets_after.by_currency(from_currency).balance
        )
        target_balance_delta = (
            wallets_after.by_currency(to_currency).balance
            - wallets_before.by_currency(to_currency).balance
        )
        monetary.assert_equal(
            actual=source_balance_delta,
            expected=quote.amount_in,
            context=f"source wallet delta ({from_currency})",
        )
        monetary.assert_equal(
            actual=target_balance_delta,
            expected=quote.amount_out,
            context=f"target wallet delta ({to_currency})",
        )

    def assert_fee(
        self,
        *,
        quote: Quote,
        source_currency: WalletCurrency,
    ) -> None:
        expected_fee = monetary.round_half_up(
            quote.amount_in * CONVERSION_FEE_RATE,
            source_currency.quantity_precision,
        )
        monetary.assert_equal(
            actual=quote.fee,
            expected=expected_fee,
            context=f"fee = amountIn x {CONVERSION_FEE_RATE} ({source_currency.code})",
        )

    def assert_amount_out(
        self,
        *,
        quote: Quote,
        target_currency: WalletCurrency,
    ) -> None:
        net_amount_in = quote.amount_in - quote.fee
        expected_amount_out = net_amount_in * quote.price
        allowed_rounding_error = net_amount_in * monetary.max_rounding_error(
            target_currency.price_precision
        ) + monetary.max_rounding_error(target_currency.quantity_precision)
        monetary.assert_equal_within(
            actual=quote.amount_out,
            expected=expected_amount_out,
            allowed_error=allowed_rounding_error,
            context=f"amountOut = (amountIn - fee) x price ({target_currency.code})",
        )

    def assert_quote_echoes_request(
        self,
        *,
        quote: Quote,
        from_currency: Currency,
        to_currency: Currency,
        amount_in: str | Decimal,
    ) -> None:
        requested_amount_in = Decimal(str(amount_in))
        assert quote.from_ == from_currency, (
            f"quote from: expected {from_currency}, got {quote.from_}"
        )
        assert quote.to == to_currency, f"quote to: expected {to_currency}, got {quote.to}"
        monetary.assert_equal(
            actual=quote.amount_in,
            expected=requested_amount_in,
            context="quote amountIn",
        )

    def assert_success_terminal(self, quote: Quote) -> None:
        assert quote.quote_status == QuoteStatus.PAYMENT_OUT_PROCESSED, (
            f"quoteStatus: expected {QuoteStatus.PAYMENT_OUT_PROCESSED}, got {quote.quote_status}"
        )
        assert quote.payment_status == PaymentStatus.SUCCESS, (
            f"paymentStatus: expected {PaymentStatus.SUCCESS}, got {quote.payment_status}"
        )

    def assert_wallets_equal(
        self,
        *,
        expected_wallet: Wallet,
        actual_wallet: Wallet,
    ) -> None:
        wallet_context = f"wallet ({expected_wallet.currency.code})"
        monetary.assert_equal(
            actual=actual_wallet.balance,
            expected=expected_wallet.balance,
            context=f"{wallet_context} balance",
        )
        monetary.assert_equal(
            actual=actual_wallet.available,
            expected=expected_wallet.available,
            context=f"{wallet_context} available",
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
        self.assert_success_terminal(quote)
        self.assert_fee(
            quote=quote,
            source_currency=wallets_after.by_currency(from_currency).currency,
        )
        self.assert_amount_out(
            quote=quote,
            target_currency=wallets_after.by_currency(to_currency).currency,
        )
        self.assert_wallet_deltas(
            quote=quote,
            wallets_before=wallets_before,
            wallets_after=wallets_after,
            from_currency=from_currency,
            to_currency=to_currency,
        )
        for uninvolved_currency in Currency:
            if uninvolved_currency not in (from_currency, to_currency):
                self.assert_wallets_equal(
                    expected_wallet=wallets_before.by_currency(uninvolved_currency),
                    actual_wallet=wallets_after.by_currency(uninvolved_currency),
                )
