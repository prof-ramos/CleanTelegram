"""CLI module for CleanTelegram."""

import argparse
import asyncio
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors import RPCError

from .backup import backup_group_full, backup_group_with_media
from .cleaner import clean_all_dialogs
from .interactive import interactive_main
from .reports import (
    generate_all_reports,
    generate_contacts_report,
    generate_groups_channels_report,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AuthConfig:
    """Configuração de autenticação do cliente Telegram."""

    mode: Literal["user", "bot"]
    session_name: str
    bot_token: str | None = None


def env_int(name: str) -> int:
    """Lê uma variável de ambiente obrigatória e converte para int."""
    v = os.getenv(name)
    if not v:
        raise SystemExit(f"Faltou {name} no .env")
    try:
        return int(v)
    except ValueError:
        raise SystemExit(f"Valor inválido para {name}: '{v}' não é um inteiro válido")


def parse_args() -> argparse.Namespace:
    """Parse argumentos da linha de comando."""
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
        "-i",
        "--interactive",
        action="store_true",
        help="Modo interativo com menus visuais.",
    )

    # Opções de relatório
    parser.add_argument(
        "--report",
        choices=["groups", "contacts", "all"],
        help="Gera relatório no diretório relatorios/ (groups = grupos e canais)",
    )
    parser.add_argument(
        "--report-format",
        choices=["csv", "json", "txt"],
        default="csv",
        help="Formato do relatório (padrão: csv).",
    )
    parser.add_argument(
        "--report-output",
        type=str,
        default=None,
        help="Caminho do arquivo de relatório (opcional, usa padrão com timestamp se omitido).",
    )

    # Opções de backup
    parser.add_argument(
        "--backup-group",
        type=str,
        metavar="CHAT_ID",
        help="Faz backup completo de um grupo (mensagens + participantes).",
    )
    parser.add_argument(
        "--export-members",
        type=str,
        metavar="CHAT_ID",
        help="Exporta participantes de um grupo.",
    )
    parser.add_argument(
        "--export-messages",
        type=str,
        metavar="CHAT_ID",
        help="Exporta mensagens de um grupo.",
    )
    parser.add_argument(
        "--backup-format",
        choices=["json", "csv", "both"],
        default="json",
        help="Formato do backup (padrão: json).",
    )
    parser.add_argument(
        "--backup-output",
        type=str,
        default="backups",
        help="Diretório para arquivos de backup (padrão: backups/).",
    )
    parser.add_argument(
        "--download-media",
        action="store_true",
        help="Baixa arquivos de mídia do grupo (junto com --backup-group).",
    )
    parser.add_argument(
        "--media-types",
        type=str,
        default=None,
        help="Tipos de mídia para baixar (separados por vírgula: photo,video,document,audio,voice,sticker,gif).",
    )
    parser.add_argument(
        "--backup-to-cloud",
        action="store_true",
        help="Envia arquivos de backup para Cloud Chat (Saved Messages).",
    )
    parser.add_argument(
        "--max-concurrent-downloads",
        type=int,
        default=5,
        help="Máximo de downloads paralelos (padrão: 5).",
    )

    return parser.parse_args()


def resolve_auth_config() -> AuthConfig:
    """Resolve modo de autenticação (bot ou usuário) com base no ambiente."""
    bot_token = os.getenv("BOT_TOKEN")
    if bot_token:
        bot_session_name = os.getenv("BOT_SESSION_NAME", "bot_session")
        return AuthConfig(
            mode="bot",
            session_name=bot_session_name,
            bot_token=bot_token,
        )

    session_name = os.getenv("SESSION_NAME", "session")
    return AuthConfig(mode="user", session_name=session_name)


def create_client() -> tuple[TelegramClient, AuthConfig]:
    """Cria cliente Telegram e metadados de autenticação."""
    api_id = env_int("API_ID")
    api_hash = os.getenv("API_HASH")
    if not api_hash:
        raise SystemExit("Faltou API_HASH no .env")

    auth_config = resolve_auth_config()
    client = TelegramClient(auth_config.session_name, api_id, api_hash)
    return client, auth_config


async def start_client(client: TelegramClient, auth_config: AuthConfig) -> None:
    """Inicializa sessão do cliente conforme o modo de autenticação."""
    if auth_config.mode == "bot":
        await client.start(bot_token=auth_config.bot_token)
        return

    await client.start()


