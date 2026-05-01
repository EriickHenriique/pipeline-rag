import re
import uuid
from typing import Any

from loguru import logger

from fin_pipeline.schemas.document import Chunk, DFPMetadata, DocumentSection


TEXT_CHUNK_SIZE = 1000
TEXT_CHUNK_OVERLAP = 100
CHARS_PER_TOKEN = 4

# Marcador sintético do Docling 
PAGE_BREAK_RE = re.compile(r"#_#_DOCLING_DOC_PAGE_BREAK_\d+_(\d+)_#_#")

# Form feed é um caractere de controle que indica uma quebra de página, presente em alguns documentos como um marcador nativo de fim de página. Ele pode ser usado como uma estratégia adicional para detectar quebras de página quando os marcadores sintéticos do Docling não estão presentes ou são inconsistentes.
FORM_FEED = "\x0c"

# Rodapé comum em muitos relatórios financeiros, que pode ser usado para detectar quebras de página mesmo quando os marcadores sintéticos do Docling não estão presentes. O padrão busca por "IFRS <número>" no rodapé, onde o número é interpretado como o número da página.
FOOTER_PAGE_RE = re.compile(r"\bIFRS\s+(\d+)\s*$", re.MULTILINE)


def _extract_page_number_from_footer(text: str) -> int | None:
    """Tenta extrair o número da página a partir do rodapé do documento, utilizando uma expressão regular que busca um padrão específico (neste caso, 'IFRS <número>'). Retorna o número da página se encontrado, ou None caso contrário."""

    m = FOOTER_PAGE_RE.search(text)
    return int(m.group(1)) if m else None


def _split_by_page_breaks(text: str, start_page: int) -> list[tuple[int, str]]:
    """Divide um trecho de texto em segmentos por página, utilizando múltiplas estratégias para detectar quebras de página. As estratégias incluem a detecção de marcadores sintéticos do Docling, form feed (separador de página nativo) e rodapés do documento. Retorna uma lista de tuplas (número da página, texto do segmento), garantindo que cada segmento seja associado à página correta, mesmo em casos onde os marcadores de página não sejam consistentes ou estejam ausentes."""



    # Estratégia 1: marcadores sintéticos do Docling
    if PAGE_BREAK_RE.search(text):
        segments: list[tuple[int, str]] = []
        current_page = start_page
        remaining = text

        while True:
            match = PAGE_BREAK_RE.search(remaining)
            if not match:
                clean = PAGE_BREAK_RE.sub("", remaining).strip()
                if clean:
                    segments.append((current_page, clean))
                break
            before = remaining[: match.start()].strip()
            if before:
                segments.append((current_page, PAGE_BREAK_RE.sub("", before).strip()))
            current_page = int(match.group(1))
            remaining = remaining[match.end():]

        return segments

    # Estratégia 2: form feed (separador de página nativo) 
    if FORM_FEED in text:
        segments = []
        current_page = start_page
        raw_pages = text.split(FORM_FEED)

        for raw in raw_pages:
            clean = raw.strip()
            if not clean:
                continue

            # Tenta confirmar/corrigir o número de página pelo rodapé
            footer_page = _extract_page_number_from_footer(clean)
            if footer_page is not None:
                current_page = footer_page

            # Remove o rodapé do texto do chunk para não poluir o conteúdo
            clean_no_footer = FOOTER_PAGE_RE.sub("", clean).strip()
            if clean_no_footer:
                segments.append((current_page, clean_no_footer))

            # Próxima página será current_page + 1 se não encontrar rodapé
            if footer_page is None:
                current_page += 1

        return segments

    # Estratégia 3: rodapé do documento
    footer_positions = list(FOOTER_PAGE_RE.finditer(text))
    if footer_positions:
        segments = []
        prev_end = 0
        current_page = start_page

        for m in footer_positions:
            chunk_text = text[prev_end: m.start()].strip()
            page_num = int(m.group(1))
            if chunk_text:
                segments.append((page_num, chunk_text))
            prev_end = m.end()
            current_page = page_num + 1

        # Texto após o último rodapé
        tail = text[prev_end:].strip()
        if tail:
            segments.append((current_page, tail))

        return segments

    #Fallback: nenhum marcador encontrado, usa start_page
    clean = text.strip()
    return [(start_page, clean)] if clean else []


