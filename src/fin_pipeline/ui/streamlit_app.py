import time

import httpx
import streamlit as st

# Configuração

API_BASE = "http://localhost:8000"
st.set_page_config(
    page_title="Pipeline Financeiro - RAG",
    page_icon="📊",
    layout="wide",
)

def api_get(path: str) -> dict | list | None:
    """Faz uma requisição GET para a API e retorna os dados como JSON."""
    try:
        response = httpx.get(f"{API_BASE}{path}", timeout=10)
        response.raise_for_status()
        return response.json()
    except httpx.RequestError as exc:
        st.error(f"Erro de conexão: {exc}")
        return None
    except httpx.HTTPStatusError as exc:
        st.error(f"Erro HTTP: {exc.response.status_code} - {exc.response.text}")
        return None

def api_post_json(path: str, payload: dict) -> dict | None:
    """Faz uma requisição POST para a API com um payload JSON e retorna a resposta como JSON."""
    try:
        response= httpx.post(f"{API_BASE}{path}", json=payload, timeout=120)
        response.raise_for_status()
        return response.json()
    except httpx.RequestError as exc:
        st.error(f"Erro de conexão: {exc}")
        return None
    except httpx.HTTPStatusError as exc:
        st.error(f"Erro HTTP: {exc.response.status_code} - {exc.response.text}")
        return None

def api_post_file(
        path: str,
        file_bytes: bytes,
        filename: str,
        form_data: dict,
) -> dict | None:
    """Faz uma requisição POST para a API com um arquivo e dados de formulário, e retorna a resposta como JSON."""
    try:
        response = httpx.post(
            f"{API_BASE}{path}",
            files={"file": (filename, file_bytes, "application/pdf")},
            data=form_data,
            timeout=9200,
        )
        response.raise_for_status()
        return response.json()
    except httpx.RequestError as exc:
        st.error(f"Erro de conexão: {exc}")
        return None
    except httpx.HTTPStatusError as exc:
        st.error(f"Erro HTTP: {exc.response.status_code} - {exc.response.text}")
        return None

# Navegação

st.sidebar.title("Pipeline Financeiro - RAG")
st.sidebar.caption("Relatórios de Análise Financeira")

page = st.sidebar.radio(
    "Navegação",
    ["📄 Ingestão de PDF", "💬 Consulta de Documentos"],
    index=0,
)

# Verificar saúde da API
health = api_get("/health")
if health:
    icon = "🟢" if health["status"] == "ok" else "🟡"
    st.sidebar.markdown(
        f"{icon} API `{health['status']}` | "
        f"Qdrant `{'conectado' if health['qdrant_connected'] else 'disconnected'}`"
    )

# Página 1

if page == "📄 Ingestão de PDF":
    st.title("📄 Ingestão de DFP Document")
    st.caption("Upload de um arquivo PDF e preenchimento de metadados para indexação")

    # Show already indexed documents
    with st.expander("📚 Documents indexados atualmente", expanded=False):
        docs = api_get("/documents")
        if docs:
            if len(docs) == 0:
                st.info("Nenhum documento indexado ainda.")
            else:
                for doc in docs:
                    st.markdown(
                        f"**{doc['nome_empresa']}** — "
                        f"{doc['tipo_relatorio']} {doc['ano_fiscal']} {doc['trimestre']} "
                        f"({doc['chunk_count']} chunks)"
                    )
        else:
            st.warning("Não foi possível carregar a lista de documentos.")

    st.divider()

    # Upload form
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("1. Upload do PDF")
        uploaded_file = st.file_uploader(
            "Selecione um arquivo PDF para upload",
            type=["pdf"],
            help="Tamanho máximo do arquivo: 50MB",
        )

    with col2:
        st.subheader("2. Preencher Metadados")
        nome_empresa = st.text_input(
            "Nome da Empresa *",
            placeholder="Nome da Empresa",
            help="Exemplo: Petrobras, Vale, Ambev",
        )
        cnpj = st.text_input(
            "CNPJ *",
            placeholder="33.000.167/0001-01",
            help="Formato: XX.XXX.XXX/XXXX-XX",
        )
        ticker = st.text_input(
            "Ticker (optional)",
            placeholder="ticket da empresa na bolsa, ex: PETR4",
            help="Exemplo: PETR4, VALE3, ABEV3"
        )

        col_a, col_b, col_c = st.columns(3)
        with col_a:
            tipo_relatorio = st.selectbox(
                "Tipo de Relatório *",
                ["DFP", "ITR", "Release"],
            )
        with col_b:
            ano_fiscal = st.number_input(
                "Ano Fiscal *",
                min_value=1998,
                max_value=2040,
                value=2024,
            )
        with col_c:
            trimestre = st.selectbox(
                "Trimestre *",
                ["1", "2", "3", "4"],
            )

    st.divider()

    if st.button("🚀 Ingestão do PDF", type="primary", use_container_width=True):
        if not uploaded_file:
            st.error("Por favor, faça upload de um arquivo PDF.")
        elif not nome_empresa:
            st.error("O nome da empresa é obrigatório.")
        elif not cnpj:
            st.error("O CNPJ é obrigatório.")
        else:
            with st.spinner(
                f"Processando {uploaded_file.name}... "
                "Isso pode levar alguns minutos (Docling + embedding)."
            ):
                result = api_post_file(
                    path="/ingest",
                    file_bytes=uploaded_file.read(),
                    filename=uploaded_file.name,
                    form_data={
                        "nome_empresa": nome_empresa,
                        "cnpj": cnpj,
                        "ticker": ticker or "",
                        "tipo_relatorio": tipo_relatorio,
                        "ano_fiscal": str(ano_fiscal),
                        "trimestre": trimestre,
                    },
                )

            if result and result.get("success"):
                st.success(f"✅ {result['message']}")

                # Show indexing stats
                st.subheader("📊 Estatísticas de Indexação")
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Total chunks", result["total_chunks"])
                m2.metric("Table chunks", result["table_chunks"])
                m3.metric("Text chunks", result["text_chunks"])
                m4.metric(
                    "Tempo de processamento",
                    f"{result['processing_time_ms'] / 1000:.1f}s",
                )

                st.info(
                    f"Collection: `{result['collection_name']}` — "
                    f"Documento pronto para consulta!"
                )
            elif result:
                st.error(f"❌ Ingestão falhou: {result.get('message')}")

