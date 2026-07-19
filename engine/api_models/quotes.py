from collections.abc import Iterator
from decimal import Decimal
from enum import StrEnum
from pydantic import Field, RootModel
from engine.api_constants.currencies import Currency
from engine.api_models.common import ApiModel

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
    # Currencies are wire-typed (str, not the Currency enum) so negative tests can send
    # invalid codes through the same model; happy-path type safety lives on the flow
    # signatures, which take Currency.
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


class AccountQuotes(RootModel[list[Quote]]):
    def by_uuid(self, uuid: str) -> Quote:
        matching_quotes = [quote for quote in self.root if quote.uuid == uuid]
        if not matching_quotes:
            raise KeyError(f"No quote with uuid {uuid!r}")
        if len(matching_quotes) > 1:
            raise ValueError(f"{len(matching_quotes)} quotes with uuid {uuid!r}, expected one")
        return matching_quotes[0]

    def __iter__(self) -> Iterator[Quote]:
        return iter(self.root)

    def __len__(self) -> int:
        return len(self.root)
