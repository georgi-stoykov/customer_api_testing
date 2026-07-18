from decimal import Decimal
from enum import StrEnum
from pydantic import Field, RootModel
from engine.api_constants.currencies import Currency
from engine.api_models.common import ApiModel


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
    status: WalletStatus


class AccountWallets(RootModel[list[Wallet]]):
    def by_currency(self, code: Currency) -> Wallet:
        matching_wallets = [wallet for wallet in self.root if wallet.currency.code == code]
        if not matching_wallets:
            raise KeyError(f"No wallet for currency {code!r}")
        if len(matching_wallets) > 1:
            raise ValueError(f"{len(matching_wallets)} wallets for currency {code!r}, expected one")
        return matching_wallets[0]

    def __len__(self) -> int:
        return len(self.root)
