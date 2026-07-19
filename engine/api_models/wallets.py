from decimal import Decimal
from enum import StrEnum
from pydantic import Field
from engine.api_constants.currencies import Currency
from engine.api_models.common import ApiModel, RootList


class WalletStatus(StrEnum):
    ACTIVE = "ACTIVE"


class WalletCurrency(ApiModel):
    code: str
    quantity_precision: int = Field(alias="quantityPrecision")
    price_precision: int = Field(alias="pricePrecision")


class Wallet(ApiModel):
    id: int
    currency: WalletCurrency
    address: str
    balance: Decimal
    available: Decimal
    approx_balance: Decimal = Field(alias="approxBalance")
    approx_available: Decimal = Field(alias="approxAvailable")
    status: str

    @property
    def label(self) -> str:
        return f"wallet ({self.currency.code})"


class CustomerWallets(RootList[Wallet]):
    def by_currency(self, code: Currency) -> Wallet:
        return self._single(
            lambda wallet: wallet.currency.code == code,
            description=f"wallet for currency {code!r}",
        )

    def by_id(self, wallet_id: int) -> Wallet:
        return self._single(
            lambda wallet: wallet.id == wallet_id,
            description=f"wallet with id {wallet_id!r}",
        )
