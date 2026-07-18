from decimal import Decimal
from enum import StrEnum
from pydantic import Field
from engine.api_constants.currencies import Currency
from engine.api_models.common import ApiModel

DEFAULT_QUOTE_REFERENCE = "conversion-test"


class QuoteStatus(StrEnum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    PAYMENT_OUT_PROCESSED = "PAYMENT_OUT_PROCESSED"


class PaymentStatus(StrEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"


class PayMethod(StrEnum):
    WALLET = "wallet"


class QuoteCreateRequest(ApiModel):
    from_: Currency = Field(alias="from")
    to: Currency
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
