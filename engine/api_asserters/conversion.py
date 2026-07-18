from decimal import Decimal
from engine.api_constants.currencies import Currency
from engine.api_constants.fees import CONVERSION_FEE_RATE
from engine.api_models.quotes import PaymentStatus, Quote, QuoteStatus
from engine.api_models.wallets import AccountWallets, Wallet, WalletCurrency, WalletStatus
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
        source_before = wallets_before.by_currency(from_currency)
        source_after = wallets_after.by_currency(from_currency)
        target_before = wallets_before.by_currency(to_currency)
        target_after = wallets_after.by_currency(to_currency)
        monetary.assert_equal(
            actual=source_before.balance - source_after.balance,
            expected=quote.amount_in,
            context=f"source wallet balance delta ({from_currency})",
        )
        monetary.assert_equal(
            actual=source_before.available - source_after.available,
            expected=quote.amount_in,
            context=f"source wallet available delta ({from_currency})",
        )
        monetary.assert_equal(
            actual=target_after.balance - target_before.balance,
            expected=quote.amount_out,
            context=f"target wallet balance delta ({to_currency})",
        )
        monetary.assert_equal(
            actual=target_after.available - target_before.available,
            expected=quote.amount_out,
            context=f"target wallet available delta ({to_currency})",
        )

    def assert_conversion_math(
        self,
        *,
        quote: Quote,
        requested_amount_in: str | Decimal,
        source_currency: WalletCurrency,
        target_currency: WalletCurrency,
    ) -> None:
        monetary.assert_equal(
            actual=quote.amount_in,
            expected=Decimal(str(requested_amount_in)),
            context="quote amountIn vs requested amount",
        )
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
        allowed_rounding_error = net_amount_in * monetary.max_rounding_error(
            target_currency.price_precision
        ) + monetary.max_rounding_error(target_currency.quantity_precision)
        monetary.assert_equal_within(
            actual=quote.amount_out,
            expected=expected_amount_out,
            allowed_error=allowed_rounding_error,
            context=f"amountOut = (amountIn - fee) x price ({target_currency.code})",
        )

    def assert_quote_uses_requested_wallets(
        self,
        *,
        quote: Quote,
        from_currency: Currency,
        to_currency: Currency,
        source_wallet_id: int,
        target_wallet_id: int,
    ) -> None:
        assert quote.from_ == from_currency, (
            f"quote from: expected {from_currency}, got {quote.from_}"
        )
        assert quote.to == to_currency, f"quote to: expected {to_currency}, got {quote.to}"
        assert quote.use_pay_in_method.id == source_wallet_id, (
            f"quote usePayInMethod: expected wallet {source_wallet_id}, "
            f"got {quote.use_pay_in_method.id}"
        )
        assert quote.use_pay_out_method.id == target_wallet_id, (
            f"quote usePayOutMethod: expected wallet {target_wallet_id}, "
            f"got {quote.use_pay_out_method.id}"
        )

    def assert_settled_quote_consistency(self, quote: Quote) -> None:
        monetary.assert_equal(
            actual=quote.amount_in_gross,
            expected=quote.amount_in,
            context="quote amountInGross vs amountIn",
        )
        monetary.assert_equal(
            actual=quote.amount_due,
            expected=Decimal("0"),
            context="quote amountDue after settlement",
        )
        monetary.assert_equal(
            actual=quote.amount_in_net,
            expected=quote.amount_in,
            context="quote amountInNet vs amountIn",
        )
        monetary.assert_equal(
            actual=quote.fees.value.service,
            expected=quote.fee,
            context="quote fees.value.service vs fee",
        )
        monetary.assert_equal(
            actual=quote.processing_fee,
            expected=Decimal("0"),
            context="quote processingFee",
        )
        monetary.assert_equal(
            actual=quote.net_price,
            expected=quote.price,
            context="quote netPrice vs price",
        )
        monetary.assert_equal(
            actual=quote.gross_price,
            expected=quote.price,
            context="quote grossPrice vs price",
        )

    def assert_quote_settled(self, quote: Quote) -> None:
        assert quote.quote_status == QuoteStatus.PAYMENT_OUT_PROCESSED, (
            f"quoteStatus: expected {QuoteStatus.PAYMENT_OUT_PROCESSED}, got {quote.quote_status}"
        )
        assert quote.payment_status == PaymentStatus.SUCCESS, (
            f"paymentStatus: expected {PaymentStatus.SUCCESS}, got {quote.payment_status}"
        )

    def assert_wallet_count_unchanged(
        self,
        *,
        wallets_before: AccountWallets,
        wallets_after: AccountWallets,
    ) -> None:
        assert len(wallets_after) == len(wallets_before), (
            f"wallet count: expected {len(wallets_before)}, got {len(wallets_after)}"
        )

    def assert_wallet_identity(
        self,
        *,
        expected_wallet: Wallet,
        actual_wallet: Wallet,
    ) -> None:
        wallet_context = f"wallet ({expected_wallet.currency.code})"
        assert actual_wallet.id == expected_wallet.id, (
            f"{wallet_context} id: expected {expected_wallet.id}, got {actual_wallet.id}"
        )
        assert actual_wallet.address == expected_wallet.address, (
            f"{wallet_context} address: expected {expected_wallet.address}, "
            f"got {actual_wallet.address}"
        )
        assert actual_wallet.status == WalletStatus.ACTIVE, (
            f"{wallet_context} status: expected {WalletStatus.ACTIVE}, got {actual_wallet.status}"
        )

    def assert_wallet_approx_fields(self, wallet: Wallet) -> None:
        wallet_context = f"wallet ({wallet.currency.code})"
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
        self.assert_quote_uses_requested_wallets(
            quote=quote,
            from_currency=from_currency,
            to_currency=to_currency,
            source_wallet_id=wallets_before.by_currency(from_currency).id,
            target_wallet_id=wallets_before.by_currency(to_currency).id,
        )
        self.assert_quote_settled(quote)
        self.assert_settled_quote_consistency(quote)
        self.assert_conversion_math(
            quote=quote,
            requested_amount_in=amount_in,
            source_currency=wallets_after.by_currency(from_currency).currency,
            target_currency=wallets_after.by_currency(to_currency).currency,
        )
        self.assert_wallet_count_unchanged(
            wallets_before=wallets_before,
            wallets_after=wallets_after,
        )
        self.assert_wallet_deltas(
            quote=quote,
            wallets_before=wallets_before,
            wallets_after=wallets_after,
            from_currency=from_currency,
            to_currency=to_currency,
        )
        for currency in Currency:
            wallet_before = wallets_before.by_currency(currency)
            wallet_after = wallets_after.by_currency(currency)
            self.assert_wallet_identity(
                expected_wallet=wallet_before,
                actual_wallet=wallet_after,
            )
            self.assert_wallet_approx_fields(wallet_before)
            self.assert_wallet_approx_fields(wallet_after)
            if currency not in (from_currency, to_currency):
                self.assert_wallets_equal(
                    expected_wallet=wallet_before,
                    actual_wallet=wallet_after,
                )
