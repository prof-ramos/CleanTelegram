"""Modo interativo para o CLI do CleanTelegram usando Questionary.

Oferece menus de seleção bonitos e intuitivos para ações, tipos de relatório e formatos,
semelhante a ferramentas como Claude Code e Mole.
"""

import argparse
import logging
from datetime import datetime

import questionary
from telethon import TelegramClient

from .backup import backup_group_with_media
from .cleaner import CleanFilter, clean_all_dialogs
from .config import CleanTelegramConfig, load_config, save_config
from .reports import (
    generate_all_reports,
    generate_contacts_report,
    generate_groups_channels_report,
    validate_output_path,
)
from .ui import (
    CUSTOM_STYLE,
    console,
    print_error,
    print_floodwait,
    print_info,
    print_stats_table,
    print_success,
    print_tip,
    print_warning,
    spinner,
    suppress_telethon_logs,
)

logger = logging.getLogger(__name__)


async def interactive_main(
    client: TelegramClient,
    args: argparse.Namespace | None = None,
) -> None:
    """Menu interativo principal.

    Args:
        client: Cliente Telethon conectado.
        args: Argumentos CLI opcionais para pré-configurar o modo interativo.
    """
    # Histórico de ações da sessão atual
    session_log: list[dict] = []

    # Se args passou --report ou --backup-group, pular direto para o fluxo correspondente
    if args is not None:
        if getattr(args, "report", None):
            await interactive_reports(client)
            return
        if getattr(args, "backup_group", None):
            await interactive_backup(client, prefill_chat=args.backup_group)
            return

    while True:
        me = await client.get_me()
        username = me.username or me.first_name

        # Menu principal
        with suppress_telethon_logs():
            action = await questionary.select(
                f"🚀 CleanTelegram — Logado como: {username} (id={me.id})\n"
                "O que você deseja fazer?",
                choices=[
                    questionary.Choice(
                        "🧹 Limpar conta",
                        value="clean",
                        description="Apaga conversas e sai de grupos/canais",
                    ),
                    questionary.Choice(
                        "📊 Gerar relatórios",
                        value="reports",
                        description="Exporta grupos, canais e contatos",
                    ),
                    questionary.Choice(
                        "📦 Backup de grupo",
                        value="backup",
                        description="Faz backup de mensagens e participantes",
                    ),
                    questionary.Choice(
                        "⚙️  Ver estatísticas",
                        value="stats",
                        description="Mostra informações da conta",
                    ),
                    questionary.Choice(
                        "🔧 Configurações",
                        value="settings",
                        description="Whitelist, diretórios padrão e preferências",
                    ),
                    questionary.Choice("🚪 Sair", value="exit"),
                ],
                style=CUSTOM_STYLE,
            ).ask_async()

        if action is None or action == "exit":
            # Mostrar resumo da sessão antes de sair
            if session_log:
                console.print()
                print_stats_table(
                    "Resumo da Sessão",
                    {
                        f"{i + 1}. {entry['action']} ({entry['timestamp'][11:16]})": entry["result"]
                        for i, entry in enumerate(session_log)
                    },
                )
            console.print("\n👋 Até logo!")
            break
        elif action == "clean":
            result = await interactive_clean(client, args=args)
            session_log.append({
                "action": "Limpeza",
                "timestamp": datetime.now().isoformat(),
                "result": result,
            })
        elif action == "reports":
            result = await interactive_reports(client)
            session_log.append({
                "action": "Relatório",
                "timestamp": datetime.now().isoformat(),
                "result": result,
            })
        elif action == "backup":
            result = await interactive_backup(client)
            session_log.append({
                "action": "Backup",
                "timestamp": datetime.now().isoformat(),
                "result": result,
            })
        elif action == "stats":
            await interactive_stats(client)
            session_log.append({
                "action": "Estatísticas",
                "timestamp": datetime.now().isoformat(),
                "result": "ok",
            })
        elif action == "settings":
            await interactive_settings(client)
            session_log.append({
                "action": "Configurações",
                "timestamp": datetime.now().isoformat(),
                "result": "ok",
            })

        # Pausa antes de voltar ao menu (apenas se não saiu)
        if action != "exit":
            await questionary.press_any_key_to_continue(
                "\nPressione qualquer tecla para continuar..."
            ).ask_async()


