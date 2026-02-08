"""Módulo de backup e exportação de dados do Telegram.

Exporta mensagens e participantes de grupos para JSON/CSV.
"""

import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from telethon import TelegramClient
from telethon.tl.types import User

logger = logging.getLogger(__name__)


def _get_timestamp() -> str:
    """Retorna timestamp atual formatado para nomes de arquivo."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _safe_getattr(obj: Any, attr: str, default: Any = None) -> Any:
    """getattr seguro que retorna default se AttributeError ocorrer."""
    try:
        return getattr(obj, attr, default)
    except (AttributeError, TypeError):
        return default


async def export_messages_to_json(
    client: TelegramClient,
    chat_entity,
    output_path: str,
) -> int:
    """Exporta todas as mensagens de um chat para JSON.

    Args:
        client: Cliente Telethon conectado.
        chat_entity: Entidade do chat (grupo/canal).
        output_path: Caminho do arquivo JSON de saída.

    Returns:
        Número de mensagens exportadas.
    """
    messages_data = []

    async for message in client.iter_messages(chat_entity):
        msg_data: dict[str, Any] = {
            "id": message.id,
            "date": message.date.isoformat() if message.date else None,
            "text": message.text,
            "sender_id": message.sender_id,
            "reply_to_msg_id": _safe_getattr(message.reply_to, 'reply_to_msg_id') if message.reply_to else None,
            "has_media": bool(message.media),
        }

        # Adicionar informações do remetente se disponível
        if message.sender:
            msg_data["sender"] = {
                "id": message.sender.id,
                "username": _safe_getattr(message.sender, 'username'),
                "first_name": _safe_getattr(message.sender, 'first_name'),
                "last_name": _safe_getattr(message.sender, 'last_name'),
            }

        # Adicionar informações de mídia
        if message.media:
            msg_data["media_type"] = type(message.media).__name__

        messages_data.append(msg_data)

    # Salvar JSON
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            "export_date": datetime.now().isoformat(),
            "chat_id": chat_entity.id,
            "chat_title": _safe_getattr(chat_entity, 'title'),
            "total_messages": len(messages_data),
            "messages": messages_data,
        }, f, ensure_ascii=False, indent=2)

    return len(messages_data)


async def export_messages_to_csv(
    client: TelegramClient,
    chat_entity,
    output_path: str,
) -> int:
    """Exporta todas as mensagens de um chat para CSV.

    Args:
        client: Cliente Telethon conectado.
        chat_entity: Entidade do chat (grupo/canal).
        output_path: Caminho do arquivo CSV de saída.

    Returns:
        Número de mensagens exportadas.
    """
    count = 0

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            "ID", "Data", "Remetente ID", "Nome", "Username",
            "Texto", "Tipo Mídia", "Reply To"
        ])

        async for message in client.iter_messages(chat_entity):
            sender_name = ""
            sender_username = ""
            if message.sender:
                first_name = _safe_getattr(message.sender, 'first_name', '')
                last_name = _safe_getattr(message.sender, 'last_name', '')
                sender_name = f"{first_name} {last_name}".strip()
                sender_username = _safe_getattr(message.sender, 'username', '')

            media_type = type(message.media).__name__ if message.media else ""
            reply_to = _safe_getattr(message.reply_to, 'reply_to_msg_id') if message.reply_to else ""

            writer.writerow([
                message.id,
                message.date.isoformat() if message.date else "",
                message.sender_id,
                sender_name,
                sender_username,
                message.text or "",
                media_type,
                reply_to,
            ])
            count += 1

    return count


async def export_participants_to_json(
    client: TelegramClient,
    chat_entity,
    output_path: str,
) -> int:
    """Exporta todos os participantes de um grupo para JSON.

    Args:
        client: Cliente Telethon conectado.
        chat_entity: Entidade do chat (grupo/canal).
        output_path: Caminho do arquivo JSON de saída.

    Returns:
        Número de participantes exportados.
    """
    participants_data = []

    async for participant in client.iter_participants(chat_entity):
        user = participant.user if hasattr(participant, 'user') else participant

        user_data: dict[str, Any] = {
            "id": user.id,
            "first_name": _safe_getattr(user, 'first_name'),
            "last_name": _safe_getattr(user, 'last_name'),
            "username": _safe_getattr(user, 'username'),
            "is_bot": _safe_getattr(user, 'bot', False),
            "is_verified": _safe_getattr(user, 'verified', False),
            "is_premium": _safe_getattr(user, 'premium', False),
            "phone": _safe_getattr(user, 'phone'),
        }

        # Adicionar informações do participante
        if hasattr(participant, 'participant'):
            p = participant.participant
            user_data["joined_date"] = _safe_getattr(p, 'date')
            if user_data["joined_date"]:
                user_data["joined_date"] = user_data["joined_date"].isoformat()
            user_data["inviter_id"] = _safe_getattr(p, 'inviter_id')
            user_data["admin_rank"] = _safe_getattr(p, 'admin_rank')

        # Status online (para User)
        if isinstance(user, User):
            status = _safe_getattr(user, 'status')
            if status:
                if hasattr(status, 'was_online') and status.was_online:
                    user_data["last_online"] = status.was_online.isoformat()
                elif hasattr(status, 'expires'):
                    user_data["online"] = True

        participants_data.append(user_data)

    # Salvar JSON
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            "export_date": datetime.now().isoformat(),
            "chat_id": chat_entity.id,
            "chat_title": _safe_getattr(chat_entity, 'title'),
            "total_participants": len(participants_data),
            "participants": participants_data,
        }, f, ensure_ascii=False, indent=2)

    return len(participants_data)


async def export_participants_to_csv(
    client: TelegramClient,
    chat_entity,
    output_path: str,
) -> int:
    """Exporta todos os participantes de um grupo para CSV.

    Args:
        client: Cliente Telethon conectado.
        chat_entity: Entidade do chat (grupo/canal).
        output_path: Caminho do arquivo CSV de saída.

    Returns:
        Número de participantes exportados.
    """
    count = 0

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            "ID", "Nome", "Username", "Bot", "Verificado", "Premium",
            "Telefone", "Data Entrada", "ID Quem Convidou", "Admin Rank"
        ])

        async for participant in client.iter_participants(chat_entity):
            user = participant.user if hasattr(participant, 'user') else participant

            first_name = _safe_getattr(user, 'first_name', '')
            last_name = _safe_getattr(user, 'last_name', '')
            full_name = f"{first_name} {last_name}".strip()

            joined_date = None
            inviter_id = None
            admin_rank = None

            if hasattr(participant, 'participant'):
                p = participant.participant
                joined_date = _safe_getattr(p, 'date')
                inviter_id = _safe_getattr(p, 'inviter_id')
                admin_rank = _safe_getattr(p, 'admin_rank')

            writer.writerow([
                user.id,
                full_name,
                _safe_getattr(user, 'username', '') or "",
                "Sim" if _safe_getattr(user, 'bot', False) else "Não",
                "Sim" if _safe_getattr(user, 'verified', False) else "Não",
                "Sim" if _safe_getattr(user, 'premium', False) else "Não",
                _safe_getattr(user, 'phone', '') or "",
                joined_date.isoformat() if joined_date else "",
                inviter_id or "",
                admin_rank or "",
            ])
            count += 1

    return count


async def backup_group_full(
    client: TelegramClient,
    chat_entity,
    output_dir: str,
    formats: str = "json",
) -> dict[str, Any]:
    """Faz backup completo de um grupo (mensagens + participantes).

    Args:
        client: Cliente Telethon conectado.
        chat_entity: Entidade do chat (grupo/canal).
        output_dir: Diretório de saída para os arquivos.
        formats: Formato dos arquivos ('json', 'csv' ou 'both').

    Returns:
        Dicionário com informações do backup realizado.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    timestamp = _get_timestamp()
    chat_title = _safe_getattr(chat_entity, 'title', str(chat_entity.id))
    safe_name = "".join(c for c in chat_title if c.isalnum() or c in (' ', '-', '_')).strip()
    safe_name = safe_name[:50]  # Limitar tamanho do nome

    results: dict[str, Any] = {
        "chat_id": chat_entity.id,
        "chat_title": chat_title,
        "backup_date": datetime.now().isoformat(),
    }

    # Exportar mensagens
    if formats in ("json", "both"):
        messages_json = f"{output_dir}/{safe_name}_messages_{timestamp}.json"
        msg_count = await export_messages_to_json(client, chat_entity, messages_json)
        results["messages_json"] = messages_json
        results["messages_count"] = msg_count

    if formats in ("csv", "both"):
        messages_csv = f"{output_dir}/{safe_name}_messages_{timestamp}.csv"
        msg_count = await export_messages_to_csv(client, chat_entity, messages_csv)
        results["messages_csv"] = messages_csv
        results["messages_count"] = msg_count

    # Exportar participantes
    if formats in ("json", "both"):
        participants_json = f"{output_dir}/{safe_name}_participants_{timestamp}.json"
        part_count = await export_participants_to_json(client, chat_entity, participants_json)
        results["participants_json"] = participants_json
        results["participants_count"] = part_count

    if formats in ("csv", "both"):
        participants_csv = f"{output_dir}/{safe_name}_participants_{timestamp}.csv"
        part_count = await export_participants_to_csv(client, chat_entity, participants_csv)
        results["participants_csv"] = participants_csv
        results["participants_count"] = part_count

    return results


