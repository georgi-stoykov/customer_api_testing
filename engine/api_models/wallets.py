from decimal import Decimal
from pydantic import Field, RootModel
from engine.api_constants.currencies import Currency
from engine.api_models.common import ApiModel


class WalletCurrency(ApiModel):
    code: str
    quantity_precision: int = Field(alias="quantityPrecision")
    price_precision: int = Field(alias="pricePrecision")


class Wallet(ApiModel):
    id: int
    currency: WalletCurrency
    balance: Decimal
    available: Decimal


class AccountWallets(RootModel[list[Wallet]]):
    def by_currency(self, code: Currency) -> Wallet:
        for wallet in self.root:
            if wallet.currency.code == code:
                return wallet
        raise KeyError(f"No wallet for currency {code!r}")
