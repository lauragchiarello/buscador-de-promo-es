# Buscador de Promoções

Compara preços de eletrônicos em lojas brasileiras. Você digita o que quer
(ex.: `notebook 32gb ram i7 13th`), o app entende as especificações, busca nas
lojas em paralelo, **descarta o que não bate** e mostra o mais barato primeiro.

| Fase | Situação |
|---|---|
| 1. Design system, parser, Mercado Livre + KaBuM!, busca ponta a ponta | ✅ pronta |
| 2. Fast Shop, Terabyte, Amazon, Shopee | ✅ pronta (Pichau fora: bloqueia acesso automático) |
| 3. Gráfico de histórico, monitoramento e alertas | próxima (o histórico já é gravado) |

---

## Como rodar

### Opção A — Docker (um comando)

```bash
cp .env.example .env      # opcional: preencha as chaves que tiver
docker compose up --build
```

- App: http://localhost:5173
- API e documentação: http://localhost:8010/docs
- Padrão visual (design system): http://localhost:5173/#ui

O Compose sobe PostgreSQL, backend (FastAPI) e frontend (Vite). As migrações do banco rodam sozinhas.

### Opção B — Local (sem Docker)

Backend (Python 3.12+):

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Linux/Mac: source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8010
```

Sem `DATABASE_URL`, o backend usa SQLite em `backend/data/app.db`.

Frontend (Node 20+):

```bash
cd frontend
npm install
npm run dev
```

### Usando um banco externo (ex.: Supabase)

Defina `DATABASE_URL` no `.env`. **No Supabase, use a string do "Session pooler"**
(host `aws-0-<região>.pooler.supabase.com`), que funciona por IPv4. A conexão direta
(`db.<projeto>.supabase.co`) é só IPv6 e não funciona dentro do Docker.
Sem `DATABASE_URL`, o Docker usa o PostgreSQL próprio e o modo local usa SQLite.

### Testes

```bash
cd backend
pytest              # ou: docker compose exec backend pytest
```

São mais de 100 testes. O parser é testado com títulos reais de anúncios, e os adaptadores usam
HTML/JSON salvos em `backend/tests/fixtures/`, então nada depende da internet.

---

## Como funciona

```
React (Vite) ──EventSource──▶ FastAPI /api/search/stream
                                 ├─ parser: texto → specs ({ram_gb: 32, cpu_line: "i7", cpu_generation: 13})
                                 ├─ orquestrador: todas as lojas em paralelo, timeout por loja
                                 │     └─ cada loja que responde já é enviada para a tela
                                 ├─ matcher: extrai specs de cada título, filtra e dá score
                                 ├─ cache de 30 min por loja + busca
                                 └─ histórico: cada coleta vira um snapshot de preço no banco
