# FinBrain Crypto MCP

Servidor **MCP (Model Context Protocol)** que expõe as ferramentas de criptomoedas
do FinBrain: preço, candles (OHLCV), order book e lista de exchanges, via
[`ccxt`](https://github.com/ccxt/ccxt) em múltiplas exchanges.

Foi separado do `finbrain-mcp` porque a dependência `ccxt` (com `uvloop`,
`aiohttp` e outras) não cabe no deploy do Vercel.

## Ferramentas

| Tool | O que faz |
|---|---|
| `get_crypto_price` | Preço atual (ticker), máxima/mínima e variação 24h de um par em uma exchange. |
| `get_crypto_ohlcv` | Histórico de candles (abertura, máxima, mínima, fechamento, volume). |
| `get_crypto_order_book` | Melhores preços de compra e venda, spread e níveis do livro de ofertas. |
| `list_available_exchanges` | Lista as exchanges suportadas pelo `ccxt`. |

Os parâmetros e formatos de retorno estão em [`skills/cripto/tools.py`](skills/cripto/tools.py).

## Autenticação

Igual ao `finbrain-server`: quando `FINBRAIN_AUTH_JWKS_URL` está definida, toda
requisição ao endpoint `/mcp` precisa de um access token RS256 emitido pelo
auth_service, no header `Authorization: Bearer <token>`. O token é verificado
pelas chaves públicas do JWKS, com `iss`, `aud`, `typ=access` e expiração.

- Sem token ou com token inválido: `401` com `{"code", "message"}`.
- auth_service inacessível: `503`.
- `/health`, `/docs`, `/openapi.json` e `/redoc` não exigem token. `/tools` e `/mcp` exigem.
- Sem `FINBRAIN_AUTH_JWKS_URL`, o endpoint fica aberto.

Ver [`auth.py`](auth.py).

## Documentação (Swagger)

Abra `/docs` (Swagger UI) para ver, em inglês, a descrição do servidor, cada
parâmetro da ferramenta com seus limites, a operação `/mcp` com exemplos
JSON-RPC (`initialize`, `tools/list`, `tools/call`) e o catálogo JSON em `/tools`.
Use o botão **Authorize** para informar o Bearer token quando a autenticação estiver ligada.
O código fica em [`docs_api.py`](docs_api.py).

## Variáveis de ambiente

Copie [`.env.example`](.env.example) para `.env`.

| Variável | Obrigatória | Descrição |
|---|---|---|
| `FINBRAIN_AUTH_JWKS_URL` | Não | JWKS do auth_service (ex.: `https://authservice-delta.vercel.app/.well-known/jwks.json`). Liga a autenticação. |
| `FINBRAIN_AUTH_JWT_ISSUER` | Não | `iss` esperado (padrão `auth-service`). |
| `FINBRAIN_AUTH_JWT_AUDIENCE` | Não | `aud` esperado (padrão `synapse-apps`). |
| `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST` | Não | Tracing das chamadas das tools no Langfuse. |

As exchanges são acessadas sem chave de API: só dados públicos de mercado são lidos.

## Como executar

Com [uv](https://docs.astral.sh/uv/):

```bash
uv run --no-project --with-requirements requirements.txt uvicorn mcp_server:app --port 8000
```

Endpoint MCP: `POST http://localhost:8000/mcp` (Streamable HTTP, JSON-RPC).

## Testes

```bash
uv run --no-project --with-requirements requirements-dev.txt python -m pytest -q
```

Os testes não fazem chamadas de rede: o `ccxt` é substituído por um módulo falso,
e os tokens são assinados com uma chave de teste, com o JWKS também falso.

## Deploy

`api/index.py` expõe `app` para o Vercel (`vercel.json`). Configure as variáveis
de ambiente acima no projeto.

**Efeito colateral:** cada chamada faz requisições às exchanges públicas, sujeitas
aos limites de taxa de cada uma.
