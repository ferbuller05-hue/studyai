from pydantic import BaseModel, Field, field_validator
from datetime import date, datetime
from typing import Optional
from enum import Enum


# ── Enums ────────────────────────────────────────────────────────────────────

class ObjetivoEnum(str, Enum):
    vestibular       = "vestibular"
    enem             = "enem"
    concurso_federal = "concurso_federal"
    concurso_estadual = "concurso_estadual"
    faculdade        = "faculdade"
    outro            = "outro"


class NivelDificuldadeEnum(str, Enum):
    baixo = "baixo"
    medio = "médio"
    alto  = "alto"


# ── Sub-schemas ───────────────────────────────────────────────────────────────

class MateriaDificuldade(BaseModel):
    """Uma matéria com o nível de dificuldade declarado pelo aluno."""
    materia: str = Field(..., min_length=1, max_length=128,
                         examples=["Matemática", "Português", "Direito Administrativo"])
    nivel: NivelDificuldadeEnum = Field(..., examples=["alto"])


# ── Request schemas (entrada) ─────────────────────────────────────────────────

class OnboardingCreate(BaseModel):
    """
    Dados enviados pelo aluno durante o onboarding.
    Usado na rota POST /onboarding (a ser criada no próximo passo).
    """
    session_id: str = Field(..., min_length=8, max_length=64,
                             description="UUID gerado no localStorage do aluno")

    objetivo: ObjetivoEnum = Field(...,
                                    description="Objetivo principal do aluno")

    tipo_prova: str = Field(..., min_length=2, max_length=128,
                             examples=["ENEM", "FUVEST", "CEBRASPE — Analista TCU"])

    data_prova: Optional[date] = Field(None,
                                        description="Data da prova (opcional)")

    horas_por_dia: float = Field(..., ge=0.5, le=16.0,
                                  description="Horas disponíveis por dia para estudo")

    materias_dificuldade: list[MateriaDificuldade] = Field(
        default_factory=list,
        description="Matérias com dificuldade declarada"
    )

    @field_validator("data_prova")
    @classmethod
    def data_prova_nao_pode_ser_passado(cls, v: Optional[date]) -> Optional[date]:
        if v and v < date.today():
            raise ValueError("A data da prova não pode ser no passado.")
        return v

    @field_validator("materias_dificuldade")
    @classmethod
    def max_materias(cls, v: list) -> list:
        if len(v) > 20:
            raise ValueError("Máximo de 20 matérias por perfil.")
        return v


class OnboardingUpdate(BaseModel):
    """
    Atualização parcial do perfil de onboarding.
    Todos os campos são opcionais (PATCH semântico).
    """
    objetivo: Optional[ObjetivoEnum]              = None
    tipo_prova: Optional[str]                     = Field(None, max_length=128)
    data_prova: Optional[date]                    = None
    horas_por_dia: Optional[float]                = Field(None, ge=0.5, le=16.0)
    materias_dificuldade: Optional[list[MateriaDificuldade]] = None


# ── Response schemas (saída) ──────────────────────────────────────────────────

class OnboardingResponse(BaseModel):
    """
    Dados retornados ao frontend após criar ou buscar um perfil de onboarding.
    """
    id: int
    session_id: str
    objetivo: ObjetivoEnum
    tipo_prova: str
    data_prova: Optional[date]
    horas_por_dia: float
    materias_dificuldade: list[MateriaDificuldade]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
