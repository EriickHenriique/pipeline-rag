import re
import uuid
from typing import Any

from loguru import logger

from fin_pipeline.schemas.document import Chunk, DFPMetadata, DocumentSection


TEXT_CHUNK_SIZE = 500
TEXT_CHUNK_OVERLAP = 50
CHARS_PER_TOKEN = 4


def detect_section(text: str) -> DocumentSection:
    """Detecta a seção do documento com base em palavras-chave presentes no texto, utilizando regras pré-definidas 
    para classificar o conteúdo em categorias como DRE, Balanço, DFC, DMPL, Notas Explicativas, Relatório de Desempenho ou Outros."""

    text_upper = text.upper()

    # Regras de detecção baseadas em palavras-chave para cada seção do documento, onde cada seção é associada a um conjunto de palavras-chave que são verificadas no texto para determinar a qual seção ele pertence. Se nenhuma palavra-chave for encontrada, o texto é classificado como "Outros".
    rules = {
        DocumentSection.DRE: [
            "RESULTADO", "DRE", "RECEITA", "LUCRO", "EBITDA", "EBIT", 
            "CUSTO", "DESPESA", "OPERACIONAL", "FINANCEIRO", "CPV", "MARGEM"
        ],
        DocumentSection.BALANCO: [
            "BALANÇO", "ATIVO", "PASSIVO", "PATRIMÔNIO", "CIRCULANTE", 
            "NÃO CIRCULANTE", "IMOBILIZADO", "INTANGÍVEL", "ESTOQUES"
        ],
        DocumentSection.DFC: [
            "FLUXO DE CAIXA", "DFC", "ATIVIDADES OPERACIONAIS", 
            "INVESTIMENTO", "FINANCIAMENTO", "MÉTODO DIRETO", "MÉTODO INDIRETO"
        ],
        DocumentSection.DMPL: [
            "PATRIMÔNIO LÍQUIDO", "DMPL", "MUTAÇÕES", "LUCROS ACUMULADOS", 
            "RESERVAS", "CAPITAL SOCIAL", "ADJUSTES DE AVALIAÇÃO"
        ],
        DocumentSection.NOTAS: [
            "NOTA EXPLICATIVA", "NOTAS EXPLICATIVAS", "POLÍTICAS CONTÁBEIS", 
            "CONTEXTO OPERACIONAL", "APRESENTAÇÃO DAS DEMONSTRAÇÕES"
        ],
        DocumentSection.RELATORIO: [
            "RELATÓRIO", "MENSAGEM", "DESEMPENHO", "ADMINISTRAÇÃO", 
            "DIRETORIA", "PANORAMA", "COMENTÁRIOS DOS ADMINISTRADORES"
        ]
    }

    for section, keywords in rules.items():
        if any(kw in text_upper for kw in keywords):
            return section
        
    return DocumentSection.OUTROS

def split_text(text: str, chunk_size_chars: int, overlap_chars: int) -> list[str]:
    """Divide o texto em chunks menores, respeitando os limites de tamanho e sobreposição definidos, utilizando parágrafos como unidades de divisão para preservar a coesão do conteúdo."""
    
    # Remove múltiplas quebras de linha e espaços extras
    paragrafos = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current_chunk = ""

    # Itera sobre os parágrafos e constrói os chunks, garantindo que cada chunk não ultrapasse o tamanho máximo definido, e que haja uma sobreposição adequada entre os chunks para manter a continuidade do conteúdo.
    for p in paragrafos:
        if len(current_chunk) + len(p) > chunk_size_chars and current_chunk:
            chunks.append(current_chunk.strip())
            current_chunk = current_chunk[-overlap_chars:] + "\n\n" + p
        else:
            current_chunk = (current_chunk + "\n\n" + p).strip()
    
    # Adiciona o último chunk se houver conteúdo restante
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks

