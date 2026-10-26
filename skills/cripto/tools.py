from typing import Annotated

import ccxt
import pandas as pd
from langchain_core.tools import tool


@tool
def get_crypto_price(
    exchange_name: Annotated[str, "Lowercase ccxt exchange id, for example 'binance', 'coinbase' or 'kraken'."],
    symbol: Annotated[str, "Trading pair in BASE/QUOTE format, for example 'BTC/USDT' or 'ETH/USD'."],
) -> str:
    """Fetch the current ticker of a cryptocurrency pair on one exchange.

    Returns the last price, the 24-hour high and low, the 24-hour percentage
    change and the 24-hour base volume. Use it for "what is the price of X",
    not for history (see get_crypto_ohlcv).

    Parameters
    ----------
    exchange_name : str
        Lowercase ccxt exchange id.
    symbol : str
        Trading pair in BASE/QUOTE format.

    Returns
    -------
    str
        Human-readable summary of the ticker, in Portuguese. On failure, a
        message starting with "Erro ao buscar" that carries the error.

    Example
    -------
    >>> get_crypto_price.invoke({"exchange_name": "binance", "symbol": "BTC/USDT"})  # doctest: +SKIP
    'BTC/USDT na binance:\\n- Último preço: ...'
    """
    try:
        exchange = getattr(ccxt, exchange_name)()
        ticker = exchange.fetch_ticker(symbol)
    except Exception as e:
        return f"Erro ao buscar {symbol} em {exchange_name}: {e}"

    return (
        f"{symbol} na {exchange_name}:\n"
        f"- Último preço: {ticker['last']}\n"
        f"- Máxima 24h: {ticker['high']}\n"
        f"- Mínima 24h: {ticker['low']}\n"
        f"- Variação 24h: {ticker['percentage']:.2f}%\n"
        f"- Volume 24h: {ticker['baseVolume']}"
    )


@tool
def get_crypto_ohlcv(
    exchange_name: Annotated[str, "Lowercase ccxt exchange id, for example 'binance'."],
    symbol: Annotated[str, "Trading pair in BASE/QUOTE format, for example 'BTC/USDT'."],
    timeframe: Annotated[str, "Candle interval, for example '1m', '1h', '1d' or '1w'."] = "1d",
    limit: Annotated[int, "Number of most recent candles to return."] = 10,
) -> str:
    """Fetch the OHLCV candle history of a cryptocurrency pair.

    Each row holds the candle timestamp (UTC), open, high, low, close and
    volume. Use it for price history and trends.

    Parameters
    ----------
    exchange_name : str
        Lowercase ccxt exchange id.
    symbol : str
        Trading pair in BASE/QUOTE format.
    timeframe : str
        Candle interval.
    limit : int
        Number of most recent candles.

    Returns
    -------
    str
        Table of the candles as text. On failure, a message starting with
        "Erro ao buscar OHLCV" that carries the error.

    Example
    -------
    >>> get_crypto_ohlcv.invoke({"exchange_name": "binance", "symbol": "BTC/USDT", "limit": 3})  # doctest: +SKIP
    """
    try:
        exchange = getattr(ccxt, exchange_name)()
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    except Exception as e:
        return f"Erro ao buscar OHLCV de {symbol} em {exchange_name}: {e}"

    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    return df.to_string(index=False)


@tool
def get_crypto_order_book(
    exchange_name: Annotated[str, "Lowercase ccxt exchange id, for example 'binance'."],
    symbol: Annotated[str, "Trading pair in BASE/QUOTE format, for example 'BTC/USDT'."],
    limit: Annotated[int, "Number of price levels to return on each side of the book."] = 5,
) -> str:
    """Fetch the order book of a cryptocurrency pair.

    Reports the best bid (highest buy offer), the best ask (lowest sell offer),
    their spread, and the top price levels on each side. Use it for liquidity
    and spread questions.

    Parameters
    ----------
    exchange_name : str
        Lowercase ccxt exchange id.
    symbol : str
        Trading pair in BASE/QUOTE format.
    limit : int
        Number of price levels per side.

    Returns
    -------
    str
        Summary of the order book, in Portuguese. On failure, a message
        starting with "Erro ao buscar order book" that carries the error.

    Example
    -------
    >>> get_crypto_order_book.invoke({"exchange_name": "binance", "symbol": "BTC/USDT"})  # doctest: +SKIP
    """
    try:
        exchange = getattr(ccxt, exchange_name)()
        order_book = exchange.fetch_order_book(symbol, limit=limit)
    except Exception as e:
        return f"Erro ao buscar order book de {symbol} em {exchange_name}: {e}"

    melhor_compra = order_book["bids"][0][0] if order_book["bids"] else None
    melhor_venda = order_book["asks"][0][0] if order_book["asks"] else None
    spread = (melhor_venda - melhor_compra) if (melhor_compra and melhor_venda) else None

    return (
        f"Order book de {symbol} na {exchange_name}:\n"
        f"- Melhor preço de compra (bid): {melhor_compra}\n"
        f"- Melhor preço de venda (ask): {melhor_venda}\n"
        f"- Spread: {spread}\n"
        f"- Top {limit} bids: {order_book['bids']}\n"
        f"- Top {limit} asks: {order_book['asks']}"
    )


@tool
def list_available_exchanges() -> str:
    """List the cryptocurrency exchanges supported by the ccxt library.

    Use it to find valid values for exchange_name before calling the other
    crypto tools. Takes no arguments.

    Returns
    -------
    str
        Comma-separated list of ccxt exchange ids.
    """
    return ", ".join(ccxt.exchanges)
