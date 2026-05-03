from loguru import logger

from fin_pipeline.agents.base import BaseAgent
from fin_pipeline.schemas.state import AgentState
from fin_pipeline.schemas.validation import (
    ValidationIssue,
    ValidationResult,
    ValidationVerdict
)

# Prompt para o agente de validação, orientando-o a avaliar a qualidade e confiabilidade da resposta gerada pelo agente de análise
# financeira, seguindo critérios específicos de avaliação e fornecendo feedback detalhado sobre quaisquer problemas identificados.
# O prompt é estruturado para garantir que o agente de validação produza uma avaliação rigorosa, baseada em evidências
# e bem fundamentada nos dados disponíveis.
MIN_CONFIDENCE = 0.5
MIN_SOURCES = 1
MAX_RETRIES = 3

class ValidatorAgent(BaseAgent):
    """Agente de validação responsável por avaliar a qualidade e confiabilidade da resposta gerada pelo agente de análise financeira, seguindo critérios específicos de avaliação e fornecendo feedback detalhado sobre quaisquer problemas identificados."""

    name = "ValidatorAgent"

    def run(self, state: AgentState) -> dict:
        """Executa o agente de validação, avaliando a análise financeira gerada pelo agente de análise e produzindo um resultado de validação com base em critérios específicos de avaliação."""
        analysis = state["draft_analysis"]
        retry_count = state.get("retry_count", 0)

        if analysis is None:
            return self._fail("draft_analysis", "Falta a análise financeira para validação.")
        
        issues: list[ValidationIssue] = []

        # Regra 1
        """Verifica se o nível de confiança da análise financeira é adequado, comparando-o com um valor mínimo esperado. Se o nível de confiança for inferior ao mínimo, registra um problema de validação indicando que a resposta pode não ser confiável."""
        confidence_ok = analysis.confidence >= MIN_CONFIDENCE
        if not confidence_ok:
            issues.append(
                ValidationIssue(
                    field="confidence",
                    severity="error",
                    message=f"Nível de confiança baixo: {analysis.confidence:.2f} (mínimo esperado: {MIN_CONFIDENCE})"
                )
            )
        
        # Regra 2
        """Verifica se o número de fontes utilizadas na análise financeira é adequado, comparando-o com um valor mínimo esperado. Se o número de fontes for inferior ao mínimo, registra um problema de validação indicando que a resposta pode não ser confiável."""
        sources_ok = len(analysis.sources) >= MIN_SOURCES
        if not sources_ok:
            issues.append(
                ValidationIssue(
                    field="sources",
                    severity="error",
                    message=f"Apenas {len(analysis.sources)} fontes, necessário ≥{MIN_SOURCES}",
                )
            )
        
        # Regra 3
        """Verifica se os KPIs extraídos na análise financeira são consistentes e plausíveis, especialmente para valores monetários. Se um KPI tiver um valor de exatamente 0 e for do tipo monetário (BRL ou USD), registra um problema de validação indicando que o valor pode ser suspeito e deve ser verificado."""
        kpis_ok = True
        for i, kpi in enumerate(analysis.kpis):
            if kpi.value == 0 and kpi.unit in ("BRL", "USD"):
                # Valor de KPI monetário é 0, o que pode ser suspeito e merece verificação adicional
                issues.append(
                    ValidationIssue(
                        field=f"kpis[{i}].value",
                        severity="error",
                        message=f"KPI '{kpi.name}' tem valor 0, o que pode ser suspeito para um KPI monetário ({kpi.unit})",
                    )
                )
        
        has_errors = any(i.severity == "error" for i in issues)

        if not has_errors:
            verdict = ValidationVerdict.PASS
            logger.info(f"[{self.name}] validação aprovada")
            update = {
                "validation_result": ValidationResult(
                verdict=verdict,
                issues=issues,
                confidence_check_passed=confidence_ok,
                sources_check_passed=sources_ok,
                kpis_check_passed=kpis_ok
                )
            }
        
        elif retry_count >= MAX_RETRIES:
            verdict = ValidationVerdict.FAIL
            logger.info(f"[{self.name}] validação falhou após {retry_count} tentativas")
            update = {
                "validation_result": ValidationResult(
                verdict=verdict,
                issues=issues,
                confidence_check_passed=confidence_ok,
                sources_check_passed=sources_ok,
                kpis_check_passed=kpis_ok
                ),
                "is_valid": False,
                "final_answer": analysis,
                "is_done": True,
                "validation_errors": [i.message for i in issues]
            }
        else:
            verdict = ValidationVerdict.RETRY
            logger.info(f"[{self.name}] validação requer nova tentativa ({retry_count}/{MAX_RETRIES})")
            update = {
                "validation_result": ValidationResult(
                verdict=verdict,
                issues=issues,
                confidence_check_passed=confidence_ok,
                sources_check_passed=sources_ok,
                kpis_check_passed=kpis_ok
                ),
                "is_valid": False,
                "retry_count": retry_count + 1,
                "validation_errors": [i.message for i in issues],
            }
        
        return update
    
    @staticmethod
    def _fail(field: str, message: str) -> dict:
        """Método auxiliar para criar um resultado de validação com veredicto de falha, incluindo um problema de validação específico para o campo indicado."""
        return {
            "is_valid": False,
            "is_done": True,
            "validation_erros": [f"{field}: {message}"]
        }
