"""Módulo de limpeza do CleanTelegram.

Contém as funções para apagar conversas e sair de grupos/canais.
"""

import asyncio
import logging

from telethon import TelegramClient
from telethon.errors import FloodWaitError, RPCError
from telethon.tl.functions.channels import LeaveChannelRequest
from telethon.tl.functions.messages import DeleteChatUserRequest, DeleteHistoryRequest
from telethon.tl.types import Channel, Chat, InputUserSelf, User

logger = logging.getLogger(__name__)


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


async def leave_channel(client: TelegramClient, entity: Channel, *, dry_run: bool) -> None:
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

    if isinstance(entity, User) or getattr(entity, "bot", None) is not None:
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
) -> int:
    """Limpa todos os diálogos (apaga conversas e sai de grupos/canais).

    Args:
        client: Cliente Telethon conectado.
        dry_run: Se True, não faz alterações (só imprime).
        limit: Limite de diálogos para processar (0 = todos).

    Returns:
        Número de diálogos processados.
    """
    processed = 0

    async for d in client.iter_dialogs():
        if limit and processed >= limit:
            break

        title = d.name or "(sem nome)"
        entity = d.entity
        index = processed + 1

        # FloodWait retry (não pular o diálogo)
        max_retries = 5
        attempt = 0
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
                break

            except FloodWaitError as e:
                attempt += 1
                wait_s = int(getattr(e, "seconds", 0) or 0)
                logger.warning(
                    "Rate limit (FloodWait) em '%s'. Aguardando %ss (tentativa %s/%s)...",
                    title,
                    wait_s,
                    attempt,
                    max_retries,
                )
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

        processed += 1

    return processed
