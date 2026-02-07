"""Funções para interação com cliente Telegram."""

import logging
from typing import Union

from telethon import TelegramClient
from telethon.errors import FloodWaitError, RPCError
from telethon.tl.functions.channels import LeaveChannelRequest
from telethon.tl.functions.messages import DeleteChatUserRequest, DeleteHistoryRequest
from telethon.tl.types import Channel, Chat, InputUserSelf, User

logger = logging.getLogger(__name__)


async def delete_dialog(
    client: TelegramClient, peer: Union[Channel, Chat, User, InputUserSelf], *, dry_run: bool
) -> None:
    """Apaga o histórico do diálogo (tenta revogar quando aplicável).

    Args:
        client: Instância do TelegramClient.
        peer: Entidade do diálogo.
        dry_run: Se True, não executa ações destrutivas.
    """
    if dry_run:
        return
    await client(DeleteHistoryRequest(peer=peer, max_id=0, just_clear=False, revoke=True))


async def leave_channel(client: TelegramClient, entity: Channel, *, dry_run: bool) -> None:
    """Sai de um canal/megagrupo (Channel).

    Args:
        client: Instância do TelegramClient.
        entity: Entidade do canal.
        dry_run: Se True, não executa ações destrutivas.
    """
    if dry_run:
        return
    await client(LeaveChannelRequest(entity))


async def leave_legacy_chat(client: TelegramClient, entity: Chat, *, dry_run: bool) -> None:
    """Sai de um grupo antigo (Chat).

    Telethon/Telegram têm diferenças entre Chat (grupo antigo) e Channel (canal/megagrupo).

    Args:
        client: Instância do TelegramClient.
        entity: Entidade do chat.
        dry_run: Se True, não executa ações destrutivas.
    """
    if dry_run:
        return

    # Remove o próprio usuário do chat legado.
    await client(DeleteChatUserRequest(chat_id=entity.id, user_id=InputUserSelf()))


async def process_dialog(
    client: TelegramClient,
    entity: Union[Channel, Chat, User],
    title: str,
    index: int,
    *,
    dry_run: bool,
) -> bool:
    """Processa um único diálogo, escolhendo a ação correta por tipo.

    Args:
        client: Instância do TelegramClient.
        entity: Entidade do diálogo.
        title: Nome do diálogo.
        index: Índice do diálogo para log.
        dry_run: Se True, não executa ações destrutivas.

    Returns:
        True se processado com sucesso, False se ocorreu erro.
    """
    try:
        if isinstance(entity, Channel):
            logger.info("[%s] SAIR de canal/megagrupo: %s", index, title)
            await leave_channel(client, entity, dry_run=dry_run)
            return True

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
            return True

        if isinstance(entity, User):
            logger.info("[%s] APAGAR conversa: %s", index, title)
            await delete_dialog(client, entity, dry_run=dry_run)
            return True

        logger.info("[%s] APAGAR diálogo (tipo desconhecido): %s", index, title)
        if not dry_run:
            await client.delete_dialog(entity)
        return True

    except FloodWaitError as e:
        logger.error(
            "Erro ao processar diálogo '%s': FloodWaitError (aguardar %ss): %s",
            title,
            e.seconds,
            e,
        )
        return False

    except RPCError as e:
        logger.error("Erro ao processar diálogo '%s': %s", title, e)
        return False

    except Exception:
        logger.exception("Erro inesperado ao processar diálogo '%s'", title)
        return False
