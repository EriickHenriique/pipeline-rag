# Pipeline RAG — Analista Financeiro

Pipeline de Recuperação e Geração Aumentada (RAG) para análise de relatórios financeiros brasileiros (DFPs, ITRs e Releases). Permite fazer upload de PDFs de demonstrações financeiras e consultar o conteúdo via linguagem natural, com extração automática de KPIs e citação de fontes.

---

## Visão Geral

O sistema combina:

- **Docling** para parsing estruturado de PDFs financeiros (texto, tabelas, numeração de páginas)
- **Qdrant** como banco vetorial com busca híbrida (densa + esparsa via BM25)
- **LangGraph** para orquestração de um pipeline multi-agente com ciclo de retentativa
- **FastAPI** como backend REST
- **Streamlit** como interface gráfica

---

## Arquitetura

```
┌─────────────────────────────────────────────────────────────────┐
│                         INGESTÃO                                │
│                                                                 │
│  PDF → DFPParser (Docling) → DFPChunker → EmbeddingService     │
│                                                 ↓               │
│                                          QdrantIndexer          │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      PIPELINE DE CONSULTA (LangGraph)           │
│                                                                 │
│  Pergunta → QueryAnalystAgent → RetrieverAgent                  │
│                                      ↓                          │
│             ValidatorAgent ← FinancialAnalystAgent              │
│                  ↓                                              │
│          PASS → Resposta Final                                  │
│          RETRY → FinancialAnalystAgent (até 3x)                 │
│          FAIL → Resposta com aviso                              │
└─────────────────────────────────────────────────────────────────┘
```

### Módulos

| Módulo | Responsabilidade |
|---|---|
| `ingestion/parser.py` | Converte PDF em texto estruturado por página e tabelas via Docling |
| `ingestion/chunker.py` | Divide conteúdo em chunks com header enriquecido de metadados e detecção de seção |
| `storage/embedder.py` | Gera embeddings densos (OpenAI) e esparsos (BM25/fastembed) |
| `storage/qdrant_indexer.py` | Cria coleção e indexa chunks no Qdrant com suporte a busca híbrida |
| `storage/ingest_service.py` | Orquestra o fluxo completo de ingestão (Parse → Chunk → Embed → Index) |
| `agents/query_analyst.py` | Analisa a intenção da pergunta e extrai filtros e KPIs esperados |
| `agents/retriever.py` | Busca híbrida no Qdrant com fusão RRF (dense + sparse) |
| `agents/financial_analyst.py` | Gera análise financeira estruturada a partir dos chunks recuperados |
| `agents/validator.py` | Valida confiança, fontes e consistência dos KPIs; dispara retentativa se necessário |
| `graph/builder.py` | Constrói e compila o grafo de estados LangGraph |
| `api/main.py` | Aplicação FastAPI com CORS para o Streamlit |
| `ui/streamlit_app.py` | Interface gráfica para ingestão e consulta |
| `observability/tracing.py` | Inicialização do Langfuse v4 para rastreamento de chamadas LLM |

---

## Fluxo de Ingestão

1. **Parse** — Docling extrai texto por página e tabelas do PDF
2. **Chunk** — O `DFPChunker` processa tabelas e texto separadamente. Cada chunk recebe um header enriquecido:
   ```
   [PETROBRAS | DFP 2024 1 | Seção: DRE | Página: 42]
   ```
3. **Detecção de Seção** — Regras baseadas em palavras-chave classificam automaticamente cada chunk em: `DRE`, `Balanço`, `DFC`, `DMPL`, `Notas Explicativas`, `Relatório` ou `Outros`
4. **Embed** — Embeddings densos (OpenAI `text-embedding-3-large`, 3072 dimensões) + esparsos (BM25)
5. **Index** — Upload em batches para o Qdrant com payload indexado por `nome_empresa`, `ano_fiscal`, `trimestre`, `section` e `chunk_type`

---

## Fluxo de Consulta

1. **QueryAnalystAgent** — Analisa a pergunta via LLM com saída estruturada (`QueryPlan`):
   - Intenção: `kpi_lookup`, `comparison`, `trend_analysis`, `summary`, `explanation`
   - Filtros: empresa(s), anos fiscais, trimestres, seções
   - KPIs esperados e pergunta reformulada para retrieval