async def download_media_from_chat(
    client: TelegramClient,
    chat_entity,
    output_dir: str,
    limit: int = 0,
    media_types: list[str] | None = None,
) -> dict[str, int]:
    """Baixa todos os arquivos de mídia de um chat.

    Args:
        client: Cliente Telethon conectado.
        chat_entity: Entidade do chat (grupo/canal).
        output_dir: Diretório de saída para os arquivos.
        limit: Limite de mensagens para processar (0 = todas).
        media_types: Lista de tipos de mídia para baixar.
                       Se None, baixa todos. Valores: 'photo', 'video', 'document',
                       'audio', 'voice', 'sticker', 'gif'.

    Returns:
        Dicionário com contagem de arquivos baixados por tipo.
    """
    from telethon.tl.types import (
        MessageMediaDocument,
        MessageMediaPhoto,
        MessageMediaSticker,
        MessageMediaVideo,
        MessageMediaAudio,
        MessageMediaGeoLive,
    )

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    media_dir = Path(output_dir) / "media"
    media_dir.mkdir(exist_ok=True)

    counts: dict[str, int] = {
        "photo": 0,
        "video": 0,
        "document": 0,
        "audio": 0,
        "voice": 0,
        "sticker": 0,
        "gif": 0,
        "other": 0,
        "total": 0,
    }

    async def _progress_callback(received: int, total: int) -> None:
        """Callback de progresso do download."""
        percent = (received / total) * 100 if total > 0 else 0
        if received == 0:  # Primeira chamada
            print(f"  Baixando: {total / 1024 / 1024:.1f} MB...")

    async for message in client.iter_messages(chat_entity, limit=limit):
        if not message.media:
            continue

        media_type = "other"
        should_download = media_types is None  # Baixar tudo se não especificado

        if isinstance(message.media, MessageMediaPhoto):
            media_type = "photo"
            ext = ".jpg"
        elif isinstance(message.media, (MessageMediaVideo, MessageMediaGeoLive)):
            media_type = "video"
            ext = ".mp4"
        elif isinstance(message.media, MessageMediaDocument):
            doc = message.media.document
            media_type = "document"
            # Tentar determinar extensão pelo nome do arquivo
            if hasattr(doc, "attributes"):
                for attr in doc.attributes:
                    if hasattr(attr, "file_name"):
                        name = attr.file_name
                        if "." in name:
                            ext = "." + name.rsplit(".", 1)[-1]
                        else:
                            ext = ""
                        break
            if ext == "":
                ext = ".bin"  # Fallback
        elif isinstance(message.media, MessageMediaAudio):
            media_type = "audio"
            ext = ".mp3"
        elif isinstance(message.media, MessageMediaVoice):
            media_type = "voice"
            ext = ".ogg"
        elif isinstance(message.media, MessageMediaSticker):
            media_type = "sticker"
            ext = ".webp"
        else:
            # Verificar se é GIF
            if hasattr(message.media, "document"):
                if hasattr(message.media.document, "mime_type"):
                    if message.media.document.mime_type == "video/mp4":
                        media_type = "gif"
                        ext = ".mp4"

        # Filtrar por tipo se especificado
        if media_types is not None:
            should_download = media_type in media_types

        if should_download:
            counts[media_type] += 1
            counts["total"] += 1

            # Gerar nome do arquivo
            timestamp = _get_timestamp()
            sender_id = message.sender_id or "unknown"
            filename = f"{timestamp}_{sender_id}_{message.id}{ext}"

            # Criar subdiretório para o tipo de mídia
            type_dir = media_dir / media_type
            type_dir.mkdir(exist_ok=True)

            file_path = type_dir / filename

            try:
                path = await client.download_media(
                    message,
                    file=str(file_path),
                    progress_callback=_progress_callback,
                )
                logger.debug(f"Mídia baixada: {path}")
            except Exception as e:
                logger.warning(f"Erro ao baixar mídia da mensagem {message.id}: {e}")

    return counts


