from decimal import Decimal
from enum import StrEnum
from pydantic import Field
from engine.api_constants.currencies import Currency
from engine.api_models.common import ApiModel, RootList

DEFAULT_QUOTE_REFERENCE = "conversion-test"


class QuoteStatus(StrEnum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    PAYMENT_OUT_PROCESSED = "PAYMENT_OUT_PROCESSED"
    EXPIRED = "EXPIRED"


class PaymentStatus(StrEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    EXPIRED = "EXPIRED"


class PayMethod(StrEnum):
    WALLET = "wallet"


class QuoteCreateRequest(ApiModel):
    # Wire-typed (str, not Currency) so negative tests can send invalid codes.
    from_: str = Field(alias="from")
    to: str
    from_wallet: int = Field(alias="fromWallet")
    to_wallet: int = Field(alias="toWallet")
    amount_in: str = Field(alias="amountIn")
    use_maximum: bool = Field(default=False, alias="useMaximum")
    use_minimum: bool = Field(default=False, alias="useMinimum")
    reference: str = DEFAULT_QUOTE_REFERENCE
    pay_in_method: PayMethod = Field(default=PayMethod.WALLET, alias="payInMethod")
    pay_out_method: PayMethod = Field(default=PayMethod.WALLET, alias="payOutMethod")


class WalletRef(ApiModel):
    id: int


class QuoteFeeValues(ApiModel):
    service: Decimal


class QuoteFees(ApiModel):
    value: QuoteFeeValues


class Quote(ApiModel):
    uuid: str
    id: int
    from_: Currency = Field(alias="from")
    to: Currency
    amount_in: Decimal = Field(alias="amountIn")
    amount_in_gross: Decimal = Field(alias="amountInGross")
    amount_in_net: Decimal = Field(alias="amountInNet")
    amount_due: Decimal = Field(alias="amountDue")
    amount_out: Decimal = Field(alias="amountOut")
    price: Decimal
    net_price: Decimal = Field(alias="netPrice")
    gross_price: Decimal = Field(alias="grossPrice")
    fee: Decimal
    processing_fee: Decimal = Field(alias="processingFee")
    fees: QuoteFees
    use_pay_in_method: WalletRef = Field(alias="usePayInMethod")
    use_pay_out_method: WalletRef = Field(alias="usePayOutMethod")
    quote_status: QuoteStatus = Field(alias="quoteStatus")
    payment_status: PaymentStatus = Field(alias="paymentStatus")


class CustomerQuotes(RootList[Quote]):
    def by_uuid(self, uuid: str) -> Quote:
        return self._single(
            lambda quote: quote.uuid == uuid,
            description=f"quote with uuid {uuid!r}",
        )