async def interactive_clean(
    client: TelegramClient,
    args: argparse.Namespace | None = None,
) -> str:
    """Fluxo interativo de limpeza.

    Returns:
        String descrevendo o resultado ("concluído", "cancelado", "erro").
    """
    cfg = load_config()

    # Aviso inicial
    confirm = await questionary.confirm(
        "⚠️  ATENÇÃO: Esta ação é DESTRUTIVA e IRREVERSÍVEL!\n"
        "   • Apagará TODAS as conversas\n"
        "   • Você sairá de TODOS os grupos e canais\n\n"
        "Deseja continuar?",
        default=False,
        style=CUSTOM_STYLE,
    ).ask_async()

    if not confirm:
        console.print("\n❌ Operação cancelada.")
        return "cancelado"

    # Whitelist
    use_whitelist = await questionary.confirm(
        "Excluir algum chat/grupo da limpeza (whitelist)?",
        default=bool(cfg.clean_whitelist),
        style=CUSTOM_STYLE,
    ).ask_async()

    whitelist = list(cfg.clean_whitelist)
    if use_whitelist:
        whitelist_input = await questionary.text(
            "Digite IDs ou @usernames separados por vírgula (deixe vazio para usar whitelist salva)",
            default=", ".join(cfg.clean_whitelist) if cfg.clean_whitelist else "",
            style=CUSTOM_STYLE,
        ).ask_async()
        if whitelist_input and whitelist_input.strip():
            whitelist = [x.strip() for x in whitelist_input.split(",") if x.strip()]

    # Modo dry-run
    default_dry = getattr(args, "dry_run", cfg.default_dry_run) if args else cfg.default_dry_run
    dry_run = await questionary.confirm(
        "Executar em modo dry-run (simulação)?",
        default=default_dry,
        style=CUSTOM_STYLE,
    ).ask_async()

    # Confirmação adicional se não for dry-run
    if not dry_run:
        confirm_real = await questionary.confirm(
            "🔴 Confirma que deseja EXECUTAR de verdade?",
            default=False,
            style=CUSTOM_STYLE,
        ).ask_async()

        if not confirm_real:
            console.print("\n❌ Operação cancelada.")
            return "cancelado"

    # Limite de diálogos
    default_limit = getattr(args, "limit", cfg.default_dialog_limit) if args else cfg.default_dialog_limit
    limit_choice = await questionary.select(
        "Quantos diálogos processar?",
        choices=[
            questionary.Choice("Todos os diálogos", value=0),
            questionary.Choice("Apenas os primeiros 10", value=10),
            questionary.Choice("Apenas os primeiros 50", value=50),
            questionary.Choice("Cancelar", value=None),
        ],
        default=questionary.Choice("Todos os diálogos", value=0) if default_limit == 0 else None,
        style=CUSTOM_STYLE,
    ).ask_async()

    if limit_choice is None:
        console.print("\n❌ Operação cancelada.")
        return "cancelado"

    # Executar
    console.print(f"\n{'🔍 Simulando' if dry_run else '🚀 Executando'} limpeza...")

    try:
        clean_filter = CleanFilter(whitelist=whitelist)
        processed, skipped = await clean_all_dialogs(
            client,
            dry_run=dry_run,
            limit=limit_choice,
            clean_filter=clean_filter,
            on_floodwait=print_floodwait,
        )

        if dry_run:
            print_success(f"Simulação concluída! {processed} diálogos seriam processados.")
        else:
            print_success(f"Limpeza concluída! {processed} diálogos processados.")

        if skipped > 0:
            print_info(f"{skipped} diálogo(s) ignorados pela whitelist/filtro.")

        return "concluído"

    except Exception as e:
        print_error(
            f"Erro durante limpeza ({type(e).__name__}): {e}",
            hint="Tente rodar com dry-run primeiro para identificar diálogos problemáticos.",
        )
        logger.exception("Erro na limpeza interativa")
        return "erro"


