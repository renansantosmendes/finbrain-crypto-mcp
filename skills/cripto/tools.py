import ccxt
import pandas as pd
from langchain_core.tools import tool


@tool
def get_crypto_price(exchange_name: str, symbol: str) -> str:
    """Busca o preço atual (ticker) de uma criptomoeda em uma exchange específica.

    Args:
        exchange_name: nome da exchange em minúsculas (ex: "binance", "coinbase", "kraken").
        symbol: par de negociação no formato "BASE/QUOTE" (ex: "BTC/USDT", "ETH/USD").
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
def get_crypto_ohlcv(exchange_name: str, symbol: str, timeframe: str = "1d", limit: int = 10) -> str:
    """Busca o histórico de candles (OHLCV) de uma criptomoeda.

    Args:
        exchange_name: nome da exchange (ex: "binance").
        symbol: par de negociação (ex: "BTC/USDT").
        timeframe: intervalo do candle. Valores comuns: "1m", "1h", "1d", "1w".
        limit: quantidade de candles mais recentes a retornar.
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
def get_crypto_order_book(exchange_name: str, symbol: str, limit: int = 5) -> str:
    """Busca o livro de ofertas (order book) de uma criptomoeda: melhores preços de compra e venda.

    Args:
        exchange_name: nome da exchange (ex: "binance").
        symbol: par de negociação (ex: "BTC/USDT").
        limit: quantidade de níveis de preço a retornar de cada lado.
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
    """Lista as exchanges de criptomoedas suportadas pela biblioteca ccxt."""
    return ", ".join(ccxt.exchanges)