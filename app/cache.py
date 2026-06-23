"""
Cache em memória com TTL para diagnósticos e rankings.

Por que em memória (não Redis)?
  - Render free tier não tem Redis
  - O processo do Uvicorn é único (WEB_CONCURRENCY=1 no free tier)
  - Em memória é suficiente e zero latência adicional

Uso:
    chave = cache_key("conteudo do material")
    resultado = get_cached(chave)
    if resultado is None:
        resultado = chamar_ia()
        set_cached(chave, resultado)
"""

import hashlib
import time
from typing import Any

# TTL padrão: 1 hora (diagnósticos raramente mudam para o mesmo material)
_DEFAULT_TTL = 3600

_store: dict[str, tuple[Any, float]] = {}


def cache_key(*partes: str) -> str:
    """Gera chave MD5 a partir de uma ou mais strings."""
    conteudo = "|".join(str(p) for p in partes)
    return hashlib.md5(conteudo.encode("utf-8")).hexdigest()


def get_cached(chave: str, ttl: int = _DEFAULT_TTL) -> Any | None:
    """Retorna valor cacheado se ainda válido, ou None."""
    entry = _store.get(chave)
    if entry is None:
        return None
    valor, ts = entry
    if time.time() - ts > ttl:
        del _store[chave]
        return None
    return valor


def set_cached(chave: str, valor: Any) -> None:
    """Armazena valor no cache com timestamp atual."""
    _store[chave] = (valor, time.time())


def cache_size() -> int:
    """Retorna quantidade de entradas no cache (para debug/health)."""
    return len(_store)


def cache_clear() -> None:
    """Limpa todo o cache (útil para testes)."""
    _store.clear()