# Página 2

elif page == "💬 Consulta de Documentos":
    st.title("💬 Buscar no Documento")
    st.caption("Faça perguntas sobre os documentos financeiros indexados e obtenha respostas baseadas no conteúdo dos PDFs.")

    # Mostrar documentos indexados
    docs = api_get("/documents")
    if docs:
        with st.sidebar.expander("📚 Documentos Indexados"):
            for doc in docs:
                st.sidebar.caption(
                    f"{doc['nome_empresa']} {doc['ano_fiscal']} "
                    f"{doc['trimestre']} ({doc['chunk_count']} chunks)"
                )

    # Query input
    question = st.text_area(
        "Sua pergunta",
        placeholder="Qual foi o Lucro do Bradesco em 2025?",
        height=100,
    )

    col1, col2 = st.columns([3, 1])
    with col2:
        session_id = st.text_input(
            "Session ID (optional)",
            value="streamlit-session",
            help="Use a unique session ID to maintain context across perguntas. Deixe em branco para usar o padrão.",
        )

    if st.button("🔍 Busca", type="primary", use_container_width=True):
        if not question.strip():
            st.error("Por favor, insira uma pergunta.")
        else:
            with st.spinner("Processando pergunta..."):
                result = api_post_json(
                    "/query",
                    {"question": question, "session_id": session_id},
                )

            if result:
                # Mostrar resposta
                st.subheader("📝 Resposta")

                # Confiança da resposta
                confidence = result["confidence"]
                if confidence >= 0.8:
                    conf_color = "🟢"
                elif confidence >= 0.5:
                    conf_color = "🟡"
                else:
                    conf_color = "🔴"

                st.markdown(result["answer"])

                col_a, col_b, col_c = st.columns(3)
                col_a.metric("Confiança", f"{confidence:.0%}")
                col_b.metric("Tempo de processamento", f"{result['processing_time_ms']}ms")
                col_c.metric("Fontes citadas", len(result["sources"]))

                if result.get("need_more_context"):
                    st.warning(
                        "⚠️ Exige mais contexto — "
                        "mais informações relevantes não foram encontradas nos documentos indexados."
                    )

                # KPI Cards
                if result["kpis"]:
                    st.subheader("📈 Indicadores extraidos")
                    cols = st.columns(min(len(result["kpis"]), 4))
                    for i, kpi in enumerate(result["kpis"]):
                        col = cols[i % 4]
                        # Formatação de valores com base na unidade
                        if kpi["unit"] == "BRL":
                            value_str = f"R$ {kpi['value']:,.0f}"
                        elif kpi["unit"] == "percent":
                            value_str = f"{kpi['value']:.1f}%"
                        else:
                            value_str = f"{kpi['value']:,.2f}"

                        col.metric(
                            label=f"{kpi['name']} ({kpi['period']})",
                            value=value_str,
                        )
                        if kpi.get("source_page"):
                            col.caption(f"Página: {kpi['source_page']}")

                #  Reasoning 
                if result.get("reasoning"):
                    with st.expander("🧠 Reasoning"):
                        st.markdown(result["reasoning"])

                # Sources
                if result["sources"]:
                    st.subheader("📚 Fontes")
                    for i, source in enumerate(result["sources"], 1):
                        st.markdown(
                            f"`{i}` **Página {source['page']}** — "
                            f"{source['section']} — "
                            f"`chunk: {source['chunk_id'][:8]}...`"
                        )
