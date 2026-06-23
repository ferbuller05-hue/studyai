"""create_cronograma_tables

Revision ID: a3f8c2e91b47
Revises: 19d1053e4ad7
Create Date: 2026-06-22

Cria as 3 tabelas do sistema de cronograma:
  - topic_progress
  - schedule_plans
  - schedule_sessions
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision:        str                    = "a3f8c2e91b47"
down_revision:   Union[str, None]       = "19d1053e4ad7"
branch_labels:   Union[str, Sequence[str], None] = None
depends_on:      Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── topic_progress ────────────────────────────────────────────────────────
    op.create_table(
        "topic_progress",
        sa.Column("id",              sa.Integer(),     primary_key=True, autoincrement=True),
        sa.Column("session_id",      sa.String(64),    nullable=False),
        sa.Column("tema",            sa.String(256),   nullable=False),
        sa.Column("dominio",         sa.Integer(),     nullable=False, server_default="0"),
        sa.Column("sessoes",         sa.Integer(),     nullable=False, server_default="0"),
        sa.Column("prioridade",      sa.String(16),    nullable=False, server_default="média"),
        sa.Column("proxima_revisao", sa.Date(),        nullable=True),
        sa.Column("concluido",       sa.Boolean(),     nullable=False, server_default=sa.false()),
        sa.Column("historico",       sa.JSON(),        nullable=False, server_default="[]"),
        sa.Column("created_at",      sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at",      sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("session_id", "tema", name="uq_topic_progress_session_tema"),
    )
    op.create_index("ix_topic_progress_session_id", "topic_progress", ["session_id"])

    # ── schedule_plans ────────────────────────────────────────────────────────
    op.create_table(
        "schedule_plans",
        sa.Column("id",              sa.Integer(),  primary_key=True, autoincrement=True),
        sa.Column("session_id",      sa.String(64), nullable=False, unique=True),
        sa.Column("status",          sa.String(16), nullable=False, server_default="ativo"),
        sa.Column("data_prova",      sa.Date(),     nullable=True),
        sa.Column("horas_por_dia",   sa.Float(),    nullable=False, server_default="2.0"),
        sa.Column("total_semanas",   sa.Integer(),  nullable=True),
        sa.Column("config_snapshot", sa.JSON(),     nullable=True),
        sa.Column("gerado_em",       sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("atualizado_em",   sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_schedule_plans_session_id", "schedule_plans", ["session_id"])

    # ── schedule_sessions ─────────────────────────────────────────────────────
    op.create_table(
        "schedule_sessions",
        sa.Column("id",               sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("plan_id",          sa.Integer(), sa.ForeignKey("schedule_plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_id",       sa.String(64), nullable=False),
        sa.Column("data",             sa.Date(),    nullable=False),
        sa.Column("ordem_no_dia",     sa.Integer(), nullable=False, server_default="1"),
        sa.Column("duracao_minutos",  sa.Integer(), nullable=False, server_default="60"),
        sa.Column("tema",             sa.String(256), nullable=False),
        sa.Column("tipo",             sa.String(16),  nullable=False, server_default="novo"),
        sa.Column("prioridade",       sa.String(16),  nullable=False, server_default="média"),
        sa.Column("status",           sa.String(16),  nullable=False, server_default="pendente"),
        sa.Column("concluido_em",     sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_schedule_sessions_plan_id",    "schedule_sessions", ["plan_id"])
    op.create_index("ix_schedule_sessions_session_id", "schedule_sessions", ["session_id"])
    op.create_index("ix_schedule_sessions_data",       "schedule_sessions", ["data"])


def downgrade() -> None:
    op.drop_table("schedule_sessions")
    op.drop_table("schedule_plans")
    op.drop_table("topic_progress")
