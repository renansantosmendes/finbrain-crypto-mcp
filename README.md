# FinBrain Crypto MCP

![Python](https://img.shields.io/badge/Python-3-3776AB?logo=python&logoColor=white) ![FastAPI](https://img.shields.io/badge/FastAPI-0.139.2-009688?logo=fastapi&logoColor=white) ![uvicorn](https://img.shields.io/badge/uvicorn-0.51.0-499848) ![Langfuse](https://img.shields.io/badge/Langfuse-4.14.1-000000) ![pytest](https://img.shields.io/badge/pytest-8.4.1-0A9EDC?logo=pytest&logoColor=white) ![pandas](https://img.shields.io/badge/pandas-2.3.1-150458?logo=pandas&logoColor=white) ![Vercel](https://img.shields.io/badge/Vercel-deploy-000000?logo=vercel&logoColor=white) ![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-CI-2088FF?logo=githubactions&logoColor=white)

An **MCP (Model Context Protocol)** server that exposes the FinBrain
cryptocurrency tools: current price, OHLCV candles, order book and the list of
supported exchanges. Market data is read through
[`ccxt`](https://github.com/ccxt/ccxt), which supports many exchanges.

It was split out of `finbrain-mcp` because the `ccxt` dependency (with
`uvloop`, `aiohttp` and others) does not fit in the Vercel deployment.

## Contents

- [Overview](#overview)
- [Tools](#tools)
- [Authentication](#authentication)
- [API documentation](#api-documentation-swagger)
- [Environment variables](#environment-variables)
- [Running locally](#running-locally)
- [Testing](#testing)
- [Deployment](#deployment)
- [Repository layout](#repository-layout)

## Overview

```mermaid
flowchart LR
    agent["FinBrain agent<br/>(MCP client)"]
    subgraph vercel["Vercel: finbrain-crypto-mcp"]
        app["FastAPI app<br/>api/index.py"]
        mcp["POST /mcp<br/>JSON-RPC, Streamable HTTP"]
        tools["Crypto tools<br/>skills/cripto/tools.py"]
    end
    auth["auth_service<br/>JWKS endpoint"]
    exchanges["Public exchange APIs<br/>via ccxt"]

    agent -->|"Bearer access token"| mcp
    app --> mcp --> tools
    mcp -.->|"verify token signature<br/>(only when JWKS is set)"| auth
    tools -->|"public market data"| exchanges
```

## Tools

| Tool | What it does |
|---|---|
| `get_crypto_price` | Current price (ticker), high and low, and 24h change for a pair on one exchange. |
| `get_crypto_ohlcv` | Candle history (open, high, low, close, volume). |
| `get_crypto_order_book` | Best bid and ask, spread and the levels of the order book. |
| `list_available_exchanges` | Lists the exchanges supported by `ccxt`. |

The parameters and return formats are documented in
[`skills/cripto/tools.py`](skills/cripto/tools.py).

## Authentication

Authentication works the same way as in `finbrain-server`. When
`FINBRAIN_AUTH_JWKS_URL` is set, every request to the `/mcp` endpoint must
include an RS256 access token issued by the auth_service, in the
`Authorization: Bearer <token>` header. The token is checked against the public
keys of the JWKS, including `iss`, `aud`, `typ=access` and its expiry.

```mermaid
sequenceDiagram
    participant C as Client
    participant S as crypto MCP
    participant A as auth_service

    C->>S: POST /mcp (Authorization: Bearer token)
    alt no JWKS configured
        S-->>C: run the tool (endpoint open)
    else JWKS configured
        S->>A: fetch JWKS keys
        alt auth_service unreachable
            S-->>C: 503
        else token missing or invalid
            S-->>C: 401 {code, message}
        else token valid
            S-->>C: run the tool
        end
    end
```

- No token, or an invalid token: `401` with `{"code", "message"}`.
- auth_service unreachable: `503`.
- `/health`, `/docs`, `/openapi.json` and `/redoc` do not require a token.
  `/tools` and `/mcp` do.
- Without `FINBRAIN_AUTH_JWKS_URL`, the endpoint is open.

See [`auth.py`](auth.py).

## API documentation (Swagger)

Open `/docs` (Swagger UI) to see the server description, each tool parameter
with its limits, the `/mcp` operation with JSON-RPC examples (`initialize`,
`tools/list`, `tools/call`), and the JSON catalog at `/tools`. Use the
**Authorize** button to enter the Bearer token when authentication is enabled.
The code is in [`docs_api.py`](docs_api.py).

## Environment variables

Copy [`.env.example`](.env.example) to `.env`.

| Variable | Required | Description |
|---|---|---|
| `FINBRAIN_AUTH_JWKS_URL` | No | JWKS of the auth_service (for example `https://authservice-delta.vercel.app/.well-known/jwks.json`). Enables authentication. |
| `FINBRAIN_AUTH_JWT_ISSUER` | No | Expected `iss` (default `auth-service`). |
| `FINBRAIN_AUTH_JWT_AUDIENCE` | No | Expected `aud` (default `synapse-apps`). |
| `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST` | No | Tracing of tool calls in Langfuse. |

Exchanges are accessed without API keys: only public market data is read.

## Running locally

With [uv](https://docs.astral.sh/uv/):

```bash
uv run --no-project --with-requirements requirements.txt uvicorn mcp_server:app --port 8000
```

MCP endpoint: `POST http://localhost:8000/mcp` (Streamable HTTP, JSON-RPC).

## Testing

```bash
uv run --no-project --with-requirements requirements-dev.txt python -m pytest -q
```

The tests make no network calls: `ccxt` is replaced by a fake module, and
tokens are signed with a test key, with a fake JWKS.

## Deployment

`api/index.py` exposes `app` to Vercel (see `vercel.json`). Set the environment
variables above in the Vercel project.

```mermaid
flowchart LR
    push["git push to main"] --> vercel["Vercel build<br/>requirements.txt"]
    vercel --> fn["Function api/index.py<br/>maxDuration 30 s"]
    env["Vercel environment variables<br/>FINBRAIN_AUTH_*, LANGFUSE_*"] --> fn
```

**Side effect:** every call makes requests to public exchange APIs, which are
subject to each exchange's rate limits.

## Repository layout

| Path | Purpose |
|---|---|
| `mcp_server.py` | MCP server and tool registration |
| `auth.py` | JWT verification with the auth_service JWKS |
| `docs_api.py` | Swagger/OpenAPI documentation |
| `skills/cripto/` | Crypto tools (`tools.py`) |
| `api/index.py` | Vercel entry point |
| `tests/` | Unit tests (no network) |
