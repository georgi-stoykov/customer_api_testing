from decimal import Decimal
import allure
from engine.api_constants.currencies import Currency
from engine.api_constants.fees import CONVERSION_FEE_RATE
from engine.api_models.quotes import PaymentStatus, Quote, QuoteStatus
from engine.api_models.wallets import WalletCurrency
from engine.utils import checks, monetary


class QuoteAsserter:
    @allure.step("Fee is amountIn x the conversion fee rate")
    def assert_fee(self, quote: Quote) -> None:
        # Exact and unrounded: the API reports the fee at full precision, never quantized to
        # the source quantityPrecision (probed with an amountIn sitting exactly at
        # quantityPrecision - the fee came back at 12 dp).
        monetary.assert_equal(
            actual=quote.fee,
            expected=quote.amount_in * CONVERSION_FEE_RATE,
            context=f"fee = amountIn x {CONVERSION_FEE_RATE} ({quote.from_})",
        )

    @allure.step("amountOut is (amountIn - fee) x price")
    def assert_amount_out(
        self,
        *,
        quote: Quote,
        source_currency: WalletCurrency,
        target_currency: WalletCurrency,
    ) -> None:
        net_amount_in = quote.amount_in - quote.fee
        monetary.assert_equal_with_tolerance(
            actual=quote.amount_out,
            expected=net_amount_in * quote.price,
            tolerance=self._amount_out_tolerance(
                net_amount_in=net_amount_in,
                source_currency=source_currency,
                target_currency=target_currency,
            ),
            context=f"amountOut = (amountIn - fee) x price ({target_currency.code})",
        )

    @staticmethod
    def _amount_out_tolerance(
        *,
        net_amount_in: Decimal,
        source_currency: WalletCurrency,
        target_currency: WalletCurrency,
    ) -> Decimal:
        # price and amountOut are each rounded independently off a full-precision internal rate
        # the API never exposes, so (amountIn - fee) x price cannot equal amountOut exactly.
        # Two roundings, two error terms:
        #   price     - up to half a step at pricePrecision, amplified by the amount it multiplies
        #   amountOut - up to half a step at the target's quantityPrecision, absolute
        # Which side's pricePrecision bounds a pair-level rate is unverifiable while every
        # simulator currency uses 8 dp; the coarser side gives the larger error, so the bound
        # holds whichever side the API actually rounds to.
        price_precision = min(source_currency.price_precision, target_currency.price_precision)
        price_error = net_amount_in * monetary.compute_max_rounding_error(price_precision)
        amount_out_error = monetary.compute_max_rounding_error(target_currency.quantity_precision)
        return price_error + amount_out_error

    @allure.step("Quote echoes the requested pair, amount, and wallet ids")
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

    @allure.step("Settled quote's reported numbers are self-consistent")
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

    @allure.step("Quote reached settled statuses")
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

    @allure.step("Quote is pending acceptance")
    def assert_quote_pending(self, quote: Quote) -> None:
        checks.assert_equal(
            actual=quote.quote_status,
            expected=QuoteStatus.PENDING,
            context="quoteStatus",
        )
        checks.assert_equal(
            actual=quote.payment_status,
            expected=PaymentStatus.PENDING,
            context="paymentStatus",
        )

    @allure.step("Quote is accepted and processing")
    def assert_quote_accepted(self, quote: Quote) -> None:
        checks.assert_equal(
            actual=quote.quote_status,
            expected=QuoteStatus.ACCEPTED,
            context="quoteStatus",
        )
        checks.assert_equal(
            actual=quote.payment_status,
            expected=PaymentStatus.PROCESSING,
            context="paymentStatus",
        )

    @allure.step("Quote is expired")
    def assert_quote_expired(self, quote: Quote) -> None:
        checks.assert_equal(
            actual=quote.quote_status,
            expected=QuoteStatus.EXPIRED,
            context="quoteStatus",
        )
        checks.assert_equal(
            actual=quote.payment_status,
            expected=PaymentStatus.EXPIRED,
            context="paymentStatus",
        )

    @allure.step("Settled quote: statuses, self-consistency, and amount math are correct")
    def assert_settled_quote(
        self,
        *,
        quote: Quote,
        source_currency: WalletCurrency,
        target_currency: WalletCurrency,
    ) -> None:
        soft = checks.SoftAssertions()
        with soft:
            self.assert_quote_settled(quote)
        with soft:
            self.assert_settled_quote_consistency(quote)
        with soft:
            self.assert_fee(quote)
        with soft:
            self.assert_amount_out(
                quote=quote,
                source_currency=source_currency,
                target_currency=target_currency,
            )
        soft.assert_all()

    @allure.step("Quote amountIn is the requested amount rounded to the source quantityPrecision")
    def assert_amount_in_rounding(
        self,
        *,
        quote: Quote,
        requested_amount_in: Decimal,
        source_currency: WalletCurrency,
    ) -> None:
        expected_amount_in = monetary.round_half_up(
            requested_amount_in,
            source_currency.quantity_precision,
        )
        monetary.assert_equal(
            actual=quote.amount_in,
            expected=expected_amount_in,
            context=f"quote amountIn rounded to {source_currency.code} quantityPrecision",
        )
