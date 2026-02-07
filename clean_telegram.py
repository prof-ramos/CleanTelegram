import argparse
import asyncio
import os
import sys

from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors import FloodWaitError, RPCError
from telethon.tl.functions.channels import LeaveChannelRequest
from telethon.tl.functions.messages import DeleteHistoryRequest


def env_int(name: str) -> int:
    v = os.getenv(name)
    if not v:
        raise SystemExit(f"Faltou {name} no .env")
    return int(v)


async def safe_sleep(seconds: float):
    # Pequeno amortecedor para reduzir risco de rate limit
    await asyncio.sleep(seconds)


async def delete_dialog(client: TelegramClient, peer, dry_run: bool):
    if dry_run:
        return
    # DeleteHistoryRequest apaga o histórico do seu lado; revoke=True tenta revogar (quando aplicável)
    await client(DeleteHistoryRequest(peer=peer, max_id=0, just_clear=False, revoke=True))


async def leave_channel_or_group(client: TelegramClient, entity, dry_run: bool):
    if dry_run:
        return
    await client(LeaveChannelRequest(entity))


async def main():
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
        print(f"Logado como: {me.username or me.first_name} (id={me.id})")

        dialogs = []
        async for d in client.iter_dialogs():
            dialogs.append(d)
            if args.limit and len(dialogs) >= args.limit:
                break

        print(f"Diálogos encontrados: {len(dialogs)}")

        for i, d in enumerate(dialogs, start=1):
            title = d.name or "(sem nome)"
            entity = d.entity

            # Tipos comuns
            is_user = getattr(entity, "bot", None) is not None or entity.__class__.__name__ == "User"
            is_channel = entity.__class__.__name__ == "Channel"
            is_chat = entity.__class__.__name__ == "Chat"  # grupos antigos

            try:
                if is_channel or is_chat:
                    kind = "canal/grupo"
                    print(f"[{i}/{len(dialogs)}] SAIR de {kind}: {title}")
                    await leave_channel_or_group(client, entity, args.dry_run)
                elif is_user:
                    kind = "conversa"
                    print(f"[{i}/{len(dialogs)}] APAGAR {kind}: {title}")
                    await delete_dialog(client, entity, args.dry_run)
                else:
                    # fallback: tenta apagar o diálogo
                    print(f"[{i}/{len(dialogs)}] APAGAR diálogo (tipo desconhecido): {title}")
                    await delete_dialog(client, entity, args.dry_run)

                await safe_sleep(0.35)

            except FloodWaitError as e:
                wait_s = int(getattr(e, "seconds", 0) or 0)
                print(f"Rate limit (FloodWait). Aguardando {wait_s}s...")
                await asyncio.sleep(wait_s)

            except RPCError as e:
                print(f"RPCError em '{title}': {e.__class__.__name__}: {e}")

            except Exception as e:
                print(f"Erro inesperado em '{title}': {type(e).__name__}: {e}")

        print("Concluído.")


if __name__ == "__main__":
    asyncio.run(main())
