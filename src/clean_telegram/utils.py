"""Funções utilitárias para CleanTelegram."""

import asyncio
import logging
import os
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


def env_int(name: str) -> int:
    """Lê uma variável de ambiente obrigatória e converte para int.

    Args:
        name: Nome da variável de ambiente.

    Returns:
        Valor da variável convertido para int.

    Raises:
        SystemExit: Se a variável não estiver definida ou for inválida.
    """
    v = os.getenv(name)
    if not v:
        logger.error("Variável de ambiente %s não definida", name)
        raise SystemExit(f"Faltou {name} no .env")
    if v.strip() != v:
        logger.warning("Variável de ambiente %s contém espaços em branco", name)
        v = v.strip()
    try:
        return int(v)
    except ValueError:
        logger.error("Variável de ambiente %s contém valor inválido: %s", name, v)
        raise SystemExit(f"{name} deve ser um número inteiro válido")


async def safe_sleep(seconds: float) -> None:
    """Sleep curto para reduzir risco de rate limit.

    Args:
        seconds: Tempo de espera em segundos. Deve ser um número não negativo.

    Raises:
        ValueError: Se seconds não for um número ou for negativo.
    """
    if not isinstance(seconds, (int, float)):
        raise ValueError("safe_sleep: seconds deve ser um número (int ou float)")
    if seconds < 0:
        raise ValueError("safe_sleep: seconds deve ser não negativo")

    if seconds > 0:
        logger.debug("Aguardando %.2fs antes da próxima operação", seconds)
    await asyncio.sleep(seconds)


def _session_db_path(base_dir: Path, session_name: str) -> Path:
    """Retorna o caminho esperado do arquivo SQLite da sessão."""
    filename = session_name if session_name.endswith(".session") else f"{session_name}.session"
    return base_dir / filename


def resolve_session_name(
    session_name: str | None, *, cwd: Path | None = None, home: Path | None = None
) -> str:
    """Resolve o nome/caminho de sessão para evitar novo login frequente.

    Regras:
    - Se `SESSION_NAME` for caminho absoluto, usa esse caminho.
    - Se `SESSION_NAME` tiver diretório relativo (ex.: `data/minha_sessao`),
      resolve relativo ao diretório atual.
    - Se for apenas nome simples (ex.: `session`), usa por padrão
      `~/.clean_telegram/<nome>` para manter a sessão estável entre execuções
      em diretórios diferentes.
    - Se existir sessão legada no diretório atual e não existir no novo local,
      migra automaticamente.
    """
    current_dir = cwd or Path.cwd()
    home_dir = home or Path.home()

    name = (session_name or "session").strip() or "session"
    path_candidate = Path(name).expanduser()
    has_directory_hint = "/" in name or "\\" in name

    if path_candidate.is_absolute() or has_directory_hint:
        resolved = (
            path_candidate if path_candidate.is_absolute() else (current_dir / path_candidate)
        )
        resolved.parent.mkdir(parents=True, exist_ok=True)
        return str(resolved)

    session_dir = home_dir / ".clean_telegram"
    session_dir.mkdir(parents=True, exist_ok=True)
    modern_session = _session_db_path(session_dir, name)
    legacy_session = _session_db_path(current_dir, name)

    if legacy_session.exists() and not modern_session.exists():
        shutil.copy2(legacy_session, modern_session)
        logger.info("Sessão migrada para %s", modern_session)

    return str(session_dir / name)
