"""
ScheduleService — cria e gerencia o plano de estudos do aluno.

Fluxo principal:
  1. get_or_create_plano()  — retorna plano existente ou inicia um novo
  2. gerar_sessoes()        — distribui os temas nos dias disponíveis (algoritmo pendente)
  3. atualizar_sessao()     — aluno marca bloco como concluído ou pulado
  4. regenerar_plano()      — recalcula tudo quando onboarding muda

O algoritmo de distribuição (gerar_sessoes) será definido e aprovado em step separado.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.models.cronograma import SchedulePlan, ScheduleSession
from app.models.onboarding import OnboardingProfile
from app.schemas.cronograma import ScheduleSessionUpdate


class ScheduleService:

    # ── Plano ─────────────────────────────────────────────────────────────────

    @staticmethod
    def get_plano(db: Session, session_id: str) -> Optional[SchedulePlan]:
        """Retorna o plano ativo do aluno, ou None se não existir."""
        return (
            db.query(SchedulePlan)
            .filter(SchedulePlan.session_id == session_id)
            .first()
        )

    @staticmethod
    def get_or_create_plano(
        db: Session,
        session_id: str,
        onboarding: OnboardingProfile,
    ) -> SchedulePlan:
        """
        Retorna o plano existente do aluno.
        Se não existir, cria um novo SchedulePlan (sem sessões ainda).

        Após criar, o chamador deve invocar gerar_sessoes() para popular o plano.
        """
        raise NotImplementedError("Aguardando aprovação do algoritmo — step 2")

    @staticmethod
    def regenerar_plano(
        db: Session,
        session_id: str,
        onboarding: OnboardingProfile,
    ) -> SchedulePlan:
        """
        Apaga todas as sessões pendentes e recria o plano do zero.

        Disparado quando o aluno atualiza o onboarding (nova data de prova,
        mudança de horas por dia, etc.).

        Sessões já concluídas são preservadas no histórico.
        """
        raise NotImplementedError("Aguardando aprovação do algoritmo — step 2")

    @staticmethod
    def gerar_sessoes(
        db: Session,
        plan: SchedulePlan,
        onboarding: OnboardingProfile,
        temas_priorizados: list,  # list[TopicPriorityScore] do PriorityService
    ) -> list[ScheduleSession]:
        """
        Distribui os temas nos dias disponíveis até a prova.

        Entradas:
          - plan: SchedulePlan já criado (com data_prova, horas_por_dia)
          - onboarding: perfil completo do aluno
          - temas_priorizados: lista ordenada de TopicPriorityScore

        Regras (algoritmo a ser aprovado):
          - Cada dia tem N blocos = horas_por_dia / bloco_padrão (ex: 60 min)
          - Temas de prioridade alta preenchem os primeiros blocos
          - Revisões pendentes são intercaladas (a cada 3 blocos novos, 1 revisão)
          - Exercícios são inseridos após domínio ≥ 70
          - Último bloco do dia é sempre revisão do que foi visto naquela semana

        Retorna a lista de ScheduleSession criadas.
        """
        raise NotImplementedError("Aguardando aprovação do algoritmo — step 3")

    # ── Sessões ───────────────────────────────────────────────────────────────

    @staticmethod
    def atualizar_sessao(
        db: Session,
        sessao_id: int,
        data: ScheduleSessionUpdate,
        session_id: str,  # validação de ownership
    ) -> ScheduleSession:
        """
        Marca um bloco como concluído ou pulado.

        Se status → "concluido", preenche concluido_em com datetime.now().
        Valida que o session_id do chamador bate com o da sessão (sem login,
        usamos o session_id do localStorage como "dono").

        Levanta ValueError se sessao_id não existir ou não pertencer ao aluno.
        """
        raise NotImplementedError("Aguardando aprovação do algoritmo — step 2")

    @staticmethod
    def get_sessoes_hoje(
        db: Session, session_id: str
    ) -> list[ScheduleSession]:
        """
        Retorna os blocos de estudo agendados para hoje.
        Ordenados por ordem_no_dia.
        """
        hoje = date.today()
        return (
            db.query(ScheduleSession)
            .filter(
                ScheduleSession.session_id == session_id,
                ScheduleSession.data == hoje,
            )
            .order_by(ScheduleSession.ordem_no_dia.asc())
            .all()
        )

    @staticmethod
    def get_sessoes_semana(
        db: Session, session_id: str
    ) -> list[ScheduleSession]:
        """
        Retorna os blocos dos próximos 7 dias (hoje inclusive).
        Ordenados por data, ordem_no_dia.
        """
        hoje = date.today()
        fim  = hoje + timedelta(days=6)
        return (
            db.query(ScheduleSession)
            .filter(
                ScheduleSession.session_id == session_id,
                ScheduleSession.data >= hoje,
                ScheduleSession.data <= fim,
            )
            .order_by(ScheduleSession.data.asc(), ScheduleSession.ordem_no_dia.asc())
            .all()
        )

    # ── Helpers internos ──────────────────────────────────────────────────────

    @staticmethod
    def _onboarding_snapshot(onboarding: OnboardingProfile) -> dict:
        """
        Serializa os campos relevantes do onboarding para config_snapshot.
        Usado para detectar se o plano precisa ser regenerado.
        """
        return {
            "data_prova":           str(onboarding.data_prova) if onboarding.data_prova else None,
            "horas_por_dia":        onboarding.horas_por_dia,
            "materias_dificuldade": onboarding.materias_dificuldade or [],
        }

    @staticmethod
    def _plano_desatualizado(
        plano: SchedulePlan, onboarding: OnboardingProfile
    ) -> bool:
        """
        Compara o config_snapshot do plano com o onboarding atual.
        Retorna True se algum campo relevante mudou (deve regenerar).
        """
        snap = plano.config_snapshot or {}
        data_prova_str = str(onboarding.data_prova) if onboarding.data_prova else None
        return (
            snap.get("data_prova")    != data_prova_str
            or snap.get("horas_por_dia") != onboarding.horas_por_dia
        )
