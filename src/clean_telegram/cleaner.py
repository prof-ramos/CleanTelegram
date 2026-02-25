"""Módulo de limpeza do CleanTelegram.

Contém as funções para apagar conversas e sair de grupos/canais.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable

from telethon import TelegramClient
from telethon.errors import FloodWaitError, RPCError
from telethon.tl.functions.channels import LeaveChannelRequest
from telethon.tl.functions.messages import DeleteChatUserRequest, DeleteHistoryRequest
from telethon.tl.types import Channel, Chat, InputUserSelf, User

logger = logging.getLogger(__name__)


@dataclass
class CleanFilter:
    """Filtros para limpeza seletiva de diálogos.

    Attributes:
        types: Tipos de entidade a processar. Valores: "user", "group", "channel".
               Lista vazia significa processar todos os tipos.
        before_date: Só processar diálogos com última mensagem antes desta data.
        name_pattern: Padrão de substring (case-insensitive) no nome do diálogo.
        whitelist: IDs (como string) ou usernames de entidades a NUNCA processar.
    """

    types: list[str] = field(default_factory=list)
    before_date: datetime | None = None
    name_pattern: str | None = None
    whitelist: list[str] = field(default_factory=list)


def _dialog_matches_filter(d: object, entity: object, title: str, f: CleanFilter) -> bool:
    """Retorna True se o diálogo deve ser processado segundo o filtro."""
    # Whitelist: pular se ID ou username estiver na lista
    entity_id = str(getattr(entity, "id", ""))
    entity_username = getattr(entity, "username", "") or ""
    if entity_id in f.whitelist or entity_username in f.whitelist or title in f.whitelist:
        return False

    # Filtro por tipo
    if f.types:
        if isinstance(entity, Channel):
            entity_type = "channel" if getattr(entity, "broadcast", False) else "group"
        elif isinstance(entity, Chat):
            entity_type = "group"
        elif isinstance(entity, User):
            entity_type = "user"
        else:
            entity_type = "unknown"

        if entity_type not in f.types:
            return False

    # Filtro por data (última mensagem do diálogo)
    if f.before_date is not None:
        last_msg_date = getattr(d, "date", None)
        if last_msg_date is not None:
            # Normalizar timezone para comparação
            if hasattr(last_msg_date, "tzinfo") and last_msg_date.tzinfo is not None:
                if f.before_date.tzinfo is None:
                    from datetime import timezone
                    compare_date = f.before_date.replace(tzinfo=timezone.utc)
                else:
                    compare_date = f.before_date
            else:
                compare_date = f.before_date.replace(tzinfo=None) if f.before_date.tzinfo else f.before_date
            if last_msg_date >= compare_date:
                return False

    # Filtro por padrão de nome
    if f.name_pattern:
        if f.name_pattern.lower() not in title.lower():
            return False

    return True


async def safe_sleep(seconds: float) -> None:
    """Sleep curto para reduzir risco de rate limit."""
    await asyncio.sleep(seconds)


async def delete_dialog(client: TelegramClient, peer, *, dry_run: bool) -> None:
    """Apaga o histórico do diálogo (tenta revogar quando aplicável)."""
    if dry_run:
        return
    await client(
        DeleteHistoryRequest(peer=peer, max_id=0, just_clear=False, revoke=True)
    )


async def leave_channel(
    client: TelegramClient, entity: Channel, *, dry_run: bool
) -> None:
    """Sai de um canal/megagrupo (Channel)."""
    if dry_run:
        return
    await client(LeaveChannelRequest(entity))


async def leave_legacy_chat(
    client: TelegramClient, entity: Chat, *, dry_run: bool
) -> None:
    """Sai de um grupo antigo (Chat).

    Telethon/Telegram têm diferenças entre Chat (grupo antigo) e Channel (canal/megagrupo).
    """
    if dry_run:
        return

    # Remove o próprio usuário do chat legado.
    await client(DeleteChatUserRequest(chat_id=entity.id, user_id=InputUserSelf()))


async def _process_dialog(
    client: TelegramClient,
    entity,
    title: str,
    index: int,
    *,
    dry_run: bool,
) -> None:
    """Processa um único diálogo, escolhendo a ação correta por tipo."""
    if isinstance(entity, Channel):
        logger.info("[%s] SAIR de canal/megagrupo: %s", index, title)
        await leave_channel(client, entity, dry_run=dry_run)
        return

    if isinstance(entity, Chat):
        logger.info("[%s] SAIR de grupo legado (Chat): %s", index, title)
        try:
            await leave_legacy_chat(client, entity, dry_run=dry_run)
        except RPCError:
            logger.warning(
                "Falha ao sair via DeleteChatUserRequest; tentando fallback delete_dialog: %s",
                title,
            )
            if not dry_run:
                await client.delete_dialog(entity)
        return

    if isinstance(entity, User):
        logger.info("[%s] APAGAR conversa: %s", index, title)
        await delete_dialog(client, entity, dry_run=dry_run)
        return

    logger.info("[%s] APAGAR diálogo (tipo desconhecido): %s", index, title)
    if not dry_run:
        await client.delete_dialog(entity)


async def clean_all_dialogs(
    client: TelegramClient,
    *,
    dry_run: bool,
    limit: int = 0,
    clean_filter: CleanFilter | None = None,
    on_floodwait: Callable[[str, int, int, int], None] | None = None,
) -> tuple[int, int]:
    """Limpa todos os diálogos (apaga conversas e sai de grupos/canais).

    Args:
        client: Cliente Telethon conectado.
        dry_run: Se True, não faz alterações (só imprime).
        limit: Limite de diálogos para processar (0 = todos).
        clean_filter: Filtros opcionais para limpeza seletiva.
        on_floodwait: Callback chamado ao encontrar FloodWait.
                      Assinatura: (dialog_name, wait_seconds, attempt, max_retries)

    Returns:
        Tupla (processados, ignorados_pelo_filtro).
    """
    processed = 0
    skipped_by_filter = 0
    f = clean_filter or CleanFilter()

    async for d in client.iter_dialogs():
        if limit and processed >= limit:
            break

        entity = d.entity
        title = (
            d.name
            or getattr(entity, "title", None)
            or getattr(entity, "first_name", None)
            or f"(id={getattr(entity, 'id', '?')})"
        )
        index = processed + 1

        # Aplicar filtros
        if not _dialog_matches_filter(d, entity, title, f):
            logger.debug("[%s] IGNORADO (filtro): %s", index, title)
            skipped_by_filter += 1
            continue

        # FloodWait retry (não pular o diálogo)
        max_retries = 5
        attempt = 0
        success = False
        while True:
            try:
                await _process_dialog(
                    client,
                    entity,
                    title,
                    index,
                    dry_run=dry_run,
                )
                await safe_sleep(0.35)
                success = True
                break

            except FloodWaitError as e:
                attempt += 1
                wait_s = max(5, int(getattr(e, "seconds", 0) or 0))
                logger.warning(
                    "Rate limit (FloodWait) em '%s'. Aguardando %ss (tentativa %s/%s)...",
                    title,
                    wait_s,
                    attempt,
                    max_retries,
                )
                if on_floodwait is not None:
                    on_floodwait(title, wait_s, attempt, max_retries)
                await asyncio.sleep(wait_s)
                if attempt >= max_retries:
                    logger.error("Max retries atingido; pulando '%s'.", title)
                    break

            except RPCError:
                logger.exception("RPCError em '%s'", title)
                break

            except Exception:
                logger.exception("Erro inesperado em '%s'", title)
                break

        # Só incrementa se processou com sucesso
        if success:
            processed += 1

    return processed, skipped_by_filter
