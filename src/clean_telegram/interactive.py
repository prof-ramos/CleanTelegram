"""Modo interativo para o CLI do CleanTelegram usando Questionary.

Oferece menus de seleção bonitos e intuitivos para ações, tipos de relatório e formatos,
semelhante a ferramentas como Claude Code e Mole.
"""

import logging

import questionary

from telethon import TelegramClient

from .backup import backup_group_with_media
from .cleaner import clean_all_dialogs
from .reports import (
    generate_all_reports,
    generate_contacts_report,
    generate_groups_channels_report,
)

logger = logging.getLogger(__name__)


# Estilo customizado para Questionary
CUSTOM_STYLE = questionary.Style(
    [
        ("qmark", "fg:#67b7a1 bold"),  # Cor do marcador "?"
        ("question", "bold"),           # Pergunta em negrito
        ("selected", "fg:#cc5454"),     # Opção selecionada
        ("pointer", "fg:#67b7a1 bold"), # Ponteiro "> "
        ("highlighted", "fg:#67b7a1 bold"),  # Opção destacada
        ("answer", "fg:#f6b93b bold"),  # Resposta
        ("separator", "fg:#6e6e6e"),    # Separador
    ]
)


async def interactive_main(client: TelegramClient) -> None:
    """Menu interativo principal."""
    while True:
        me = await client.get_me()
        username = me.username or me.first_name

        # Menu principal
        action = await questionary.select(
            f"🚀 CleanTelegram - Logado como: {username} (id={me.id})\n"
            "O que você deseja fazer?",
            choices=[
                questionary.Choice("🧹 Limpar conta", value="clean", description="Apaga conversas e sai de grupos/canais"),
                questionary.Choice("📊 Gerar relatórios", value="reports", description="Exporta grupos, canais e contatos"),
                questionary.Choice("📦 Backup de grupo", value="backup", description="Faz backup de mensagens e participantes"),
                questionary.Choice("⚙️  Ver estatísticas", value="stats", description="Mostra informações da conta"),
                questionary.Choice("🚪 Sair", value="exit"),
            ],
            style=CUSTOM_STYLE,
        ).ask_async()

        if action == "exit":
            print("\n👋 Até logo!")
            break
        elif action == "clean":
            await interactive_clean(client)
        elif action == "reports":
            await interactive_reports(client)
        elif action == "backup":
            await interactive_backup(client)
        elif action == "stats":
            await interactive_stats(client)

        # Pausa antes de voltar ao menu (apenas se não saiu)
        if action != "exit":
            await questionary.press_any_key_to_continue("\nPressione qualquer tecla para continuar...").ask_async()


