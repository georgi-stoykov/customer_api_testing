from decimal import Decimal
from engine.api_constants.currencies import Currency
from engine.api_constants.fees import CONVERSION_FEE_RATE
from engine.api_models.quotes import PaymentStatus, Quote, QuoteStatus
from engine.api_models.wallets import AccountWallets, Wallet, WalletCurrency, WalletStatus
from engine.utils import checks, monetary


class ConversionAsserter:
    def assert_wallet_deltas(
        self,
        *,
        quote: Quote,
        source_before: Wallet,
        source_after: Wallet,
        target_before: Wallet,
        target_after: Wallet,
    ) -> None:
        monetary.assert_equal(
            actual=source_before.balance - source_after.balance,
            expected=quote.amount_in,
            context=f"source wallet balance delta ({source_before.currency.code})",
        )
        monetary.assert_equal(
            actual=source_before.available - source_after.available,
            expected=quote.amount_in,
            context=f"source wallet available delta ({source_before.currency.code})",
        )
        monetary.assert_equal(
            actual=target_after.balance - target_before.balance,
            expected=quote.amount_out,
            context=f"target wallet balance delta ({target_before.currency.code})",
        )
        monetary.assert_equal(
            actual=target_after.available - target_before.available,
            expected=quote.amount_out,
            context=f"target wallet available delta ({target_before.currency.code})",
        )

    def assert_conversion_math(
        self,
        *,
        quote: Quote,
        source_currency: WalletCurrency,
        target_currency: WalletCurrency,
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
        # price is a pair-level rate; which side's pricePrecision bounds it is unverifiable
        # while every simulator currency uses 8 dp — the target side is assumed.
        net_amount_in = quote.amount_in - quote.fee
        expected_amount_out = net_amount_in * quote.price
        price_rounding_error = net_amount_in * monetary.rounding_tolerance(
            target_currency.price_precision
        )
        amount_out_rounding_error = monetary.rounding_tolerance(target_currency.quantity_precision)
        monetary.assert_equal_with_tolerance(
            actual=quote.amount_out,
            expected=expected_amount_out,
            tolerance=price_rounding_error + amount_out_rounding_error,
            context=f"amountOut = (amountIn - fee) x price ({target_currency.code})",
        )

    def assert_quote_echoes_request(
        self,
        *,
        quote: Quote,
        from_currency: Currency,
        to_currency: Currency,
        amount_in: Decimal,
        source_wallet_id: int,
        target_wallet_id: int,
    ) -> None:
        checks.assert_equal(actual=quote.from_, expected=from_currency, context="quote from")
        checks.assert_equal(actual=quote.to, expected=to_currency, context="quote to")
        monetary.assert_equal(
            actual=quote.amount_in,
            expected=amount_in,
            context="quote amountIn vs requested amount",
        )
        checks.assert_equal(
            actual=quote.use_pay_in_method.id,
            expected=source_wallet_id,
            context="quote usePayInMethod wallet id",
        )
        checks.assert_equal(
            actual=quote.use_pay_out_method.id,
            expected=target_wallet_id,
            context="quote usePayOutMethod wallet id",
        )

    def assert_settled_quote_consistency(self, quote: Quote) -> None:
        for actual, expected, context in (
            (quote.amount_in_gross, quote.amount_in, "quote amountInGross vs amountIn"),
            (quote.amount_in_net, quote.amount_in, "quote amountInNet vs amountIn"),
            (quote.amount_due, Decimal("0"), "quote amountDue after settlement"),
            (quote.fees.value.service, quote.fee, "quote fees.value.service vs fee"),
            (quote.processing_fee, Decimal("0"), "quote processingFee"),
            (quote.net_price, quote.price, "quote netPrice vs price"),
            (quote.gross_price, quote.price, "quote grossPrice vs price"),
        ):
            monetary.assert_equal(actual=actual, expected=expected, context=context)

    def assert_quote_settled(self, quote: Quote) -> None:
        checks.assert_equal(
            actual=quote.quote_status,
            expected=QuoteStatus.PAYMENT_OUT_PROCESSED,
            context="quoteStatus",
        )
        checks.assert_equal(
            actual=quote.payment_status,
            expected=PaymentStatus.SUCCESS,
            context="paymentStatus",
        )

    def assert_wallet_count_unchanged(
        self,
        *,
        wallets_before: AccountWallets,
        wallets_after: AccountWallets,
    ) -> None:
        checks.assert_equal(
            actual=len(wallets_after),
            expected=len(wallets_before),
            context="wallet count",
        )

    def assert_wallet_identity(
        self,
        *,
        expected_wallet: Wallet,
        actual_wallet: Wallet,
    ) -> None:
        wallet_context = expected_wallet.label
        checks.assert_equal(
            actual=actual_wallet.id,
            expected=expected_wallet.id,
            context=f"{wallet_context} id",
        )
        checks.assert_equal(
            actual=actual_wallet.currency.code,
            expected=expected_wallet.currency.code,
            context=f"{wallet_context} currency",
        )
        checks.assert_equal(
            actual=actual_wallet.address,
            expected=expected_wallet.address,
            context=f"{wallet_context} address",
        )

    def assert_wallet_active(self, wallet: Wallet) -> None:
        checks.assert_equal(
            actual=wallet.status,
            expected=WalletStatus.ACTIVE,
            context=f"{wallet.label} status",
        )

    def assert_wallet_approx_fields(self, wallet: Wallet) -> None:
        wallet_context = wallet.label
        monetary.assert_equal(
            actual=wallet.approx_balance,
            expected=wallet.balance,
            context=f"{wallet_context} approxBalance vs balance",
        )
        monetary.assert_equal(
            actual=wallet.approx_available,
            expected=wallet.available,
            context=f"{wallet_context} approxAvailable vs available",
        )

    def assert_wallets_equal(
        self,
        *,
        expected_wallet: Wallet,
        actual_wallet: Wallet,
    ) -> None:
        wallet_context = expected_wallet.label
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
        amount_in: Decimal,
    ) -> None:
        source_before = wallets_before.by_currency(from_currency)
        source_after = wallets_after.by_currency(from_currency)
        target_before = wallets_before.by_currency(to_currency)
        target_after = wallets_after.by_currency(to_currency)
        self.assert_quote_echoes_request(
            quote=quote,
            from_currency=from_currency,
            to_currency=to_currency,
            amount_in=amount_in,
            source_wallet_id=source_before.id,
            target_wallet_id=target_before.id,
        )
        self.assert_quote_settled(quote)
        self.assert_settled_quote_consistency(quote)
        self.assert_conversion_math(
            quote=quote,
            source_currency=source_after.currency,
            target_currency=target_after.currency,
        )
        self.assert_wallet_count_unchanged(
            wallets_before=wallets_before,
            wallets_after=wallets_after,
        )
        self.assert_wallet_deltas(
            quote=quote,
            source_before=source_before,
            source_after=source_after,
            target_before=target_before,
            target_after=target_after,
        )
        for wallet_before in wallets_before:
            wallet_after = wallets_after.by_id(wallet_before.id)
            self.assert_wallet_identity(
                expected_wallet=wallet_before,
                actual_wallet=wallet_after,
            )
            self.assert_wallet_active(wallet_before)
            self.assert_wallet_active(wallet_after)
            self.assert_wallet_approx_fields(wallet_before)
            self.assert_wallet_approx_fields(wallet_after)
            if wallet_before.currency.code not in (from_currency, to_currency):
                self.assert_wallets_equal(
                    expected_wallet=wallet_before,
                    actual_wallet=wallet_after,
                )