class DFPChunker:

    # Inicializa o chunker com os parâmetros de tamanho e sobreposição, convertendo os valores de tokens para caracteres com base
    # em uma média de caracteres por token, para garantir que os chunks gerados estejam dentro dos limites definidos e que haja uma sobreposição adequada entre eles.
    def __init__(self, chunk_size: int = TEXT_CHUNK_SIZE, chunk_overlap: int = TEXT_CHUNK_OVERLAP):
        self.chunk_size_chars = chunk_size * CHARS_PER_TOKEN
        self.overlap = chunk_overlap * CHARS_PER_TOKEN

    # Processa as tabelas extraídas do documento, criando chunks específicos para cada tabela, e associando metadados relevantes
    # como o nome da empresa, ano fiscal e seção do documento para facilitar a organização e consulta posterior.
    def chunk(self, parsed_doc: dict[str, Any], metadata: DFPMetadata) -> list[Chunk]:

        all_chunks: list[Chunk] = []

        table_chunks = self.process_tables(parsed_doc["tables"], metadata)
        all_chunks.extend(table_chunks)
        logger.info(f"Processadas {len(table_chunks)} tabelas do documento.")

        text_chunks = self.process_text(parsed_doc["markdown"], metadata)
        all_chunks.extend(text_chunks)
        logger.info(f"Processados {len(text_chunks)} chunks de texto do documento.")

        logger.info(f"Total de chunks gerados: {len(all_chunks)} para a empresa {metadata.nome_empresa} - {metadata.ano_fiscal}.")
        return all_chunks
    
    def build_header(self, metadata: DFPMetadata, section: DocumentSection, page: int) -> str:
        """Constrói um cabeçalho para cada chunk, contendo informações relevantes como o nome da empresa, tipo de relatório, 
        ano fiscal, seção do documento e número da página, para facilitar a identificação e organização dos chunks gerados."""
        return (
            f"[{metadata.nome_empresa} | "
            f"{metadata.tipo_relatorio.value} {metadata.ano_fiscal} "
            f"{metadata.trimestre} | "
            f"Seção: {section.value} | Página: {page}]\n\n"
        )
    
    def process_tables(self, tables: list[dict], metadata: DFPMetadata) -> list[Chunk]:
        # Processa as tabelas extraídas do documento, criando chunks específicos para cada tabela, 
        # e associando metadados relevantes
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

    def process_text(self, markdown: str, metadata: DFPMetadata) -> list[Chunk]:
        """Processa o texto extraído do documento, dividindo-o em chunks menores com base em parágrafos, e enriquecendo cada chunk com um cabeçalho que contém metadados relevantes como o nome da empresa, tipo de relatório, ano fiscal, seção do documento e número da página, para facilitar a identificação e organização dos chunks gerados."""

        # Remove as tabelas do markdown para evitar que sejam processadas como texto, já que elas serão processadas separadamente,
        #  e mantém o controle da seção atual e da página para enriquecer os chunks de texto com metadados relevantes.
        clean_md = re.sub(r"```table.*?```", "", markdown, flags=re.DOTALL)
        current_section = DocumentSection.OUTROS
        current_page = 1
        chunks = []

        # Divide o texto em seções com base nos títulos (marcados por #, ## ou ###), e processa cada seção individualmente para criar chunks de texto menores, enriquecidos com um cabeçalho que contém metadados relevantes como o nome da empresa, tipo de relatório, ano fiscal, seção do documento e número da página, para facilitar a identificação e organização dos chunks gerados.
        for section_text in re.split(r"(?m)^#{1,3} ", clean_md):
            if not section_text.strip():
                continue

            current_section = detect_section(section_text.split("\n")[0])

            page_match = re.search(r"<!-- Page (\d+) -->", section_text)
            if page_match:
                current_page = int(page_match.group(1))
            
            for part in split_text(section_text, self.chunk_size_chars, self.overlap):
                if len(part.strip()) < 51:
                    continue

                enriched_text = self.build_header(metadata, current_section, current_page) + part

                chunks.append(Chunk(
                    chunk_id=str(uuid.uuid4()),
                    text=enriched_text,
                    page_number=current_page,
                    section=current_section,
                    chunk_type="text",
                    char_count=len(enriched_text),
                    document_metadata=metadata,
                ))

        return chunks





    