async def send_backup_to_cloud(
    client: TelegramClient,
    file_path: str,
    caption: str,
) -> Any:
    """Envia um arquivo de backup para o Cloud Chat (Saved Messages).

    O Cloud Chat do Telegram é acessível usando 'me' como entidade,
    e funciona como armazenamento em nuvem pessoal.

    Args:
        client: Cliente Telethon conectado.
        file_path: Caminho do arquivo para enviar.
        caption: Descrição do arquivo (usa emojis para organização).

    Returns:
        Mensagem enviada para o Cloud Chat.
    """
    logger.info(f"Enviando arquivo para Cloud Chat: {file_path}")
    return await client.send_file('me', file_path, caption=caption)


async def backup_group_with_media(
    client: TelegramClient,
    chat_entity,
    output_dir: str,
    formats: str = "json",
    download_media: bool = False,
    media_types: list[str] | None = None,
    send_to_cloud: bool = False,
) -> dict[str, Any]:
    """Faz backup completo de um grupo incluindo mídia.

    Args:
        client: Cliente Telethon conectado.
        chat_entity: Entidade do chat (grupo/canal).
        output_dir: Diretório de saída para os arquivos.
        formats: Formato dos arquivos ('json', 'csv' ou 'both').
        download_media: Se True, baixa arquivos de mídia.
        media_types: Tipos de mídia para baixar. Se None, baixa todos.
        send_to_cloud: Se True, envia arquivos para Cloud Chat (Saved Messages).

    Returns:
        Dicionário com informações do backup realizado.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    timestamp = _get_timestamp()
    chat_title = _safe_getattr(chat_entity, 'title', str(chat_entity.id))
    safe_name = "".join(c for c in chat_title if c.isalnum() or c in (' ', '-', '_')).strip()
    safe_name = safe_name[:50]  # Limitar tamanho do nome

    results: dict[str, Any] = {
        "chat_id": chat_entity.id,
        "chat_title": chat_title,
        "backup_date": datetime.now().isoformat(),
    }

    # Exportar mensagens
    if formats in ("json", "both"):
        messages_json = f"{output_dir}/{safe_name}_messages_{timestamp}.json"
        msg_count = await export_messages_to_json(client, chat_entity, messages_json)
        results["messages_json"] = messages_json
        results["messages_count"] = msg_count

    if formats in ("csv", "both"):
        messages_csv = f"{output_dir}/{safe_name}_messages_{timestamp}.csv"
        msg_count = await export_messages_to_csv(client, chat_entity, messages_csv)
        results["messages_csv"] = messages_csv
        results["messages_count"] = msg_count

    # Exportar participantes
    if formats in ("json", "both"):
        participants_json = f"{output_dir}/{safe_name}_participants_{timestamp}.json"
        part_count = await export_participants_to_json(client, chat_entity, participants_json)
        results["participants_json"] = participants_json
        results["participants_count"] = part_count

    if formats in ("csv", "both"):
        participants_csv = f"{output_dir}/{safe_name}_participants_{timestamp}.csv"
        part_count = await export_participants_to_csv(client, chat_entity, participants_csv)
        results["participants_csv"] = participants_csv
        results["participants_count"] = part_count

    # Baixar mídia
    if download_media:
        logger.info("Baixando arquivos de mídia...")
        media_counts = await download_media_from_chat(
            client,
            chat_entity,
            output_dir,
            media_types=media_types,
        )
        results["media"] = media_counts

    # Enviar para Cloud Chat
    if send_to_cloud:
        logger.info("Enviando backup para Cloud Chat (Saved Messages)...")
        cloud_files = []

        # Enviar mensagens JSON
        if "messages_json" in results and Path(results["messages_json"]).exists():
            msg_count = results.get("messages_count", 0)
            caption = f"📦 Backup: {chat_title} - Mensagens ({msg_count} msgs)"
            await send_backup_to_cloud(client, results["messages_json"], caption)
            cloud_files.append("messages_json")

        # Enviar mensagens CSV
        if "messages_csv" in results and Path(results["messages_csv"]).exists():
            msg_count = results.get("messages_count", 0)
            caption = f"📦 Backup: {chat_title} - Mensagens CSV ({msg_count} msgs)"
            await send_backup_to_cloud(client, results["messages_csv"], caption)
            cloud_files.append("messages_csv")

        # Enviar participantes JSON
        if "participants_json" in results and Path(results["participants_json"]).exists():
            part_count = results.get("participants_count", 0)
            caption = f"👥 Backup: {chat_title} - Participantes ({part_count} membros)"
            await send_backup_to_cloud(client, results["participants_json"], caption)
            cloud_files.append("participants_json")

        # Enviar participantes CSV
        if "participants_csv" in results and Path(results["participants_csv"]).exists():
            part_count = results.get("participants_count", 0)
            caption = f"👥 Backup: {chat_title} - Participantes CSV ({part_count} membros)"
            await send_backup_to_cloud(client, results["participants_csv"], caption)
            cloud_files.append("participants_csv")

        # Enviar mensagem de resumo
        summary_parts = [f"📊 **Resumo do Backup**\n"]
        summary_parts.append(f"📁 Grupo: {chat_title}")
        summary_parts.append(f"📅 Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        if "messages_count" in results:
            summary_parts.append(f"💬 Mensagens: {results['messages_count']}")
        if "participants_count" in results:
            summary_parts.append(f"👥 Participantes: {results['participants_count']}")
        if "media" in results:
            summary_parts.append(f"🖼️ Arquivos de mídia: {results['media']['total']}")
        summary_parts.append(f"\n✅ {len(cloud_files)} arquivo(s) enviado(s) para Saved Messages")

        await client.send_message('me', "\n".join(summary_parts))
        results["cloud_backup"] = True
        results["cloud_files"] = cloud_files
        logger.info(f"Backup enviado para Cloud Chat: {len(cloud_files)} arquivos")

    return results