async def interactive_reports(client: TelegramClient) -> str:
    """Fluxo interativo de geração de relatórios.

    Returns:
        String descrevendo o resultado.
    """
    cfg = load_config()

    # Tipo de relatório
    report_type = await questionary.select(
        "Que tipo de relatório deseja gerar?",
        choices=[
            questionary.Choice("📁 Grupos e Canais", value="groups"),
            questionary.Choice("👥 Contatos", value="contacts"),
            questionary.Choice("📦 Todos os relatórios", value="all"),
        ],
        style=CUSTOM_STYLE,
    ).ask_async()

    if not report_type:
        return "cancelado"

    # Formato
    output_format = await questionary.select(
        "Em qual formato?",
        choices=[
            questionary.Choice("📊 CSV (planilha)", value="csv"),
            questionary.Choice("📋 JSON (estruturado)", value="json"),
            questionary.Choice("📝 TXT (texto simples)", value="txt"),
        ],
        default=questionary.Choice(f"📊 CSV (planilha)", value=cfg.default_report_format)
        if cfg.default_report_format == "csv"
        else None,
        style=CUSTOM_STYLE,
    ).ask_async()

    if not output_format:
        return "cancelado"

    # Ordenação (apenas para relatórios individuais)
    sort_by = None
    sort_reverse = False
    if report_type != "all":
        sort_choice = await questionary.select(
            "Ordenar por?",
            choices=[
                questionary.Choice("Sem ordenação", value=None),
                questionary.Choice("Nome (A-Z)", value=("title" if report_type == "groups" else "name", False)),
                questionary.Choice("Nome (Z-A)", value=("title" if report_type == "groups" else "name", True)),
                questionary.Choice("Participantes (maior)", value=("participants_count", True)) if report_type == "groups" else questionary.Choice("ID", value=("id", False)),
            ],
            style=CUSTOM_STYLE,
        ).ask_async()

        if sort_choice:
            sort_by, sort_reverse = sort_choice

    # Caminho personalizado
    output_path = None
    if report_type != "all":
        custom_path = await questionary.confirm(
            "Deseja especificar caminho do arquivo?",
            default=False,
            style=CUSTOM_STYLE,
        ).ask_async()

        if custom_path:
            output_path = await questionary.path(
                "Caminho do arquivo (deixe vazio para padrão)",
                style=CUSTOM_STYLE,
            ).ask_async()

            if output_path:
                is_valid, err = validate_output_path(output_path)
                if not is_valid:
                    print_error(f"Caminho inválido: {err}")
                    return "erro"
            else:
                output_path = None

    # Gerar relatório
    console.print(f"\n📊 Gerando relatório: {report_type} ({output_format})...")

    try:
        if report_type == "all":
            results = await generate_all_reports(client, output_format=output_format)
            print_success("Relatórios gerados:")
            for name, path in results.items():
                console.print(f"   • {name}: {path}")
        elif report_type == "groups":
            path = await generate_groups_channels_report(
                client,
                output_path=output_path,
                output_format=output_format,
                sort_by=sort_by,
                sort_reverse=sort_reverse,
            )
            print_success(f"Relatório de grupos/canais: {path}")
        else:  # contacts
            path = await generate_contacts_report(
                client,
                output_path=output_path,
                output_format=output_format,
                sort_by=sort_by,
                sort_reverse=sort_reverse,
            )
            print_success(f"Relatório de contatos: {path}")

        return "concluído"

    except PermissionError as e:
        print_error(f"Sem permissão para escrever o relatório: {e}")
        return "erro"
    except Exception as e:
        print_error(
            f"Erro ao gerar relatório ({type(e).__name__}): {e}",
            hint="Verifique a conexão com o Telegram e as permissões do diretório de saída.",
        )
        logger.exception("Erro na geração de relatório")
        return "erro"