```

- **Filtro de compatibilidade** (`backend/app/parsing/`):
  - Especificação diferente da pedida → o anúncio é descartado. Exemplos: 16GB quando você pediu 32GB, i5, i7 de 12ª.
  - Especificação ausente no título → o anúncio aparece com score menor e com o motivo ("RAM não informada no título").
  - Acessórios e peças (capa, carregador, "tela para notebook") são descartados.
- **Uma loja nunca derruba a busca.** Erro, bloqueio, captcha ou timeout viram o status
  "indisponível no momento" daquela loja, e o log mostra o motivo.
- **Acesso às lojas** (`backend/app/adapters/http_policy.py`):
  - respeita o robots.txt (com um leitor próprio, que entende curingas);
  - espera de 1,5 a 4 s entre requisições à mesma loja;
  - usa um User-Agent de navegador real;
  - **para** quando a loja pede captcha ou login, sem tentar contornar.

---

## Lojas: estratégia e limitações

| Loja | Como pega os dados | Limitações |
|---|---|---|
| **KaBuM!** | Página de busca `/busca/<termo>`, que traz um JSON embutido (`__NEXT_DATA__`) | O robots.txt bloqueia a paginação, então cada termo traz só a 1ª página (até 60 itens). O adaptador faz 2 variações de termo. |
| **Mercado Livre** | API oficial com OAuth (`ML_CLIENT_ID` / `ML_CLIENT_SECRET`) | Sem chave, fica como "precisa de chave". A busca do site redireciona robôs para verificação de conta, por isso não fazemos scraping. A fixture de teste segue o formato documentado da API; troque por uma resposta real quando tiver as credenciais. |
| **Fast Shop** | API pública de busca da VTEX (`/api/io/_v/api/intelligent-search/product_search`), a mesma que o site usa | Sem frete (depende do CEP). Pega o vendedor mais barato com estoque (Fast Shop ou parceiro, como a "Acer Loja Oficial"). |
| **Terabyte** | Catálogo da 1ª página de cada categoria (`/notebooks`, `/hardware/...`), guardado por 6 h | A Cloudflare costuma pedir verificação anti-robô; aí a loja aparece como indisponível e usamos o catálogo salvo, se houver. A paginação é sempre desafiada, então a cobertura é parcial (cerca de 20 a 30 produtos por categoria). |
| **Amazon** | Creators API oficial (`AMAZON_CLIENT_ID`, `AMAZON_CLIENT_SECRET`, `AMAZON_PARTNER_TAG`) | Exige conta no Associados com vendas recentes. Até 10 itens por página (buscamos 2 páginas por termo). A API não informa parcelamento nem frete. Fixture no formato da documentação. |
| **Shopee** | API de Afiliados GraphQL (`SHOPEE_APP_ID`, `SHOPEE_APP_SECRET`) | Exige aprovação no programa de afiliados. O preço "de" é estimado pelo % de desconto. Os links são de afiliado. Fixture no formato da documentação. |
| **Lomadee** (rede de afiliados) | API de afiliados (`LOMADEE_API_KEY`): `/affiliate/products?search=` traz produtos de todas as lojas parceiras | Só aparecem as lojas da rede às quais sua conta tem acesso. A documentação diz que os preços vêm em centavos, mas o exemplo oficial contradiz; confira com dados reais (`LOMADEE_PRICE_IN_CENTS`). Funciona no Render. |
| Pichau | — (não implementada) | Responde 403 com desafio da Cloudflare até na primeira página de categoria. Não contornamos. Alternativa: feed de produtos de um programa de afiliados. |

Respeitar o robots.txt não significa que a loja autoriza scraping nos termos de uso.
O projeto é para uso pessoal, em volume baixo e com cache.

---

## Site na nuvem + coletor de casa (KaBuM! no Render)

O KaBuM! bloqueia acessos vindos de servidores de nuvem. Para ele aparecer no site do
Render, um **coletor** roda no seu computador e faz essas buscas pela internet de casa:

```
site (Render) ── grava pedido ──▶ banco (Supabase) ◀── lê pedido / grava resultado ── coletor (seu PC)
```

- O resultado chega na mesma busca, alguns segundos depois das outras lojas ("via PC de casa").
- Com o coletor desligado, o site funciona normalmente e mostra "PC de casa desligado" para essas lojas.
- O coletor não abre nenhuma porta no seu computador; ele só conversa com o banco.

**Configuração (uma vez):**
1. O site e o coletor precisam usar o **mesmo banco**: coloque a mesma `DATABASE_URL` (Supabase) no Render e no `.env`.
2. No **Render → Environment**: `REMOTE_STORES` = `kabum`.
3. No seu computador, ligue o coletor com **uma** destas opções:
   - dê dois cliques em `coletor.bat` (Windows) e deixe a janela aberta; ou
   - rode `docker compose --profile coletor up -d coletor`. Ele reinicia sozinho com o Docker. No Supabase, use a string do Session pooler, porque o Docker não tem IPv6.

---

## Deploy no Render

Um único Web Service (runtime **Python 3**) entrega a API e as telas do React.

| Configuração (Settings) | Valor |
|---|---|
| Branch | `main` |
| Root Directory | *(vazio)* |
| Build Command | `bash render-build.sh` |
| Start Command | `bash render-start.sh` |
| Health Check Path | `/api/health` |

Variáveis de ambiente (Environment), todas opcionais:

- `PYTHON_VERSION` = `3.12.8`
- `DATABASE_URL`: string do "Session pooler" do Supabase. Sem ela, o app usa SQLite, que **é apagado a cada deploy ou reinício** no plano Free.
- `ML_CLIENT_ID`, `ML_CLIENT_SECRET`, `AMAZON_*`, `SHOPEE_*`: chaves das lojas.

No plano Free, o serviço "dorme" depois de 15 min sem uso. A primeira visita depois disso leva cerca de 50 s.

---

## Como adicionar uma loja nova

1. Crie `backend/app/adapters/minha_loja.py`:

   ```python
   from ..schemas import Offer, SearchQuery
   from .base import StoreAdapter, StoreError
   from .registry import register

   @register
   class MinhaLojaAdapter(StoreAdapter):
       slug = "minhaloja"
       name = "Minha Loja"
       homepage = "https://www.minhaloja.com.br"
       strategy = "Scraping da busca"

       async def search(self, query: SearchQuery) -> list[Offer]:
           # query.store_terms = ["notebook i7 13 geracao 32gb", "notebook i7 32gb"]
           resp = await self.http.get(f"{self.homepage}/busca?q=...")  # robots, rate limit e bloqueio já tratados
           return [Offer(store=self.slug, store_name=self.name, external_id=..., title=..., url=..., price_cash=...)]
   ```

   - Para APIs com chave, sobrescreva `is_configured()` e leia a chave de `self.settings`
     (adicione o campo em `app/config.py` e em `.env.example`).
   - Loja VTEX? Herde de `VtexAdapter` (veja `fastshop.py`: 5 linhas).
   - Loja que só libera páginas de categoria? Herde de `CatalogAdapter` (veja `terabyte.py`).
   - Para avisar o usuário de um problema, levante `StoreError("mensagem amigável", detail="detalhe técnico")`.
     Use `StoreBlocked` para captcha ou bloqueio.
2. Salve um HTML/JSON real em `backend/tests/fixtures/` e escreva testes como os de `tests/test_adapters.py`.
3. No frontend, inclua a loja em `STORES` no componente `StoreTag` e a cor em `tokens.css` (`--store-minhaloja`).

A loja aparece sozinha na API, nos filtros e na barra de status.

---

## Frontend: regras e como criar um componente

- Usa **só React + react-dom**. O Vite serve apenas como ferramenta de build, sem plugins:
  o JSX é compilado pelo esbuild embutido.
- Não usa nenhuma biblioteca de UI, rotas, estado, requisições, gráficos ou ícones.
- Requisições ficam em `src/services/api.js`, com `fetch` e `EventSource` nativos.
- **Todo valor visual vem de `src/styles/tokens.css`**: cores, espaços, raios, sombras, fontes, transições e larguras.

Para criar um componente base:

1. Crie `src/components/ui/MeuComponente/MeuComponente.jsx` e `MeuComponente.module.css`.
2. Documente as props com JSDoc no topo do componente (veja `Button.jsx`).
3. No CSS, use só `var(--...)` do `tokens.css`. Se faltar um valor, crie um token novo em vez de usar um número solto.
4. Não use estilo inline. Para variantes, use classes: `styles[variant]`, junto com o helper `cx()`.
5. Mostre todas as variantes em `src/pages/UiShowcasePage.jsx` (abra com `#ui`).

