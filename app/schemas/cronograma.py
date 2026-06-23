"""
Schemas Pydantic v2 para o sistema de cronograma.

Grupos:
  TopicProgress  — domínio dos temas
  SchedulePlan   — plano geral
  ScheduleSession — bloco individual de estudo
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field


# ── Enums como Literal (evita import desnecessário de Enum) ──────────────────

PrioridadeType  = Literal["alta", "média", "baixa"]
TipoSessaoType  = Literal["novo", "revisao", "exercicio"]
StatusSessaoType = Literal["pendente", "concluido", "pulado"]
StatusPlanoType  = Literal["ativo", "pausado", "concluido"]


# ═══════════════════════════════════════════════════════════════════════════════
# TopicProgress
# ═══════════════════════════════════════════════════════════════════════════════

class TopicProgressUpsert(BaseModel):
    """
    Cria ou atualiza o domínio de um tema.
    Usado por TopicProgressService.upsert() e pelo endpoint de sync.
    """
    session_id: str         = Field(..., min_length=8, max_length=64)
    tema:       str         = Field(..., min_length=1, max_length=256)
    dominio:    int         = Field(..., ge=0, le=100)
    sessoes:    int         = Field(default=0, ge=0)
    prioridade: PrioridadeType = "média"
    proxima_revisao: Optional[date] = None
    concluido:  bool        = False
    historico:  list[dict]  = Field(default_factory=list)


class TopicProgressBulkSync(BaseModel):
    """
    Sincroniza o localStorage studyai_perfil inteiro de uma vez.
    O frontend envia session_id + lista de temas ao carregar a página.
    """
    session_id: str
    temas: list[TopicProgressUpsert]


class TopicProgressResponse(BaseModel):
    """Retorno completo de um tema."""
    id:              int
    session_id:      str
    tema:            str
    dominio:         int
    sessoes:         int
    prioridade:      str
    proxima_revisao: Optional[date]
    concluido:       bool
    historico:       list[dict]
    created_at:      datetime
    updated_at:      datetime

    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════════════════════════
# ScheduleSession
# ═══════════════════════════════════════════════════════════════════════════════

class ScheduleSessionResponse(BaseModel):
    """Bloco individual de estudo (leitura)."""
    id:              int
    plan_id:         int
    session_id:      str
    data:            date
    ordem_no_dia:    int
    duracao_minutos: int
    tema:            str
    tipo:            str
    prioridade:      str
    status:          str
    concluido_em:    Optional[datetime]

    model_config = {"from_attributes": True}


class ScheduleSessionUpdate(BaseModel):
    """
    Atualiza o status de um bloco de estudo.
    Enviado pelo frontend ao marcar uma sessão como concluída ou pulada.
    """
    status: Literal["concluido", "pulado"]


# ═══════════════════════════════════════════════════════════════════════════════
# SchedulePlan
# ═══════════════════════════════════════════════════════════════════════════════

class SchedulePlanCreate(BaseModel):
    """
    Solicita a criação (ou regeneração) de um plano de estudos.
    O serviço busca OnboardingProfile e TopicProgress pelo session_id.
    """
    session_id: str = Field(..., min_length=8, max_length=64)


class SchedulePlanResponse(BaseModel):
    """Plano completo com todos os blocos de estudo."""
    id:             int
    session_id:     str
    status:         str
    data_prova:     Optional[date]
    horas_por_dia:  float
    total_semanas:  Optional[int]
    gerado_em:      datetime
    atualizado_em:  datetime
    sessoes:        list[ScheduleSessionResponse]

    model_config = {"from_attributes": True}


class SchedulePlanSummary(BaseModel):
    """
    Resumo do plano (sem listar todos os blocos).
    Usado na página inicial para mostrar o status geral.
    """
    id:                  int
    status:              str
    data_prova:          Optional[date]
    horas_por_dia:       float
    total_semanas:       Optional[int]
    total_sessoes:       int   # contagem de ScheduleSession
    sessoes_concluidas:  int
    sessoes_pendentes:   int
    gerado_em:           datetime

    model_config = {"from_attributes": True}
