from collections.abc import Iterator
from decimal import Decimal
import allure
from engine.api_asserters.quotes import QuoteAsserter
from engine.api_constants.currencies import Currency
from engine.api_models.quotes import Quote
from engine.api_models.wallets import CustomerWallets, Wallet, WalletStatus
from engine.utils import checks, monetary


class ConversionAsserter:
    def __init__(self) -> None:
        self._quote_asserter = QuoteAsserter()

    @staticmethod
    def _paired_wallets(
        wallets_before: CustomerWallets,
        wallets_after: CustomerWallets,
    ) -> Iterator[tuple[Wallet, Wallet]]:
        for wallet_before in wallets_before:
            yield wallet_before, wallets_after.by_id(wallet_before.id)

    @allure.step("Source/target wallet balance+available move by exactly amountIn/amountOut")
    def assert_wallet_deltas(
        self,
        *,
        amount_in: Decimal,
        amount_out: Decimal,
        source_before: Wallet,
        source_after: Wallet,
        target_before: Wallet,
        target_after: Wallet,
    ) -> None:
        monetary.assert_equal(
            actual=source_before.balance - source_after.balance,
            expected=amount_in,
            context=f"source wallet balance delta ({source_before.currency.code})",
        )
        monetary.assert_equal(
            actual=source_before.available - source_after.available,
            expected=amount_in,
            context=f"source wallet available delta ({source_before.currency.code})",
        )
        monetary.assert_equal(
            actual=target_after.balance - target_before.balance,
            expected=amount_out,
            context=f"target wallet balance delta ({target_before.currency.code})",
        )
        monetary.assert_equal(
            actual=target_after.available - target_before.available,
            expected=amount_out,
            context=f"target wallet available delta ({target_before.currency.code})",
        )

    @allure.step("Wallet count unchanged")
    def assert_wallet_count_unchanged(
        self,
        *,
        wallets_before: CustomerWallets,
        wallets_after: CustomerWallets,
    ) -> None:
        checks.assert_equal(
            actual=len(wallets_after),
            expected=len(wallets_before),
            context="wallet count",
        )

    @allure.step("Wallet keeps its id, currency, and address")
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

    @allure.step("Wallet stays ACTIVE")
    def assert_wallet_active(self, wallet: Wallet) -> None:
        checks.assert_equal(
            actual=wallet.status,
            expected=WalletStatus.ACTIVE,
            context=f"{wallet.label} status",
        )

    @allure.step("approxBalance/approxAvailable mirror balance/available")
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

    @allure.step("Uninvolved wallet balances untouched")
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

    @allure.step("Wallet is drained to exactly zero")
    def assert_wallet_drained(self, wallet: Wallet) -> None:
        monetary.assert_equal(
            actual=wallet.balance,
            expected=Decimal("0"),
            context=f"{wallet.label} balance",
        )
        monetary.assert_equal(
            actual=wallet.available,
            expected=Decimal("0"),
            context=f"{wallet.label} available",
        )

    @allure.step("Customer wallets are unchanged")
    def assert_wallets_unchanged(
        self,
        *,
        wallets_before: CustomerWallets,
        wallets_after: CustomerWallets,
    ) -> None:
        soft = checks.SoftAssertions()
        with soft:
            self.assert_wallet_count_unchanged(
                wallets_before=wallets_before,
                wallets_after=wallets_after,
            )
        for wallet_before, wallet_after in self._paired_wallets(wallets_before, wallets_after):
            with soft:
                self.assert_wallets_equal(
                    expected_wallet=wallet_before,
                    actual_wallet=wallet_after,
                )
        soft.assert_all()

    @allure.step("Wallet deltas equal the combined impact of all settled conversions")
    def assert_combined_conversion_deltas(
        self,
        *,
        quotes: list[Quote],
        wallets_before: CustomerWallets,
        wallets_after: CustomerWallets,
        from_currency: Currency,
        to_currency: Currency,
    ) -> None:
        self.assert_wallet_deltas(
            amount_in=sum((quote.amount_in for quote in quotes), Decimal("0")),
            amount_out=sum((quote.amount_out for quote in quotes), Decimal("0")),
            source_before=wallets_before.by_currency(from_currency),
            source_after=wallets_after.by_currency(from_currency),
            target_before=wallets_before.by_currency(to_currency),
            target_after=wallets_after.by_currency(to_currency),
        )

    @allure.step("Settled conversion: full customer impact is correct")
    def assert_settled_conversion(
        self,
        *,
        quote: Quote,
        wallets_before: CustomerWallets,
        wallets_after: CustomerWallets,
        from_currency: Currency,
        to_currency: Currency,
    ) -> None:
        source_before = wallets_before.by_currency(from_currency)
        source_after = wallets_after.by_currency(from_currency)
        target_before = wallets_before.by_currency(to_currency)
        target_after = wallets_after.by_currency(to_currency)
        soft = checks.SoftAssertions()
        with soft:
            self._quote_asserter.assert_quote_settled(quote)
        with soft:
            self.assert_wallet_count_unchanged(
                wallets_before=wallets_before,
                wallets_after=wallets_after,
            )
        with soft:
            self.assert_wallet_deltas(
                amount_in=quote.amount_in,
                amount_out=quote.amount_out,
                source_before=source_before,
                source_after=source_after,
                target_before=target_before,
                target_after=target_after,
            )
        for wallet_before, wallet_after in self._paired_wallets(wallets_before, wallets_after):
            with soft:
                self.assert_wallet_identity(
                    expected_wallet=wallet_before,
                    actual_wallet=wallet_after,
                )
            with soft:
                self.assert_wallet_active(wallet_before)
            with soft:
                self.assert_wallet_active(wallet_after)
            with soft:
                self.assert_wallet_approx_fields(wallet_before)
            with soft:
                self.assert_wallet_approx_fields(wallet_after)
            if wallet_before.currency.code not in (from_currency, to_currency):
                with soft:
                    self.assert_wallets_equal(
                        expected_wallet=wallet_before,
                        actual_wallet=wallet_after,
                    )
        soft.assert_all()
