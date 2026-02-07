"""CleanTelegram: script destrutivo para limpar conta Telegram via Telethon.

Apaga históricos de conversa (usuários/bots) e sai de grupos/canais.
Use com cuidado e teste primeiro com --dry-run.
"""

import argparse
import asyncio
import logging
import os
import sys

from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors import FloodWaitError, RPCError
from telethon.tl.functions.channels import LeaveChannelRequest
from telethon.tl.functions.messages import DeleteChatUserRequest, DeleteHistoryRequest
from telethon.tl.types import Channel, Chat, InputUserSelf, User

logger = logging.getLogger(__name__)


def env_int(name: str) -> int:
    """Lê uma variável de ambiente obrigatória e converte para int."""
    v = os.getenv(name)
    if not v:
        raise SystemExit(f"Faltou {name} no .env")
    return int(v)


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


async def main() -> None:
    """Entry-point assíncrono."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Apaga diálogos e sai de grupos/canais (Telethon)."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Não faz alterações; só imprime o que faria.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Não pedir confirmação interativa.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limita quantos diálogos processar (0 = todos).",
    )
    args = parser.parse_args()

    api_id = env_int("API_ID")
    api_hash = os.getenv("API_HASH")
    if not api_hash:
        raise SystemExit("Faltou API_HASH no .env")

    session_name = os.getenv("SESSION_NAME", "session")

    if not args.dry_run and not args.yes:
        print(
            "ATENÇÃO: isso vai apagar conversas e sair de grupos/canais.\n"
            "Digite 'APAGAR TUDO' para confirmar: ",
            end="",
            flush=True,
        )
        confirm = sys.stdin.readline().strip()
        if confirm != "APAGAR TUDO":
            print("Cancelado.")
            return

    async with TelegramClient(session_name, api_id, api_hash) as client:
        me = await client.get_me()
        logger.info("Logado como: %s (id=%s)", me.username or me.first_name, me.id)

        processed = 0
        async for d in client.iter_dialogs():
            if args.limit and processed >= args.limit:
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
                        dry_run=args.dry_run,
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

        logger.info("Concluído. Diálogos processados: %s", processed)


if __name__ == "__main__":
    asyncio.run(main())
