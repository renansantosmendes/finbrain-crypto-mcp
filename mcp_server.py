"""MCP server exposing FinBrain's cryptocurrency tools (prices, candles, order books).

The endpoint requires an auth_service access token when FINBRAIN_AUTH_JWKS_URL
is set; see auth.py.
"""

import functools
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from langfuse import get_client, observe
from mcp.server.mcpserver import MCPServer

from auth import BearerAuthMiddleware, build_verifier_from_env
from docs_api import ToolSpec, build_openapi_schema, tool_catalog
from skills.cripto.tools import (
    get_crypto_ohlcv,
    get_crypto_order_book,
    get_crypto_price,
    list_available_exchanges,
)

SERVER_TITLE = "FinBrain Crypto MCP"
SERVER_VERSION = "0.1.0"
SERVER_DESCRIPTION = """\
MCP server that exposes FinBrain's **cryptocurrency tools**, backed by the
[ccxt](https://github.com/ccxt/ccxt) library and public market data from
many exchanges.

## Tools

- `get_crypto_price`: last price, 24-hour range, change and volume of a pair.
- `get_crypto_ohlcv`: candle history (open, high, low, close, volume).
- `get_crypto_order_book`: best bid and ask, spread and top price levels.
- `list_available_exchanges`: exchange ids accepted by the other tools.

Pairs use the `BASE/QUOTE` format, for example `BTC/USDT`. Exchanges are
queried without API keys, so only public data is returned. Exchange rate
limits apply.

## Authentication

With `FINBRAIN_AUTH_JWKS_URL` set, the server requires an access token issued
by the FinBrain auth service. Click **Authorize** and paste the token. The
documentation pages and `/health` are always public.

## Reading this page

- The `/tools` route lists every tool with its JSON Schema.
- The `/mcp` operation shows the JSON-RPC lifecycle with examples.
"""

mcp = MCPServer("finbrain-crypto")

LANGCHAIN_TOOLS = [
    get_crypto_price,
    get_crypto_ohlcv,
    get_crypto_order_book,
    list_available_exchanges,
]


def _with_tracing(func, name: str):
    """Wrap a tool function so each call is traced as a Langfuse tool observation.

    Parameters
    ----------
    func : Callable
        Tool function to wrap.
    name : str
        Name the tool appears with in Langfuse.

    Returns
    -------
    Callable
        Function that runs ``func`` and flushes the Langfuse client afterwards.
    """
    traced_func = observe(name=name, as_type="tool")(func)

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return traced_func(*args, **kwargs)
        finally:
            get_client().flush()

    return wrapper


for langchain_tool in LANGCHAIN_TOOLS:
    mcp.tool(name=langchain_tool.name)(_with_tracing(langchain_tool.func, langchain_tool.name))

mcp_asgi_app = mcp.streamable_http_app(host="0.0.0.0", stateless_http=True)


async def _lifespan(app: FastAPI):
    """Run the MCP session manager for the life of the application.

    Parameters
    ----------
    app : FastAPI
        Application the session manager belongs to.

    Yields
    ------
    None
    """
    async with mcp.session_manager.run():
        yield


fastapi_app = FastAPI(
    title=SERVER_TITLE,
    version=SERVER_VERSION,
    description=SERVER_DESCRIPTION,
    lifespan=_lifespan,
)


@fastapi_app.get("/health", tags=["Status"], summary="Liveness check")
def health() -> dict[str, str]:
    """Report that the server is running. Does not require an access token.

    Returns
    -------
    dict[str, str]
        ``{"status": "ok"}`` while the server accepts requests.
    """
    return {"status": "ok"}


@fastapi_app.get(
    "/tools",
    tags=["MCP"],
    summary="List the tools with their input schemas",
    response_model=list[ToolSpec],
    description=(
        "Plain JSON catalog of every tool the MCP server exposes, with the "
        "JSON Schema of its arguments. The same information is returned by "
        "`tools/list` on the `/mcp` endpoint."
    ),
)
def list_tools() -> list[ToolSpec]:
    """Describe every tool registered in the server.

    Returns
    -------
    list[ToolSpec]
        One entry per tool in ``LANGCHAIN_TOOLS``.
    """
    return tool_catalog(LANGCHAIN_TOOLS)


def _openapi_schema() -> dict:
    """Build the OpenAPI document once and keep it for later requests.

    Returns
    -------
    dict
        OpenAPI document served at ``/openapi.json`` and shown at ``/docs``.
    """
    if fastapi_app.openapi_schema is None:
        fastapi_app.openapi_schema = build_openapi_schema(
            fastapi_app,
            title=SERVER_TITLE,
            version=SERVER_VERSION,
            description=SERVER_DESCRIPTION,
        )
    return fastapi_app.openapi_schema


fastapi_app.openapi = _openapi_schema


fastapi_app.mount("/", mcp_asgi_app)

app = BearerAuthMiddleware(fastapi_app, build_verifier_from_env())

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