def detect_section(text: str) -> DocumentSection:
    """Detecta a seção do relatório financeiro a que um trecho de texto pertence, com base em palavras-chave comuns. A detecção é feita por meio de regras simples que verificam a presença de termos específicos relacionados a cada seção (Balanço, DRE, DFC, DMPL, Notas Explicativas, Relatório da Administração). Retorna a seção detectada ou DocumentSection.OUTROS se não for possível identificar."""
    
    text_upper = text.upper()

    rules = {
        DocumentSection.BALANCO: [
            "BALANÇO PATRIMONIAL", "BALANÇO", "ATIVO", "PASSIVO",
            "CIRCULANTE", "NÃO CIRCULANTE", "IMOBILIZADO DE USO", "IMOBILIZADO",
            "ATIVOS INTANGÍVEIS", "INTANGÍVEL", "ÁGIO", "ESTOQUES",
            "OUTROS ATIVOS", "OUTROS PASSIVOS", "ATIVOS NÃO CORRENTES",
            "RECURSOS DE CLIENTES", "RECURSOS DE INSTITUIÇÕES",
            "RECURSOS DE EMISSÃO DE TÍTULOS", "DÍVIDAS SUBORDINADAS",
            "ITENS NÃO REGISTRADOS NO BALANÇO",
        ],
        DocumentSection.DRE: [
            "DEMONSTRAÇÃO DO RESULTADO", "RESULTADO ABRANGENTE",
            "RESULTADO LÍQUIDO DE JUROS", "RESULTADO LÍQUIDO DE SERVIÇOS",
            "RESULTADO DE SEGUROS", "RESULTADO", "DRE",
            "RECEITA DE JUROS", "RECEITA", "LUCRO LÍQUIDO", "LUCRO",
            "EBITDA", "EBIT", "DESPESAS DE PESSOAL",
            "OUTRAS DESPESAS ADMINISTRATIVAS", "DEPRECIAÇÃO E AMORTIZAÇÃO",
            "OUTRAS RECEITAS", "GANHOS/(PERDAS) LÍQUIDOS", "GANHOS",
            "CUSTO", "DESPESA", "CPV", "MARGEM",
            "IMPOSTO DE RENDA E CONTRIBUIÇÃO SOCIAL",
        ],
        DocumentSection.DFC: [
            "DEMONSTRAÇÃO DO FLUXO DE CAIXA", "FLUXO DE CAIXA", "DFC",
            "CAIXA, DISPONIBILIDADES", "EQUIVALENTES DE CAIXA",
            "ATIVIDADES OPERACIONAIS", "MÉTODO DIRETO", "MÉTODO INDIRETO",
        ],
        DocumentSection.DMPL: [
            "MUTAÇÃO DO PATRIMÔNIO LÍQUIDO", "PATRIMÔNIO LÍQUIDO", "DMPL",
            "MUTAÇÕES", "LUCROS ACUMULADOS", "RESERVAS DE LUCROS", "RESERVAS",
            "CAPITAL SOCIAL", "AJUSTES DE AVALIAÇÃO", "LUCRO POR AÇÃO",
        ],
        DocumentSection.NOTAS: [
            "NOTAS EXPLICATIVAS", "NOTA EXPLICATIVA",
            "POLÍTICAS CONTÁBEIS MATERIAIS", "POLÍTICAS CONTÁBEIS",
            "INFORMAÇÕES GERAIS", "USO DE ESTIMATIVAS", "JULGAMENTOS CONTÁBEIS",
            "NORMAS, ALTERAÇÕES E INTERPRETAÇÕES",
            "INSTRUMENTOS FINANCEIROS DERIVATIVOS", "INSTRUMENTOS FINANCEIROS",
            "CONTRATOS DE SEGUROS", "PROVISÕES, ATIVOS E PASSIVOS CONTINGENTES",
            "PROVISÕES", "GERENCIAMENTO DE RISCOS",
            "TRANSAÇÕES COM PARTES RELACIONADAS", "SEGMENTOS OPERACIONAIS",
            "PLANOS DE PREVIDÊNCIA COMPLEMENTAR", "OUTRAS INFORMAÇÕES",
            "CONTEXTO OPERACIONAL", "APRESENTAÇÃO DAS DEMONSTRAÇÕES",
            "SINISTROS", "ARRENDAMENTO", "PERDA DE CRÉDITO ESPERADA",
            "VALOR JUSTO", "RISCO DE CRÉDITO", "RISCO DE MERCADO",
            "RISCO OPERACIONAL", "RISCO DE LIQUIDEZ",
            "EMPRÉSTIMOS E ADIANTAMENTOS", "TÍTULOS E VALORES MOBILIÁRIOS",
            "COLIGADAS E JOINT VENTURE",
        ],
        DocumentSection.RELATORIO: [
            "RELATÓRIO DA ADMINISTRAÇÃO", "RELATÓRIO",
            "MENSAGEM AOS ACIONISTAS", "MENSAGEM", "COMENTÁRIO ECONÔMICO",
            "DESTAQUES", "TECNOLOGIA E INOVAÇÃO", "GOVERNANÇA CORPORATIVA",
            "SUSTENTABILIDADE", "RECONHECIMENTOS", "ACIONISTAS",
            "INFORMAÇÕES SELECIONADAS", "COMPLIANCE", "FUNDAÇÃO BRADESCO",
            "DESEMPENHO", "ADMINISTRAÇÃO", "DIRETORIA", "PANORAMA",
            "COMENTÁRIOS DOS ADMINISTRADORES",
        ],
    }

    for section, keywords in rules.items():
        if any(kw in text_upper for kw in keywords):
            return section

    return DocumentSection.OUTROS


