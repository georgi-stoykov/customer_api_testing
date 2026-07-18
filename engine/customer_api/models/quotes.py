from decimal import Decimal
from enum import StrEnum
from pydantic import Field
from engine.constants.currencies import Currency
from engine.customer_api.models.common import ApiModel

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


class Quote(ApiModel):
    uuid: str
    id: int
    from_: str = Field(alias="from")
    to: str
    amount_in: Decimal = Field(alias="amountIn")
    amount_out: Decimal = Field(alias="amountOut")
    price: Decimal
    fee: Decimal
    quote_status: QuoteStatus = Field(alias="quoteStatus")
    payment_status: PaymentStatus = Field(alias="paymentStatus")
