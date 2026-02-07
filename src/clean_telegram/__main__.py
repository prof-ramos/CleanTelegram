"""Entry-point para execução do CleanTelegram."""

import argparse
import asyncio
import logging
import os
import sys

import qrcode
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors import FloodWaitError, RPCError, SessionPasswordNeededError

from clean_telegram.client import process_dialog
from clean_telegram.utils import env_int, resolve_session_name, safe_sleep

logger = logging.getLogger(__name__)


def display_qr_code(url: str) -> None:
    """Exibe o QR code no terminal usando ASCII.

    Args:
        url: URL para codificar no QR code.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=1,
        border=2,
    )
    qr.add_data(url)
    qr.print_ascii(invert=True)
    print(f"\nURL: {url}\n")


async def login_with_qr(client: TelegramClient) -> bool:
    """Realiza login usando QR code.

    Args:
        client: Instância do TelegramClient.

    Returns:
        True se login foi bem-sucedido, False caso contrário.
    """
    logger.info("Iniciando login via QR code...")

    qr_login = await client.qr_login()

    print("\nEscaneie o QR code abaixo com o seu Telegram mobile:")
    print("(Telegram > Configurações > Dispositivos > Escanear QR Code)\n")

    while not qr_login.is_logged:
        display_qr_code(qr_login.url)

        try:
            logger.info("Aguardando leitura do QR code...")
            await asyncio.wait_for(qr_login.wait(), timeout=10)

        except asyncio.TimeoutError:
            # Timeout é esperado - o QR code expira e precisamos gerar outro
            logger.info("QR code expirado, gerando novo...")
            continue

        except SessionPasswordNeededError:
            print("\nVerificação em duas etapas (2FA) habilitada.")
            print("Por favor, use o login por telefone/código.")
            return False

        except Exception as e:
            logger.error("Erro durante login via QR code: %s", e)
            return False

    logger.info("Login via QR code realizado com sucesso!")
    return True


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
    parser.add_argument(
        "--qr-login",
        action="store_true",
        help="Usa login via QR code em vez de telefone/código.",
    )
    args = parser.parse_args()

    try:
        api_id = env_int("API_ID")
    except SystemExit:
        raise SystemExit("Faltou API_ID no .env ou valor inválido")

    api_hash = os.getenv("API_HASH")
    if not api_hash:
        raise SystemExit("Faltou API_HASH no .env")

    session_name = resolve_session_name(os.getenv("SESSION_NAME", "session"))

    # Se for login via QR code, usa uma sessão temporária
    if args.qr_login:
        # Remove extensão .session se existir para criar sessão temporária
        base_name = session_name.replace(".session", "")
        session_name = f"{base_name}_qr.session"

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
        # Login via QR code se solicitado
        if args.qr_login:
            logger.info("Modo de login via QR code ativado.")
            # Conecta o cliente antes de tentar QR login
            await client.connect()
            # Tenta fazer login via QR code
            success = await login_with_qr(client)
            if not success:
                logger.error("Falha no login via QR code. Encerrando.")
                return

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
                    await process_dialog(
                        client,
                        entity,
                        title,
                        index,
                        dry_run=args.dry_run,
                    )
                    await safe_sleep(0.35)
                    # Só incrementa se processou com sucesso
                    processed += 1
                    break

                except FloodWaitError as e:
                    attempt += 1
                    wait_s = int(e.seconds)
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

        logger.info("Concluído. Diálogos processados: %s", processed)


if __name__ == "__main__":
    asyncio.run(main())
