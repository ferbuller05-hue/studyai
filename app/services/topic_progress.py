"""
TopicProgressService — persiste e consulta o domínio dos temas por aluno.

Substitui o objeto de temas do localStorage studyai_perfil no backend.
Ponto de entrada principal: bulk_sync() ao carregar a página de progresso.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.models.cronograma import TopicProgress
from app.schemas.cronograma import TopicProgressUpsert, TopicProgressBulkSync


class TopicProgressService:

    # ── Escrita ───────────────────────────────────────────────────────────────

    @staticmethod
    def upsert(db: Session, data: TopicProgressUpsert) -> TopicProgress:
        """
        Cria um registro de TopicProgress ou atualiza o existente.

        Usa UNIQUE(session_id, tema) como chave de conflito.
        Se o tema já existe, sobrescreve apenas os campos enviados.

        Retorna a instância persistida (com id preenchido).
        """
        raise NotImplementedError("Aguardando aprovação do algoritmo — step 2")

    @staticmethod
    def bulk_sync(
        db: Session,
        session_id: str,
        temas: list[TopicProgressUpsert],
    ) -> list[TopicProgress]:
        """
        Sincroniza o localStorage inteiro de uma vez.

        Chama upsert() para cada tema da lista.
        Não remove temas que existam no banco mas não vieram no payload
        (o backend é source of truth após o primeiro sync).

        Retorna todos os TopicProgress do aluno após o sync.
        """
        raise NotImplementedError("Aguardando aprovação do algoritmo — step 2")

    # ── Leitura ───────────────────────────────────────────────────────────────

    @staticmethod
    def get_all(db: Session, session_id: str) -> list[TopicProgress]:
        """Retorna todos os temas do aluno, ordenados por domínio ASC."""
        return (
            db.query(TopicProgress)
            .filter(TopicProgress.session_id == session_id)
            .order_by(TopicProgress.dominio.asc())
            .all()
        )

    @staticmethod
    def get_tema(
        db: Session, session_id: str, tema: str
    ) -> Optional[TopicProgress]:
        """Retorna um tema específico ou None se não existir."""
        return (
            db.query(TopicProgress)
            .filter(
                TopicProgress.session_id == session_id,
                TopicProgress.tema == tema,
            )
            .first()
        )

    @staticmethod
    def get_dominados(
        db: Session, session_id: str, threshold: int = 70
    ) -> list[TopicProgress]:
        """
        Retorna temas com domínio >= threshold.
        Default threshold=70 (usado no diagnóstico premium).
        """
        return (
            db.query(TopicProgress)
            .filter(
                TopicProgress.session_id == session_id,
                TopicProgress.dominio >= threshold,
            )
            .order_by(TopicProgress.dominio.desc())
            .all()
        )

    @staticmethod
    def get_fracos(
        db: Session, session_id: str, threshold: int = 50
    ) -> list[TopicProgress]:
        """
        Retorna temas com domínio < threshold, priorizados por prioridade alta.
        Esses temas têm prioridade máxima no cronograma.
        """
        return (
            db.query(TopicProgress)
            .filter(
                TopicProgress.session_id == session_id,
                TopicProgress.dominio < threshold,
                TopicProgress.concluido == False,  # noqa: E712
            )
            .order_by(
                # prioridade alta primeiro
                TopicProgress.prioridade.desc(),
                TopicProgress.dominio.asc(),
            )
            .all()
        )

    @staticmethod
    def get_revisoes_pendentes(
        db: Session, session_id: str
    ) -> list[TopicProgress]:
        """
        Retorna temas cuja proxima_revisao <= hoje.
        Usados pelo ScheduleService para intercalar revisões no cronograma.
        """
        hoje = date.today()
        return (
            db.query(TopicProgress)
            .filter(
                TopicProgress.session_id == session_id,
                TopicProgress.proxima_revisao <= hoje,
                TopicProgress.concluido == False,  # noqa: E712
            )
            .order_by(TopicProgress.proxima_revisao.asc())
            .all()
        )
