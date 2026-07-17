from engine.constants.currencies import Currency
from engine.flows import convert


def test_eth_to_trx_settles_with_exact_deltas(api):
    before = api.wallet.list()
    eth_before = before.by_currency(Currency.ETH).balance
    trx_before = before.by_currency(Currency.TRX).balance

    quote = convert(
        api,
        from_currency=Currency.ETH,
        to_currency=Currency.TRX,
        amount_in="1",
    )

    after = api.wallet.list()
    eth_after = after.by_currency(Currency.ETH).balance
    trx_after = after.by_currency(Currency.TRX).balance

    assert eth_before - eth_after == quote.amount_in
    assert trx_after - trx_before == quote.amount_out
