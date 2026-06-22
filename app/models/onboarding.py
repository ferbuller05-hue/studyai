from sqlalchemy import Column, Integer, String, Float, Date, DateTime, JSON
from sqlalchemy.sql import func
from app.database import Base


class OnboardingProfile(Base):
    """
    Perfil de onboarding do aluno.
    Coletado antes do primeiro diagnóstico para personalizar a experiência.

    session_id: identificador único vindo do localStorage (sem necessidade de login).
    """
    __tablename__ = "onboarding_profiles"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Identificador de sessão (localStorage uuid gerado no frontend)
    session_id = Column(String(64), unique=True, index=True, nullable=False)

    # Objetivo principal do aluno
    # Valores esperados: "vestibular" | "enem" | "concurso_federal" |
    #                    "concurso_estadual" | "faculdade" | "outro"
    objetivo = Column(String(32), nullable=False)

    # Nome específico da prova (ex: "FUVEST", "ENEM", "CEBRASPE — Analista TRF")
    tipo_prova = Column(String(128), nullable=False)

    # Data da prova (permite calcular dias restantes e urgência)
    data_prova = Column(Date, nullable=True)

    # Horas disponíveis por dia para estudo (ex: 1.5, 3.0, 6.0)
    horas_por_dia = Column(Float, nullable=False, default=2.0)

    # Lista de matérias com dificuldade declarada pelo aluno.
    # Formato JSON: [{"materia": "Matemática", "nivel": "alto"}, ...]
    # Níveis: "baixo" | "médio" | "alto"
    materias_dificuldade = Column(JSON, nullable=False, default=list)

    # Timestamps automáticos
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(),
                        onupdate=func.now(), nullable=False)

    def __repr__(self) -> str:
        return (
            f"<OnboardingProfile id={self.id} "
            f"objetivo={self.objetivo!r} "
            f"tipo_prova={self.tipo_prova!r}>"
        )
