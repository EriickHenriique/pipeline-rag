from abc import ABC, abstractmethod

from fin_pipeline.schemas import AgentState


class BaseAgent(ABC):

    nome: str

    @abstractmethod
    def run(self, state: AgentState) -> dict:
        """Executa a lógica do agente, recebendo o estado atual e retornando um dicionário com os resultados."""