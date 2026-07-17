from decimal import Decimal

from pydantic import RootModel

from ...constants.currencies import Currency
from .common import ApiModel


class WalletCurrency(ApiModel):
    code: str


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