def split_text(text: str, chunk_size_chars: int, overlap_chars: int) -> list[str]:
    """Divide o texto em chunks de tamanho máximo chunk_size_chars, com overlap de overlap_chars entre os chunks. A divisão é feita preferencialmente por parágrafos (duas quebras de linha), mas respeitando o limite de caracteres. Retorna a lista de chunks gerados."""
    paragrafos = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current_chunk = ""
    # Itera sobre os parágrafos, acumulando em current_chunk até atingir o tamanho máximo (chunk_size_chars).
    for p in paragrafos:
        if len(current_chunk) + len(p) > chunk_size_chars and current_chunk:
            chunks.append(current_chunk.strip())
            current_chunk = current_chunk[-overlap_chars:] + "\n\n" + p
        else:
            current_chunk = (current_chunk + "\n\n" + p).strip()

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks


class DFPChunker:
    """Responsável por dividir o conteúdo extraído de um relatório financeiro em chunks menores, enriquecendo cada chunk com um header que inclui metadados do documento e a seção detectada. O chunker processa primeiro as tabelas, depois o texto, garantindo que as tabelas sejam removidas do markdown para evitar poluição. Retorna a lista completa de chunks gerados para o documento."""

    def __init__(self, chunk_size: int = TEXT_CHUNK_SIZE, chunk_overlap: int = TEXT_CHUNK_OVERLAP):
        self.chunk_size_chars = chunk_size * CHARS_PER_TOKEN
        self.overlap = chunk_overlap * CHARS_PER_TOKEN

    def chunk(self, parsed_doc: dict[str, Any], metadata: DFPMetadata) -> list[Chunk]:
        """Processa o documento parseado e gera uma lista de chunks, enriquecendo cada chunk com um header que inclui metadados do documento e a seção detectada. O método processa primeiro as tabelas, depois o texto, garantindo que as tabelas sejam removidas do markdown para evitar poluição. Retorna a lista completa de chunks gerados para o documento."""
        all_chunks: list[Chunk] = []

        table_chunks = self.process_tables(parsed_doc["tables"], metadata)
        all_chunks.extend(table_chunks)
        logger.info(f"Processadas {len(table_chunks)} tabelas do documento.")

        text_chunks = self.process_text(parsed_doc, metadata)
        all_chunks.extend(text_chunks)
        logger.info(f"Processados {len(text_chunks)} chunks de texto do documento.")

        logger.info(
            f"Total de chunks gerados: {len(all_chunks)} para a empresa "
            f"{metadata.nome_empresa} - {metadata.ano_fiscal}."
        )
        return all_chunks

    def build_header(self, metadata: DFPMetadata, section: DocumentSection, page: int) -> str:
        """Constrói um header enriquecido para cada chunk, incluindo o nome da empresa, tipo e ano do relatório, seção detectada e número da página. Este header é adicionado antes do texto do chunk para fornecer contexto adicional durante a análise e indexação."""
        return (
            f"[{metadata.nome_empresa} | "
            f"{metadata.tipo_relatorio.value} {metadata.ano_fiscal} "
            f"{metadata.trimestre} | "
            f"Seção: {section.value} | Página: {page}]\n\n"
        )

    def process_tables(self, tables: list[dict], metadata: DFPMetadata) -> list[Chunk]:
        """Gera chunks para as tabelas extraídas do documento, enriquecendo o texto da tabela com um header que inclui metadados do documento e a seção detectada."""
        chunks = []
        for table in tables:
            table_md = table.get("markdown", "")
            if not table_md or len(table_md) < 10:
                continue

            section = detect_section(table_md)
            page = table.get("page") or 1
            enriched_text = self.build_header(metadata, section, page) + table_md

            chunks.append(Chunk(
                chunk_id=str(uuid.uuid4()),
                text=enriched_text,
                page_number=page,
                section=section,
                chunk_type="table",
                char_count=len(enriched_text),
                document_metadata=metadata,
            ))

        return chunks

    def process_text(self, parsed_doc: dict[str, Any], metadata: DFPMetadata) -> list[Chunk]:
        """Usa páginas extraídas nativamente pelo Docling quando disponíveis; cai no legado caso contrário."""
        pages = parsed_doc.get("pages", [])
        if pages:
            return self._process_text_by_pages(pages, metadata)

        logger.warning("'pages' ausente no parsed_doc — usando fallback baseado em markdown e heurísticas.")
        return self._process_text_legacy(parsed_doc.get("markdown", ""), metadata)

    def _process_text_by_pages(self, pages: list[dict], metadata: DFPMetadata) -> list[Chunk]:
        """Caminho principal: cada entrada de `pages` já tem page_no garantido pelo Docling."""
        chunks: list[Chunk] = []

        for page_data in pages:
            page_no = page_data["page_no"]
            text = page_data["text"]

            if not text.strip():
                continue

            section = detect_section(text)

            for part in split_text(text, self.chunk_size_chars, self.overlap):
                if len(part.strip()) < 51:
                    continue

                enriched_text = self.build_header(metadata, section, page_no) + part
                chunks.append(Chunk(
                    chunk_id=str(uuid.uuid4()),
                    text=enriched_text,
                    page_number=page_no,
                    section=section,
                    chunk_type="text",
                    char_count=len(enriched_text),
                    document_metadata=metadata,
                ))

        return chunks

    def _process_text_legacy(self, markdown: str, metadata: DFPMetadata) -> list[Chunk]:
        """Fallback: tenta detectar páginas via marcadores sintéticos do Docling, \\f ou rodapé IFRS."""
        clean_md = re.sub(r"```table.*?```", "", markdown, flags=re.DOTALL)

        chunks: list[Chunk] = []
        current_page = 1

        for section_text in re.split(r"(?m)^#{1,3} ", clean_md):
            if not section_text.strip():
                continue

            section_title_line = section_text.split("\n")[0]
            current_section = detect_section(section_title_line)

            page_segments = _split_by_page_breaks(section_text, start_page=current_page)

            for seg_page, seg_text in page_segments:
                current_page = seg_page

                for part in split_text(seg_text, self.chunk_size_chars, self.overlap):
                    if len(part.strip()) < 51:
                        continue

                    enriched_text = self.build_header(metadata, current_section, seg_page) + part
                    chunks.append(Chunk(
                        chunk_id=str(uuid.uuid4()),
                        text=enriched_text,
                        page_number=seg_page,
                        section=current_section,
                        chunk_type="text",
                        char_count=len(enriched_text),
                        document_metadata=metadata,
                    ))

        return chunks