Componentes de negócio ficam em `src/components/features/` e usam os componentes base.
Telas ficam em `src/pages/`. A navegação é controlada por estado e pelo `#hash` da URL.

---

## Estrutura

```
backend/
  app/
    adapters/   base.py, registry.py, http_policy.py, robots.py, vtex.py, catalog_base.py,
                kabum.py, mercadolivre.py, fastshop.py, terabyte.py, amazon.py, shopee.py
    parsing/    normalize.py, specs.py, accessories.py, matcher.py
    services/   orchestrator.py, cache.py, history.py, catalog.py
    api/        routes.py
    models/     tabelas (searches, search_cache, listings, price_snapshots, watchlist, alerts)
  alembic/      migrações
  tests/        testes + fixtures
frontend/src/
  components/ui/        Button, Input, SearchBar, Select, Checkbox, Card, Badge, Spinner, Skeleton,
                        EmptyState, ErrorMessage, Modal, Tooltip, Toast, PriceTag, StoreTag, Icon
  components/features/  OfferCard, OfferList, FilterPanel, SortControl, StoreStatusBar, QuerySummary
  pages/                SearchPage, ComingSoonPage, UiShowcasePage
  hooks/                useSearch, useDebounce, useStores, useFilteredOffers
  services/api.js
  utils/                format.js, specs.js, classNames.js
  styles/               tokens.css, global.css
```