async def interactive_stats(client: TelegramClient) -> None:
    """Mostra estatísticas detalhadas da conta."""
    from telethon.tl.types import Channel, Chat, User

    me = await client.get_me()

    # Estatísticas do usuário
    console.print()
    print_stats_table(
        "📊 Conta",
        {
            "👤 Nome": f"{me.first_name} {me.last_name or ''}".strip(),
            "📱 Username": f"@{me.username}" if me.username else "(não definido)",
            "🆔 ID": me.id,
            "✅ Verificado": "Sim" if getattr(me, "verified", False) else "Não",
            "🤖 Bot": "Sim" if getattr(me, "bot", False) else "Não",
        },
    )

    # Contagem detalhada de diálogos
    counts: dict[str, int] = {
        "total": 0,
        "supergroups": 0,
        "channels": 0,
        "legacy_groups": 0,
        "users": 0,
        "bots": 0,
        "unread": 0,
    }

    with spinner("⏳ Contando diálogos..."):
        async for dialog in client.iter_dialogs():
            counts["total"] += 1
            entity = dialog.entity

            if getattr(dialog, "unread_count", 0) > 0:
                counts["unread"] += 1

            if isinstance(entity, Channel):
                if getattr(entity, "broadcast", False):
                    counts["channels"] += 1
                else:
                    counts["supergroups"] += 1
            elif isinstance(entity, Chat):
                counts["legacy_groups"] += 1
            elif isinstance(entity, User):
                if getattr(entity, "bot", False):
                    counts["bots"] += 1
                else:
                    counts["users"] += 1

    console.print()
    print_stats_table(
        "📁 Diálogos",
        {
            "Total": counts["total"],
            "Supergrupos": counts["supergroups"],
            "Canais broadcast": counts["channels"],
            "Grupos legados": counts["legacy_groups"],
            "Usuários (DM)": counts["users"],
            "Bots": counts["bots"],
            "Com mensagens não lidas": counts["unread"],
        },
    )

    print_tip("Use 'Gerar relatórios' para exportar esses dados.")


