from enum import Enum

from pydantic import BaseModel, Field


class ValidationVerdict(str, Enum):
    """Enumeração para representar o veredicto de uma validação, indicando se a resposta é válida, se deve ser reavaliada ou se é inválida."""
    PASS = "pass"
    RETRY = "retry"
    FAIL = "fail" 

class ValidationIssue(BaseModel):
    """Modelo para representar um problema identificado durante a validação, incluindo o campo específico da resposta que apresenta o problema e a gravidade do problema identificado."""
    field: str = Field(description="O campo específico da resposta que apresenta o problema identificado na validação.")
    severity: str = Field(description="A gravidade do problema identificado, que pode ser classificada como 'error'.")
    message: str = Field(description="Uma descrição detalhada do problema identificado na validação, explicando o que está errado ou o que precisa ser corrigido na resposta.")

class ValidationResult(BaseModel):
    """Modelo para representar o resultado de uma validação, incluindo o veredicto geral da validação, uma lista de problemas identificados durante a validação, e indicadores booleanos para cada tipo específico de verificação realizada (verificação de confiança, verificação de fontes e verificação de KPIs)."""
    verdict: ValidationVerdict = Field(description="O veredicto da validação, indicando se a resposta é válida (pass), se deve ser reavaliada (retry) ou se é inválida (fail).")
    issues: list[ValidationIssue] = Field(default_factory=list, description="Uma lista de problemas identificados durante a validação, onde cada problema inclui o campo específico da resposta que apresenta o problema, a gravidade do problema e uma descrição detalhada do que está errado ou precisa ser corrigido na resposta.")
    confidence_check_passed: bool = True
    sources_check_passed: bool = True
    kpis_check_passed: bool = True

    @property
    def is_valid(self) -> bool:
        """Propriedade para verificar se a resposta é considerada válida com base no veredicto da validação."""
        return self.verdict == ValidationVerdict.PASS