async def interactive_clean(client: TelegramClient) -> None:
    """Fluxo interativo de limpeza."""
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
        print("\n❌ Operação cancelada.")
        return

    # Modo dry-run
    dry_run = await questionary.confirm(
        "Executar em modo dry-run (simulação)?",
        default=True,
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
            print("\n❌ Operação cancelada.")
            return

    # Limite de diálogos
    limit_choice = await questionary.select(
        "Quantos diálogos processar?",
        choices=[
            questionary.Choice("Todos os diálogos", value=0),
            questionary.Choice("Apenas os primeiros 10", value=10),
            questionary.Choice("Apenas os primeiros 50", value=50),
            questionary.Choice("Cancelar", value=None),
        ],
        style=CUSTOM_STYLE,
    ).ask_async()

    if limit_choice is None:
        print("\n❌ Operação cancelada.")
        return

    # Executar
    print(f"\n{'🔍 Simulando' if dry_run else '🚀 Executando'} limpeza...")

    try:
        processed = await clean_all_dialogs(
            client,
            dry_run=dry_run,
            limit=limit_choice,
        )

        if dry_run:
            print(f"\n✅ Simulação concluída! {processed} diálogos seriam processados.")
        else:
            print(f"\n✅ Limpeza concluída! {processed} diálogos processados.")
    except Exception as e:
        print(f"\n❌ Erro durante limpeza: {e}")
        logger.exception("Erro na limpeza interativa")


async def interactive_reports(client: TelegramClient) -> None:
    """Fluxo interativo de geração de relatórios."""
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
        return

    # Formato
    output_format = await questionary.select(
        "Em qual formato?",
        choices=[
            questionary.Choice("📊 CSV (planilha)", value="csv"),
            questionary.Choice("📋 JSON (estruturado)", value="json"),
            questionary.Choice("📝 TXT (texto simples)", value="txt"),
        ],
        style=CUSTOM_STYLE,
    ).ask_async()

    if not output_format:
        return

    # Caminho personalizado
    custom_path = await questionary.confirm(
        "Deseja especificar caminho do arquivo?",
        default=False,
        style=CUSTOM_STYLE,
    ).ask_async()

    output_path = None
    if custom_path:
        output_path = await questionary.path(
            "Caminho do arquivo (deixe vazio para padrão)",
            style=CUSTOM_STYLE,
        ).ask_async()

        if not output_path:
            output_path = None

    # Gerar relatório
    print(f"\n📊 Gerando relatório: {report_type} ({output_format})...")

    try:
        if report_type == "all":
            results = await generate_all_reports(client, output_format=output_format)
            print("\n✅ Relatórios gerados:")
            for name, path in results.items():
                print(f"   • {name}: {path}")
        elif report_type == "groups":
            path = await generate_groups_channels_report(
                client,
                output_path=output_path,
                output_format=output_format,
            )
            print(f"\n✅ Relatório de grupos/canais: {path}")
        else:  # contacts
            path = await generate_contacts_report(
                client,
                output_path=output_path,
                output_format=output_format,
            )
            print(f"\n✅ Relatório de contatos: {path}")

    except Exception as e:
        print(f"\n❌ Erro ao gerar relatório: {e}")
        logger.exception("Erro na geração de relatório")


async def interactive_stats(client: TelegramClient) -> None:
    """Mostra estatísticas da conta."""
    me = await client.get_me()

    print("\n📊 Estatísticas da Conta")
    print("=" * 40)
    print(f"👤 Nome: {me.first_name} {me.last_name or ''}".strip())
    print(f"📱 Username: @{me.username}" if me.username else "📱 Username: (não definido)")
    print(f"🆔 ID: {me.id}")
    print(f"✅ Verificado: {'Sim' if getattr(me, 'verified', False) else 'Não'}")
    print(f"🤖 Bot: {'Sim' if getattr(me, 'bot', False) else 'Não'}")

    # Contar diálogos
    print("\n⏳ Contando diálogos...")

    dialogs_count = 0
    groups_count = 0
    users_count = 0
    channels_count = 0

    async for dialog in client.iter_dialogs():
        dialogs_count += 1
        entity = dialog.entity

        # Verificar tipo usando duck-typing
        if hasattr(entity, "megagroup"):
            if getattr(entity, "broadcast", False):
                channels_count += 1
            else:
                groups_count += 1
        elif hasattr(entity, "participants_count"):
            # Chat legado
            groups_count += 1
        elif hasattr(entity, "first_name") or hasattr(entity, "bot"):
            users_count += 1

    print("\n📁 Diálogos:")
    print(f"   • Total: {dialogs_count}")
    print(f"   • Grupos: {groups_count}")
    print(f"   • Canais: {channels_count}")
    print(f"   • Contatos: {users_count}")

    print("\n💡 Dica: Use 'Gerar relatórios' para exportar esses dados.")


async def interactive_backup(client: TelegramClient) -> None:
    """Fluxo interativo de backup de grupo."""
    # Perguntar qual grupo/canal fazer backup
    chat_id = await questionary.text(
        "Digite o ID, username ou link do grupo/canal (ex: @grupo, -1001234567890)",
        style=CUSTOM_STYLE,
    ).ask_async()

    if not chat_id:
        print("\n❌ Operação cancelada.")
        return

    # Tentar resolver a entidade
    try:
        entity = await client.get_entity(chat_id)
    except Exception as e:
        print(f"\n❌ Erro ao encontrar chat '{chat_id}': {e}")
        return

    chat_title = getattr(entity, 'title', str(entity.id))
    print(f"\n📁 Grupo encontrado: {chat_title}")

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
        print("\n❌ Operação cancelada.")
        return

    # Perguntar se quer baixar mídia
    download_media = await questionary.confirm(
        "Baixar arquivos de mídia (fotos, vídeos, documentos)?",
        default=False,
        style=CUSTOM_STYLE,
    ).ask_async()

    # Tipos de mídia (se quiser baixar)
    media_types = None
    if download_media:
        media_choice = await questionary.select(
            "Quais tipos de mídia baixar?",
            choices=[
                questionary.Choice("📦 Todos os tipos", value=None),
                questionary.Choice("📷 Apenas fotos", value=["photo"]),
                questionary.Choice("🎥 Apenas vídeos", value=["video"]),
                questionary.Choice("📄 Apenas documentos", value=["document"]),
                questionary.Choice("Seleção personalizada", value="custom"),
            ],
            style=CUSTOM_STYLE,
        ).ask_async()

        if media_choice == "custom":
            media_types = []
            if await questionary.confirm("📷 Fotos?", default=False, style=CUSTOM_STYLE).ask_async():
                media_types.append("photo")
            if await questionary.confirm("🎥 Vídeos?", default=False, style=CUSTOM_STYLE).ask_async():
                media_types.append("video")
            if await questionary.confirm("📄 Documentos?", default=False, style=CUSTOM_STYLE).ask_async():
                media_types.append("document")
            if await questionary.confirm("🎵 Áudio?", default=False, style=CUSTOM_STYLE).ask_async():
                media_types.append("audio")
            if await questionary.confirm("🎤 Voice notes?", default=False, style=CUSTOM_STYLE).ask_async():
                media_types.append("voice")
            if await questionary.confirm("😄 Stickers?", default=False, style=CUSTOM_STYLE).ask_async():
                media_types.append("sticker")
            if await questionary.confirm("🎞️ GIFs?", default=False, style=CUSTOM_STYLE).ask_async():
                media_types.append("gif")

            if not media_types:
                print("\n⚠️ Nenhum tipo selecionado, baixando todos...")
                media_types = None
        else:
            media_types = media_choice

    # Perguntar se quer enviar para Cloud Chat
    send_to_cloud = await questionary.confirm(
        "☁️ Enviar backup para Cloud Chat (Saved Messages)?\n"
        "   Os arquivos serão enviados para suas 'Mensagens Salvas' no Telegram.",
        default=False,
        style=CUSTOM_STYLE,
    ).ask_async()

    # Confirmação final
    print("\n📋 Resumo do backup:")
    print(f"   • Grupo: {chat_title}")
    print(f"   • Formato: {output_format}")
    if download_media:
        print(f"   • Mídia: Sim ({'todos os tipos' if not media_types else ', '.join(media_types)})")
    else:
        print(f"   • Mídia: Não")
    print(f"   • Cloud Chat: {'Sim' if send_to_cloud else 'Não'}")

    confirm = await questionary.confirm(
        "\nIniciar backup?",
        default=True,
        style=CUSTOM_STYLE,
    ).ask_async()

    if not confirm:
        print("\n❌ Operação cancelada.")
        return

    # Executar backup
    print(f"\n📦 Iniciando backup...")

    try:
        results = await backup_group_with_media(
            client,
            entity,
            "backups",
            output_format,
            download_media=download_media,
            media_types=media_types,
            send_to_cloud=send_to_cloud,
        )

        print("\n✅ Backup concluído!")
        print(f"   • Mensagens: {results.get('messages_count', 0)}")
        print(f"   • Participantes: {results.get('participants_count', 0)}")

        if "media" in results:
            print(f"   • Arquivos de mídia: {results['media']['total']} baixados")
            for media_type, count in results['media'].items():
                if media_type != 'total' and count > 0:
                    print(f"     - {media_type}: {count}")

        if "cloud_backup" in results and results["cloud_backup"]:
            print(f"   • ☁️ Cloud Chat: {len(results.get('cloud_files', []))} arquivo(s) enviado(s) para Saved Messages")

        if "messages_json" in results:
            print(f"\n📁 Arquivos salvos:")
            if "messages_json" in results:
                print(f"   • Mensagens: {results['messages_json']}")
            if "participants_json" in results:
                print(f"   • Participantes: {results['participants_json']}")
            if "messages_csv" in results:
                print(f"   • Mensagens CSV: {results['messages_csv']}")
            if "participants_csv" in results:
                print(f"   • Participantes CSV: {results['participants_csv']}")

    except Exception as e:
        print(f"\n❌ Erro durante backup: {e}")
        logger.exception("Erro no backup interativo")