async def interactive_backup(
    client: TelegramClient,
    prefill_chat: str | None = None,
) -> str:
    """Fluxo interativo de backup de grupo.

    Args:
        prefill_chat: ID/username pré-preenchido (vindo do CLI).

    Returns:
        String descrevendo o resultado.
    """
    cfg = load_config()

    # Perguntar qual grupo/canal fazer backup
    if prefill_chat:
        chat_id = prefill_chat
    else:
        chat_id = await questionary.text(
            "Digite o ID, username ou link do grupo/canal (ex: @grupo, -1001234567890)",
            style=CUSTOM_STYLE,
        ).ask_async()

    if not chat_id:
        console.print("\n❌ Operação cancelada.")
        return "cancelado"

    # Tentar resolver a entidade
    try:
        entity = await client.get_entity(chat_id)
    except Exception as e:
        print_error(
            f"Erro ao encontrar chat '{chat_id}': {type(e).__name__}: {e}",
            hint="Verifique se o ID/username está correto e se você tem acesso ao chat.",
        )
        return "erro"

    chat_title = getattr(entity, "title", str(entity.id))
    console.print(f"\n📁 Grupo encontrado: {chat_title}")

    # Perguntar formato
    output_format = await questionary.select(
        "Em qual formato exportar?",
        choices=[
            questionary.Choice("📋 JSON", value="json"),
            questionary.Choice("📊 CSV", value="csv"),
            questionary.Choice("📦 Ambos (JSON + CSV)", value="both"),
        ],
        style=CUSTOM_STYLE,
    ).ask_async()

    if not output_format:
        console.print("\n❌ Operação cancelada.")
        return "cancelado"

    # Backup incremental
    incremental = await questionary.confirm(
        "Backup incremental? (busca apenas mensagens novas desde o último backup)",
        default=False,
        style=CUSTOM_STYLE,
    ).ask_async()

    # Perguntar se quer baixar mídia
    download_media = await questionary.confirm(
        "Baixar arquivos de mídia (fotos, vídeos, documentos)?",
        default=False,
        style=CUSTOM_STYLE,
    ).ask_async()

    # Tipos de mídia
    media_types = None
    if download_media:
        download_all = await questionary.confirm(
            "Baixar TODOS os tipos de mídia?",
            default=True,
            style=CUSTOM_STYLE,
        ).ask_async()

        if not download_all:
            selected = await questionary.checkbox(
                "Selecione os tipos de mídia (Espaço para marcar, Enter para confirmar):",
                choices=[
                    questionary.Choice("📷 Fotos", value="photo", checked=True),
                    questionary.Choice("🎥 Vídeos", value="video", checked=True),
                    questionary.Choice("📄 Documentos", value="document", checked=True),
                    questionary.Choice("🎵 Áudio", value="audio", checked=False),
                    questionary.Choice("🎤 Voice notes", value="voice", checked=False),
                    questionary.Choice("😄 Stickers", value="sticker", checked=False),
                    questionary.Choice("🎞️ GIFs", value="gif", checked=False),
                ],
                style=CUSTOM_STYLE,
            ).ask_async()

            media_types = selected if selected else None
            if not media_types:
                print_warning("Nenhum tipo selecionado — baixando todos os tipos.")

    # Enviar para Cloud Chat
    send_to_cloud = await questionary.confirm(
        "☁️ Enviar backup para Cloud Chat (Saved Messages)?",
        default=False,
        style=CUSTOM_STYLE,
    ).ask_async()

    # Confirmação final
    console.print("\n📋 Resumo do backup:")
    console.print(f"   • Grupo: {chat_title}")
    console.print(f"   • Formato: {output_format}")
    console.print(f"   • Incremental: {'Sim' if incremental else 'Não'}")
    if download_media:
        console.print(
            f"   • Mídia: {'todos os tipos' if not media_types else ', '.join(media_types)}"
        )
    else:
        console.print("   • Mídia: Não")
    console.print(f"   • Cloud Chat: {'Sim' if send_to_cloud else 'Não'}")

    confirm = await questionary.confirm(
        "\nIniciar backup?",
        default=True,
        style=CUSTOM_STYLE,
    ).ask_async()

    if not confirm:
        console.print("\n❌ Operação cancelada.")
        return "cancelado"

    console.print("\n📦 Iniciando backup...")

    try:
        from telethon.errors import ChatAdminRequiredError, FloodWaitError

        results = await backup_group_with_media(
            client,
            entity,
            cfg.default_backup_dir,
            output_format,
            download_media=download_media,
            media_types=media_types,
            send_to_cloud=send_to_cloud,
            incremental=incremental,
        )

        print_success("Backup concluído!")
        console.print(f"   • Mensagens: {results.get('messages_count', 0)}")
        console.print(f"   • Participantes: {results.get('participants_count', 0)}")

        if results.get("participants_error"):
            print_warning(
                f"Participantes: {results['participants_error']}"
            )

        if "media" in results:
            console.print(f"   • Arquivos de mídia: {results['media']['total']} baixados")
            for media_type, count in results["media"].items():
                if media_type != "total" and count > 0:
                    console.print(f"     - {media_type}: {count}")

        if "cloud_backup" in results and results["cloud_backup"]:
            console.print(
                f"   • ☁️ Cloud Chat: {len(results.get('cloud_files', []))} arquivo(s) enviado(s)"
            )

        if "messages_json" in results or "messages_csv" in results:
            console.print("\n📁 Arquivos salvos:")
            for key in ("messages_json", "participants_json", "messages_csv", "participants_csv"):
                if key in results:
                    console.print(f"   • {key}: {results[key]}")

        return "concluído"

    except ChatAdminRequiredError:
        print_error("Você não tem permissão de administrador neste grupo para exportar participantes.")
        print_tip("O backup de mensagens foi salvo. Para exportar participantes, peça ao admin do grupo.")
        return "parcial"
    except FloodWaitError as e:
        wait = getattr(e, "seconds", "?")
        print_error(f"Rate limit do Telegram. Aguarde {wait} segundos e tente novamente.")
        return "erro"
    except Exception as e:
        print_error(
            f"Erro durante backup ({type(e).__name__}): {e}",
            hint="Verifique a conexão com o Telegram e tente novamente.",
        )
        logger.exception("Erro no backup interativo")
        return "erro"


