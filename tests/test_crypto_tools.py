"""Tests for the cryptocurrency tools, with the ccxt exchanges mocked.

No exchange is contacted: ``skills.cripto.tools.ccxt`` is replaced by a fake
module whose exchanges return fixed market data.
"""

from types import SimpleNamespace

import pytest

from skills.cripto import tools


class FakeExchange:
    def fetch_ticker(self, symbol):
        return {
            "last": 100.0,
            "high": 110.0,
            "low": 90.0,
            "percentage": 1.5,
            "baseVolume": 12.0,
        }

    def fetch_ohlcv(self, symbol, timeframe, limit):
        return [[1700000000000, 1.0, 2.0, 0.5, 1.5, 10.0]]

    def fetch_order_book(self, symbol, limit):
        return {"bids": [[99.0, 1.0]], "asks": [[101.0, 2.0]]}


@pytest.fixture
def fake_ccxt(monkeypatch):
    module = SimpleNamespace(binance=FakeExchange, exchanges=["binance", "kraken"])
    monkeypatch.setattr(tools, "ccxt", module)
    return module


def test_price_reports_last_price_and_24h_variation(fake_ccxt):
    result = tools.get_crypto_price.invoke({"exchange_name": "binance", "symbol": "BTC/USDT"})
    assert "BTC/USDT na binance" in result
    assert "Último preço: 100.0" in result
    assert "Variação 24h: 1.50%" in result


def test_price_reports_an_error_for_an_unknown_exchange(fake_ccxt):
    result = tools.get_crypto_price.invoke({"exchange_name": "nope", "symbol": "BTC/USDT"})
    assert result.startswith("Erro ao buscar BTC/USDT em nope")


def test_ohlcv_lists_candles_with_readable_dates(fake_ccxt):
    result = tools.get_crypto_ohlcv.invoke({"exchange_name": "binance", "symbol": "BTC/USDT"})
    assert "2023-11-14" in result
    assert "close" in result


def test_order_book_reports_best_prices_and_spread(fake_ccxt):
    result = tools.get_crypto_order_book.invoke({"exchange_name": "binance", "symbol": "BTC/USDT"})
    assert "Melhor preço de compra (bid): 99.0" in result
    assert "Melhor preço de venda (ask): 101.0" in result
    assert "Spread: 2.0" in result


def test_available_exchanges_come_from_ccxt(fake_ccxt):
    result = tools.list_available_exchanges.invoke({})
    assert result == "binance, kraken"
