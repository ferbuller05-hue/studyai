from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.models.onboarding import OnboardingProfile
from app.schemas.onboarding import (
    OnboardingCreate,
    OnboardingUpdate,
    OnboardingResponse,
)

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_or_404(session_id: str, db: Session) -> OnboardingProfile:
    """Busca perfil pelo session_id ou levanta 404."""
    profile = (
        db.query(OnboardingProfile)
        .filter(OnboardingProfile.session_id == session_id)
        .first()
    )
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Perfil não encontrado para session_id '{session_id}'.",
        )
    return profile


# ── POST /onboarding ──────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=OnboardingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cria perfil de onboarding do aluno",
)
def criar_onboarding(
    payload: OnboardingCreate,
    db: Session = Depends(get_db),
) -> OnboardingProfile:
    """
    Recebe os dados do onboarding e persiste na tabela onboarding_profiles.

    - **session_id**: UUID gerado no localStorage do aluno (único por dispositivo).
    - **objetivo**: vestibular | enem | concurso_federal | concurso_estadual | faculdade | outro
    - **tipo_prova**: nome da prova (ex: "ENEM", "FUVEST", "CEBRASPE — TRF").
    - **data_prova**: data da prova (não pode ser no passado).
    - **horas_por_dia**: entre 0.5 e 16.
    - **materias_dificuldade**: lista de {materia, nivel} — máximo 20 itens.

    Retorna 409 se já existir um perfil para o session_id informado.
    """
    # Verifica duplicidade antes de tentar inserir
    existe = (
        db.query(OnboardingProfile)
        .filter(OnboardingProfile.session_id == payload.session_id)
        .first()
    )
    if existe:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Já existe um perfil para session_id '{payload.session_id}'. "
                "Use PATCH /onboarding/{session_id} para atualizar."
            ),
        )

    profile = OnboardingProfile(
        session_id=payload.session_id,
        objetivo=payload.objetivo.value,
        tipo_prova=payload.tipo_prova,
        data_prova=payload.data_prova,
        horas_por_dia=payload.horas_por_dia,
        materias_dificuldade=[
            m.model_dump() for m in payload.materias_dificuldade
        ],
    )

    try:
        db.add(profile)
        db.commit()
        db.refresh(profile)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conflito ao salvar perfil. Tente novamente.",
        )

    return profile


# ── GET /onboarding/{session_id} ──────────────────────────────────────────────

@router.get(
    "/{session_id}",
    response_model=OnboardingResponse,
    summary="Retorna perfil de onboarding pelo session_id",
)
def buscar_onboarding(
    session_id: str,
    db: Session = Depends(get_db),
) -> OnboardingProfile:
    """
    Busca o perfil de onboarding pelo session_id (vindo do localStorage).

    Retorna 404 se o perfil não existir.
    """
    return _get_or_404(session_id, db)


# ── PATCH /onboarding/{session_id} ───────────────────────────────────────────

@router.patch(
    "/{session_id}",
    response_model=OnboardingResponse,
    summary="Atualiza parcialmente o perfil de onboarding",
)
def atualizar_onboarding(
    session_id: str,
    payload: OnboardingUpdate,
    db: Session = Depends(get_db),
) -> OnboardingProfile:
    """
    Atualiza apenas os campos enviados (PATCH semântico).
    Campos não enviados no body permanecem inalterados.

    Retorna 404 se o perfil não existir.
    """
    profile = _get_or_404(session_id, db)

    # Aplica apenas os campos que vieram no payload (exclui None)
    updates = payload.model_dump(exclude_none=True)

    for field, value in updates.items():
        if field == "objetivo" and value is not None:
            # Converte enum para string antes de salvar
            setattr(profile, field, value.value if hasattr(value, "value") else value)
        elif field == "materias_dificuldade" and value is not None:
            setattr(profile, field, [m.model_dump() for m in value])
        else:
            setattr(profile, field, value)

    try:
        db.commit()
        db.refresh(profile)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Erro ao atualizar perfil. Verifique os dados enviados.",
        )

    return profile