async def interactive_settings(client: TelegramClient) -> None:
    """Menu de configurações persistentes."""
    cfg = load_config()

    setting = await questionary.select(
        "🔧 Configurações — O que deseja alterar?",
        choices=[
            questionary.Choice(
                f"📋 Whitelist de limpeza ({len(cfg.clean_whitelist)} item(ns))",
                value="whitelist",
            ),
            questionary.Choice(
                f"📂 Diretório de backup: {cfg.default_backup_dir}",
                value="backup_dir",
            ),
            questionary.Choice(
                f"📊 Formato padrão de relatório: {cfg.default_report_format}",
                value="report_format",
            ),
            questionary.Choice(
                f"🔍 Dry-run por padrão: {'Sim' if cfg.default_dry_run else 'Não'}",
                value="dry_run",
            ),
            questionary.Choice("↩️  Voltar", value=None),
        ],
        style=CUSTOM_STYLE,
    ).ask_async()

    if setting is None:
        return

    if setting == "whitelist":
        await _settings_edit_whitelist(cfg)

    elif setting == "backup_dir":
        new_dir = await questionary.path(
            "Novo diretório de backup:",
            default=cfg.default_backup_dir,
            style=CUSTOM_STYLE,
        ).ask_async()
        if new_dir:
            cfg.default_backup_dir = new_dir
            save_config(cfg)
            print_success(f"Diretório de backup atualizado: {new_dir}")

    elif setting == "report_format":
        fmt = await questionary.select(
            "Formato padrão de relatório:",
            choices=["csv", "json", "txt"],
            default=cfg.default_report_format,
            style=CUSTOM_STYLE,
        ).ask_async()
        if fmt:
            cfg.default_report_format = fmt
            save_config(cfg)
            print_success(f"Formato padrão de relatório: {fmt}")

    elif setting == "dry_run":
        new_val = await questionary.confirm(
            "Ativar dry-run por padrão?",
            default=cfg.default_dry_run,
            style=CUSTOM_STYLE,
        ).ask_async()
        cfg.default_dry_run = new_val
        save_config(cfg)
        print_success(f"Dry-run padrão: {'Sim' if new_val else 'Não'}")


async def _settings_edit_whitelist(cfg: CleanTelegramConfig) -> None:
    """Submenu de edição da whitelist de limpeza."""
    action = await questionary.select(
        f"Whitelist atual: {cfg.clean_whitelist or '(vazia)'}",
        choices=[
            questionary.Choice("➕ Adicionar item", value="add"),
            questionary.Choice("➖ Remover item", value="remove") if cfg.clean_whitelist else None,
            questionary.Choice("🗑️  Limpar tudo", value="clear") if cfg.clean_whitelist else None,
            questionary.Choice("↩️  Voltar", value=None),
        ],
        style=CUSTOM_STYLE,
    ).ask_async()

    if action == "add":
        item = await questionary.text(
            "ID ou @username para adicionar à whitelist:",
            style=CUSTOM_STYLE,
        ).ask_async()
        if item and item.strip():
            cfg.clean_whitelist.append(item.strip())
            save_config(cfg)
            print_success(f"Adicionado à whitelist: {item.strip()}")

    elif action == "remove" and cfg.clean_whitelist:
        to_remove = await questionary.checkbox(
            "Selecione os itens para remover:",
            choices=cfg.clean_whitelist,
            style=CUSTOM_STYLE,
        ).ask_async()
        if to_remove:
            cfg.clean_whitelist = [x for x in cfg.clean_whitelist if x not in to_remove]
            save_config(cfg)
            print_success(f"Removidos da whitelist: {', '.join(to_remove)}")

    elif action == "clear":
        confirm = await questionary.confirm(
            "Limpar toda a whitelist?",
            default=False,
            style=CUSTOM_STYLE,
        ).ask_async()
        if confirm:
            cfg.clean_whitelist = []
            save_config(cfg)
            print_success("Whitelist limpa.")
