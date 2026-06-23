"""
Modelos do sistema de cronograma.

Tabelas:
  topic_progress   — domínio de cada tema por aluno (migra o localStorage studyai_perfil)
  schedule_plans   — plano de estudos geral (1 por aluno)
  schedule_sessions — blocos individuais de estudo agendados
"""

from sqlalchemy import (
    Column, Integer, String, Float, Date, DateTime, Boolean,
    JSON, ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class TopicProgress(Base):
    """
    Domínio de um tema específico para um aluno (session_id).

    Substitui o objeto de tema dentro de studyai_perfil no localStorage.
    A constraint UNIQUE(session_id, tema) garante um registro por aluno/tema.
    """
    __tablename__ = "topic_progress"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), nullable=False, index=True)
    tema       = Column(String(256), nullable=False)

    # Domínio atual (0–100). Calculado por analisar_feedback().
    dominio    = Column(Integer, nullable=False, default=0)

    # Total de sessões de estudo realizadas neste tema.
    sessoes    = Column(Integer, nullable=False, default=0)

    # Prioridade vinda do diagnóstico: "alta" | "média" | "baixa"
    prioridade = Column(String(16), nullable=False, default="média")

    # Data da próxima revisão (repetição espaçada).
    # Calculada em feedback.py: 1d (<50%), 3d (<70%), 7d (<85%), 14d (≥85%).
    proxima_revisao = Column(Date, nullable=True)

    # True quando domínio ≥ 90.
    concluido = Column(Boolean, nullable=False, default=False)

    # Histórico completo de sessões.
    # Formato: [{"data": "2026-06-22", "dominio": 45, "feedback": "..."}]
    historico = Column(JSON, nullable=False, default=list)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(),
                        onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("session_id", "tema", name="uq_topic_progress_session_tema"),
    )

    def __repr__(self) -> str:
        return f"<TopicProgress session={self.session_id!r} tema={self.tema!r} dominio={self.dominio}>"


class SchedulePlan(Base):
    """
    Plano de estudos do aluno. Um registro por aluno (UNIQUE session_id).

    Gerado a partir de OnboardingProfile + TopicProgress.
    Regenerado automaticamente quando o onboarding é atualizado.
    """
    __tablename__ = "schedule_plans"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), nullable=False, unique=True, index=True)

    # "ativo" | "pausado" | "concluido"
    status     = Column(String(16), nullable=False, default="ativo")

    # Snapshot dos dados usados na geração (para detectar se precisa regenerar).
    data_prova    = Column(Date, nullable=True)
    horas_por_dia = Column(Float, nullable=False, default=2.0)
    total_semanas = Column(Integer, nullable=True)

    # Snapshot completo do OnboardingProfile no momento da geração.
    # Permite detectar mudanças e regenerar o plano se necessário.
    config_snapshot = Column(JSON, nullable=True)

    gerado_em    = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    atualizado_em = Column(DateTime(timezone=True), server_default=func.now(),
                           onupdate=func.now(), nullable=False)

    # Relacionamento com os blocos de estudo.
    sessoes = relationship(
        "ScheduleSession",
        back_populates="plano",
        cascade="all, delete-orphan",
        order_by="ScheduleSession.data, ScheduleSession.ordem_no_dia",
    )

    def __repr__(self) -> str:
        return f"<SchedulePlan session={self.session_id!r} status={self.status!r}>"


class ScheduleSession(Base):
    """
    Bloco individual de estudo dentro de um SchedulePlan.

    Cada linha representa uma sessão de estudo agendada para uma data/tema/tipo.
    """
    __tablename__ = "schedule_sessions"

    id      = Column(Integer, primary_key=True, autoincrement=True)
    plan_id = Column(Integer, ForeignKey("schedule_plans.id", ondelete="CASCADE"),
                     nullable=False, index=True)

    # Redundante mas evita JOINs nas queries de listagem por aluno.
    session_id = Column(String(64), nullable=False, index=True)

    # Quando acontece.
    data          = Column(Date, nullable=False, index=True)
    ordem_no_dia  = Column(Integer, nullable=False, default=1)  # 1 = primeiro bloco do dia
    duracao_minutos = Column(Integer, nullable=False, default=60)

    # O que estudar.
    tema      = Column(String(256), nullable=False)

    # "novo" | "revisao" | "exercicio"
    tipo      = Column(String(16), nullable=False, default="novo")

    # "alta" | "média" | "baixa"
    prioridade = Column(String(16), nullable=False, default="média")

    # "pendente" | "concluido" | "pulado"
    status     = Column(String(16), nullable=False, default="pendente")

    # Preenchido quando status → "concluido".
    concluido_em = Column(DateTime(timezone=True), nullable=True)

    plano = relationship("SchedulePlan", back_populates="sessoes")

    def __repr__(self) -> str:
        return (
            f"<ScheduleSession plan={self.plan_id} "
            f"data={self.data} tema={self.tema!r} tipo={self.tipo!r} status={self.status!r}>"
        )