def confirm_action() -> bool:
    """Pede confirmação do usuário antes de executar ação destrutiva."""
    print(
        "ATENÇÃO: isso vai apagar conversas e sair de grupos/canais.\n"
        "Digite 'APAGAR TUDO' para confirmar: ",
        end="",
        flush=True,
    )
    confirm = sys.stdin.readline().strip()
    return confirm == "APAGAR TUDO"


def _get_timestamp() -> str:
    """Gera timestamp para nomes de arquivos."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def warn_bot_permissions(
    *,
    auth_config: AuthConfig,
    is_clean_mode: bool,
    is_backup_mode: bool,
) -> None:
    """Exibe aviso de permissões quando operação sensível roda em modo bot."""
    if auth_config.mode != "bot":
        return

    if not is_clean_mode and not is_backup_mode:
        return

    logger.warning(
        "Modo bot ativo: operações de limpeza/backup exigem permissões administrativas "
        "no chat (ex.: apagar mensagens, remover usuários, acessar histórico)."
    )


def format_rpc_error(error: RPCError, auth_config: AuthConfig) -> str:
    """Converte RPCError para mensagem amigável ao usuário."""
    if auth_config.mode == "bot":
        return (
            "Falha em modo bot. Verifique se o bot foi adicionado ao chat e se possui "
            "as permissões necessárias para a ação solicitada. "
            f"Detalhe Telegram: {error}"
        )

    return f"Erro da API do Telegram: {error}"


async def run_report(args: argparse.Namespace, client: TelegramClient) -> None:
    """Executa geração de relatórios conforme argumentos."""
    me = await client.get_me()
    logger.info(
        "Logado como: %s (id=%s)",
        me.username or me.first_name,
        me.id,
    )

    report_type = args.report
    output_format = args.report_format
    output_path = args.report_output

    logger.info(
        "Gerando relatório: %s (formato: %s)",
        report_type,
        output_format,
    )

    if report_type == "all":
        # Gerar todos os relatórios
        results = await generate_all_reports(client, output_format=output_format)
        for report_name, path in results.items():
            logger.info("Relatório '%s' gerado: %s", report_name, path)
    elif report_type == "groups":
        # Grupos e canais são tratados juntos
        path = await generate_groups_channels_report(
            client,
            output_path=output_path,
            output_format=output_format,
        )
        logger.info("Relatório de grupos/canais gerado: %s", path)
    elif report_type == "contacts":
        path = await generate_contacts_report(
            client,
            output_path=output_path,
            output_format=output_format,
        )
        logger.info("Relatório de contatos gerado: %s", path)


async def run_clean(args: argparse.Namespace, client: TelegramClient) -> None:
    """Executa limpeza de diálogos."""
    me = await client.get_me()
    logger.info(
        "Logado como: %s (id=%s)",
        me.username or me.first_name,
        me.id,
    )

    processed = await clean_all_dialogs(
        client,
        dry_run=args.dry_run,
        limit=args.limit,
    )

    logger.info("Concluído. Diálogos processados: %s", processed)


async def run_backup(args: argparse.Namespace, client: TelegramClient) -> None:
    """Executa backup de grupo ou exportação de dados."""
    me = await client.get_me()
    logger.info(
        "Logado como: %s (id=%s)",
        me.username or me.first_name,
        me.id,
    )

    # Determinar o chat alvo
    chat_id = args.backup_group or args.export_members or args.export_messages
    if not chat_id:
        logger.error("Nenhum chat especificado para backup")
        return

    # Resolver a entidade do chat
    try:
        entity = await client.get_entity(chat_id)
    except Exception as e:
        logger.error(f"Erro ao resolver chat '{chat_id}': {e}")
        return

    chat_title = getattr(entity, 'title', str(entity.id))
    logger.info(f"Processando chat: {chat_title}")

    output_dir = args.backup_output
    output_format = args.backup_format

    # Processar tipos de mídia se especificados
    media_types = None
    if args.media_types:
        media_types = args.media_types.split(',')

    # Backup completo
    if args.backup_group:
        if args.download_media:
            logger.info(f"Fazendo backup completo COM MÍDIA no formato '{output_format}'...")
            results = await backup_group_with_media(
                client, entity, output_dir, output_format,
                download_media=True,
                media_types=media_types,
                send_to_cloud=args.backup_to_cloud,
                max_concurrent_downloads=args.max_concurrent_downloads,
            )
        else:
            logger.info(f"Fazendo backup completo no formato '{output_format}'...")
            # Usar backup_group_with_media mesmo sem mídia para suportar send_to_cloud
            results = await backup_group_with_media(
                client, entity, output_dir, output_format,
                download_media=False,
                send_to_cloud=args.backup_to_cloud,
                max_concurrent_downloads=args.max_concurrent_downloads,
            )

        logger.info(f"Backup concluído:")
        if "messages_count" in results:
            logger.info(f"  • Mensagens: {results['messages_count']}")
        if "participants_count" in results:
            logger.info(f"  • Participantes: {results['participants_count']}")
        if "media" in results:
            logger.info(f"  • Arquivos de mídia: {results['media']['total']} baixados")
            for media_type, count in results['media'].items():
                if media_type != 'total' and count > 0:
                    logger.info(f"    - {media_type}: {count}")
        if "cloud_backup" in results and results["cloud_backup"]:
            logger.info(f"  • Cloud Chat: {len(results.get('cloud_files', []))} arquivo(s) enviado(s) para Saved Messages")

        if "messages_json" in results:
            logger.info(f"  • Mensagens JSON: {results['messages_json']}")
        if "participants_json" in results:
            logger.info(f"  • Participantes JSON: {results['participants_json']}")

    # Exportar apenas participantes
    elif args.export_members:
        from .backup import export_participants_to_json, export_participants_to_csv

        timestamp = _get_timestamp()
        safe_name = "".join(c for c in chat_title if c.isalnum() or c in (' ', '-', '_')).strip()

        if output_format in ("json", "both"):
            output_path = f"{output_dir}/{safe_name}_participants_{timestamp}.json"
            count = await export_participants_to_json(client, entity, output_path)
            logger.info(f"Participantes exportados (JSON): {count} -> {output_path}")

        if output_format in ("csv", "both"):
            output_path = f"{output_dir}/{safe_name}_participants_{timestamp}.csv"
            count = await export_participants_to_csv(client, entity, output_path)
            logger.info(f"Participantes exportados (CSV): {count} -> {output_path}")

    # Exportar apenas mensagens
    elif args.export_messages:
        from .backup import export_messages_to_json, export_messages_to_csv

        timestamp = _get_timestamp()
        safe_name = "".join(c for c in chat_title if c.isalnum() or c in (' ', '-', '_')).strip()

        if output_format in ("json", "both"):
            output_path = f"{output_dir}/{safe_name}_messages_{timestamp}.json"
            count = await export_messages_to_json(client, entity, output_path)
            logger.info(f"Mensagens exportadas (JSON): {count} -> {output_path}")

        if output_format in ("csv", "both"):
            output_path = f"{output_dir}/{safe_name}_messages_{timestamp}.csv"
            count = await export_messages_to_csv(client, entity, output_path)
            logger.info(f"Mensagens exportadas (CSV): {count} -> {output_path}")


async def main() -> None:
    """Entry-point assíncrono."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    load_dotenv()
    args = parse_args()

    client, auth_config = create_client()
    logger.info(
        "Autenticação selecionada: %s (session=%s)",
        auth_config.mode,
        auth_config.session_name,
    )

    # Modo interativo tem precedência
    if args.interactive:
        async with client:
            await start_client(client, auth_config)
            await interactive_main(client)
        return

    # Verificar se é modo backup (não precisa de confirmação)
    is_backup_mode = (
        args.backup_group is not None
        or args.export_members is not None
        or args.export_messages is not None
    )

    # Verificar se é modo relatório (não precisa de confirmação)
    is_report_mode = args.report is not None
    is_clean_mode = not is_backup_mode and not is_report_mode

    if not is_backup_mode and not is_report_mode and not args.dry_run and not args.yes:
        if not confirm_action():
            print("Cancelado.")
            return

    warn_bot_permissions(
        auth_config=auth_config,
        is_clean_mode=is_clean_mode,
        is_backup_mode=is_backup_mode,
    )

    async with client:
        await start_client(client, auth_config)
        try:
            if is_backup_mode:
                await run_backup(args, client)
            elif is_report_mode:
                await run_report(args, client)
            else:
                await run_clean(args, client)
        except RPCError as error:
            logger.error(format_rpc_error(error, auth_config))


if __name__ == "__main__":
    asyncio.run(main())
