"""
PriorityService — calcula a ordem de prioridade dos temas para o cronograma.

Score de urgência considera 4 fatores:
  1. domínio atual   — quanto menor o domínio, maior a urgência
  2. prioridade do diagnóstico — alta/média/baixa (vinda do extractor.py)
  3. declaração do aluno — matérias marcadas como difíceis no onboarding
  4. revisão pendente  — temas com proxima_revisao vencida sobem na lista

O algoritmo final (pesos) será definido e aprovado separadamente.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from app.models.cronograma import TopicProgress
from app.models.onboarding import OnboardingProfile


@dataclass
class TopicPriorityScore:
    """Resultado do cálculo de prioridade para um tema."""
    tema:              str
    score:             float          # score final (maior = mais urgente)
    dominio:           int
    prioridade_diag:   str            # "alta" | "média" | "baixa"
    declarado_dificil: bool           # aluno marcou no onboarding
    revisao_pendente:  bool
    tipo_sugerido:     str            # "novo" | "revisao" | "exercicio"


class PriorityService:

    @staticmethod
    def calcular_prioridades(
        topics: list[TopicProgress],
        onboarding: OnboardingProfile,
    ) -> list[TopicPriorityScore]:
        """
        Recebe todos os TopicProgress do aluno + o perfil de onboarding.
        Retorna lista ordenada por score DESC (mais urgente primeiro).

        Regras de negócio (pesos a serem aprovados):
          - Domínio 0–49   → bônus alto   (tema fraco, precisa de atenção)
          - Domínio 50–69  → bônus médio
          - Domínio 70–89  → bônus baixo  (quase dominado, mantém revisão)
          - Domínio ≥ 90   → penalidade   (já dominado, vai para o fim)
          - prioridade "alta" do diagnóstico → bônus
          - matéria declarada difícil no onboarding → bônus extra
          - proxima_revisao vencida → bônus de urgência de revisão
          - dias_restantes baixo → amplifica todos os bônus

        O tipo_sugerido é inferido do domínio:
          domínio = 0       → "novo"
          0 < domínio < 70  → "novo" ou "revisao" (alternado pelo ScheduleService)
          domínio ≥ 70      → "revisao" ou "exercicio"
        """
        raise NotImplementedError("Aguardando aprovação dos pesos — step 3")

    @staticmethod
    def _materias_dificeis_set(onboarding: OnboardingProfile) -> set[str]:
        """
        Extrai os nomes das matérias declaradas difíceis no onboarding
        como um set de strings em lowercase para comparação rápida.

        Exemplo: {"matemática", "direito administrativo"}
        """
        materias = onboarding.materias_dificuldade or []
        return {
            m["materia"].lower()
            for m in materias
            if m.get("nivel") in ("médio", "alto")
        }

    @staticmethod
    def _tipo_sugerido(dominio: int) -> str:
        """Infere o tipo de sessão mais adequado ao nível de domínio."""
        if dominio == 0:
            return "novo"
        if dominio < 70:
            return "novo"   # ScheduleService alterna com "revisao"
        return "revisao"    # ScheduleService alterna com "exercicio"
