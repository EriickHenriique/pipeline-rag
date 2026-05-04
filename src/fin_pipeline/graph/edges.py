from loguru import logger

from fin_pipeline.schemas.state import AgentState
from fin_pipeline.schemas.validation import ValidationVerdict

def route_after_validation(state: AgentState) -> str:
    """ Decide o que acontece depois que a validação é feita.

    retorna:
        "retry" -> voltar ao nó de análise financeira para tentar novamente.
        "end" -> finalizar o pipeline.

    """
    result = state.get("validation_result")

    if not result:
        logger.error("[edge] Nenhum resultado de validação encontrado.")
        return "end"

    match result.verdict:
        case ValidationVerdict.PASS:
            logger.info("[edge] Validação passou. Finalizando pipeline.")
            return "end"
        
        case ValidationVerdict.RETRY:
            logger.info("[edge] Validação falhou. Tentando novamente.")
            return "retry"
        
    # Caso o veredicto seja desconhecido, loga um aviso e finaliza o pipeline.    
    logger.warning(f"[edge] Veredicto desconhecido: {result.verdict}. Finalizando.")
    return "end"