2. **RetrieverAgent** — Busca híbrida no Qdrant: pré-busca densa + esparsa com fusão RRF, retorna os top-10 chunks mais relevantes
3. **FinancialAnalystAgent** — Gera `FinancialAnalysis` estruturada com resposta em português, KPIs extraídos (nome, valor, unidade, período), fontes citadas e `confidence_score`
4. **ValidatorAgent** — Verifica três critérios:
   - `confidence >= 0.4`
   - `len(sources) >= 1`
   - Nenhum KPI monetário com valor 0 suspeito
   - Em caso de falha: `RETRY` (até 3 vezes) → `FAIL` com aviso

---

## Pré-requisitos

- Python 3.13+
- [`uv`](https://docs.astral.sh/uv/) (gerenciador de pacotes)
- Conta na [OpenAI API](https://platform.openai.com/)
- Instância do [Qdrant](https://qdrant.tech/) (Cloud gratuito ou local via Docker)
- (Opcional) Conta no [Langfuse](https://langfuse.com/) para observabilidade

---

## Configuração

Crie um arquivo `.env` na raiz do projeto:

```env
# OpenAI (obrigatório)
OPENAI_API_KEY=sk-...
EMBEDDING_MODEL=text-embedding-3-large
CHAT_MODEL=gpt-4o-mini

# Qdrant (obrigatório)
QDRANT_URL=https://<seu-cluster>.cloud.qdrant.io
QDRANT_API_KEY=<sua-api-key>
QDRANT_COLLECTION=dfp-chunks

# Langfuse (opcional)
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com

# App
APP_ENV=development
LOG_LEVEL=INFO
```

### Qdrant com Docker (alternativa local)

```bash
docker run -p 6333:6333 qdrant/qdrant
```

Defina `QDRANT_URL=http://localhost:6333` e deixe `QDRANT_API_KEY` em branco.

---

## Instalação

```bash
# Clonar o repositório
git clone <url-do-repo>
cd pipeline-rag-financial-analyst

# Instalar dependências com uv
uv sync
```

---

## Iniciando o Projeto

O sistema é composto por dois serviços que devem rodar simultaneamente.

### 1. API (FastAPI)

```bash
python src/fin_pipeline/run_api.py
```

Ou diretamente com uvicorn:

```bash
uvicorn fin_pipeline.api.main:app --host 0.0.0.0 --port 8000 --reload
```

A API estará disponível em `http://localhost:8000`.
Documentação interativa: `http://localhost:8000/docs`

### 2. Interface (Streamlit)

Em outro terminal:

```bash
python src/fin_pipeline/run_ui.py
```

A UI estará disponível em `http://localhost:8501`.

---

## Endpoints da API

| Método | Endpoint | Descrição |
|---|---|---|
| `GET` | `/health` | Status da API e conectividade com o Qdrant |
| `GET` | `/documents` | Lista todos os documentos indexados |
| `POST` | `/ingest` | Upload e indexação de PDF (multipart/form-data) |
| `POST` | `/query` | Consulta em linguagem natural |

### Exemplo: Ingestão via curl

```bash
curl -X POST http://localhost:8000/ingest \
  -F "file=@relatorio.pdf" \
  -F "nome_empresa=PETROBRAS" \
  -F "cnpj=33.000.167/0001-01" \
  -F "tipo_relatorio=DFP" \
  -F "ano_fiscal=2024" \
  -F "trimestre=4"
```

### Exemplo: Consulta via curl

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Qual foi o EBITDA da Petrobras no 4T2024?", "session_id": "sess-01"}'
```

---

## Particularidades

### Busca Híbrida com RRF
O retriever combina dois vetores por chunk: denso (semântico, OpenAI) e esparso (lexical, BM25). O Qdrant usa Reciprocal Rank Fusion para unir os rankings, o que melhora a cobertura de termos financeiros específicos (siglas, números, nomes de contas).

### Chunks Enriquecidos
Cada chunk indexado contém um header com contexto completo. Isso garante que o LLM sempre saiba de qual empresa, relatório, seção e página o trecho veio — sem depender apenas dos metadados do payload.

### Detecção de Página Robusta
O chunker usa três estratégias em cascata para detectar números de página no markdown do Docling: marcadores sintéticos (`DOCLING_DOC_PAGE_BREAK`), form feed (`\x0c`) e rodapé padrão IFRS. Quando nada é encontrado, mantém o número da página da entrada nativa da API do Docling.

### Filtragem por Metadados
O `QueryAnalystAgent` extrai automaticamente filtros da pergunta do usuário. Se o usuário mencionar "Bradesco 2024 Q3", o retriever restringe a busca apenas a chunks com `nome_empresa=BRADESCO`, `ano_fiscal=2024`, `trimestre=3`.

### Ciclo de Retentativa
O `ValidatorAgent` pode sinalizar `RETRY` para o `FinancialAnalystAgent` se a análise tiver confiança baixa ou fontes insuficientes. O ciclo repete até 3 vezes antes de sinalizar `FAIL` e retornar a melhor resposta disponível com aviso.

### Suporte a Tipos de Relatório

| Tipo | Descrição |
|---|---|
| `DFP` | Demonstração Financeira Padronizada (anual) |
| `ITR` | Informações Trimestrais |
| `Release` | Comunicado de Resultados |

---

## Estrutura do Projeto

```
src/fin_pipeline/
├── agents/
│   ├── base.py              # Classe base dos agentes
│   ├── query_analyst.py     # Agente de planejamento de consulta
│   ├── retriever.py         # Agente de recuperação vetorial
│   ├── financial_analyst.py # Agente de análise financeira
│   └── validator.py         # Agente de validação com retry
├── api/
│   ├── main.py              # Criação da app FastAPI
│   ├── dependencies.py      # Dependências injetadas
│   └── routes/
│       ├── health.py
│       ├── query.py
│       ├── ingest.py
│       └── documents.py
├── graph/
│   ├── builder.py           # Compilação do grafo LangGraph
│   ├── nodes.py             # Funções de nó
│   └── edges.py             # Roteamento condicional
├── ingestion/
│   ├── parser.py            # Parser de PDF com Docling
│   └── chunker.py           # Divisão e enriquecimento de chunks
├── observability/
│   └── tracing.py           # Inicialização do Langfuse
├── schemas/
│   ├── state.py             # AgentState (TypedDict do LangGraph)
│   ├── document.py          # Chunk, DFPMetadata, DocumentSection
│   ├── query.py             # QueryPlan, RetrievedChunk
│   ├── analysis.py          # FinancialAnalysis, KPI
│   ├── validation.py        # ValidationResult
│   ├── storage.py           # EmbeddedChunk, IndexingStats
│   └── api.py               # Request/Response DTOs da API
├── storage/
│   ├── embedder.py          # Geração de embeddings densos e esparsos
│   ├── qdrant_indexer.py    # Indexação e busca no Qdrant
│   └── ingest_service.py    # Orquestrador de ingestão
├── ui/
│   └── streamlit_app.py     # Interface gráfica
├── config.py                # Configurações via pydantic-settings
├── run_api.py               # Entrypoint da API
└── run_ui.py                # Entrypoint da UI
```

---

## Tecnologias

| Tecnologia | Versão | Uso |
|---|---|---|
| Python | 3.13 | Runtime |
| FastAPI | ≥0.136 | API REST |
| Streamlit | ≥1.57 | Interface gráfica |
| LangGraph | ≥1.1 | Orquestração de agentes |
| LangChain | ≥0.3 | Abstrações LLM |
| OpenAI SDK | ≥2.33 | LLM + embeddings |
| Qdrant Client | ≥1.17 | Banco vetorial |
| fastembed | ≥0.8 | Embeddings esparsos (BM25) |
| Docling | ≥2.90 | Parsing de PDF |
| Langfuse | ≥4.5 | Observabilidade LLM |
| Loguru | ≥0.7 | Logging |
| Pydantic | — | Validação de dados |
| uv | — | Gerenciamento de pacotes |
