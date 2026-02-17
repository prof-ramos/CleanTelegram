"""Módulo de geração de relatórios para CleanTelegram.

Gera relatórios de grupos, canais e contatos em diversos formatos.
"""

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from telethon import TelegramClient
from telethon.tl.types import Channel, Chat, User


def _get_timestamp() -> str:
    """Retorna timestamp atual formatado para nomes de arquivo."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _safe_getattr(obj: Any, attr: str, default: Any = None) -> Any:
    """getattr seguro que retorna default se AttributeError ocorrer."""
    try:
        return getattr(obj, attr, default)
    except (AttributeError, TypeError):
        return default


def _is_channel(entity: Any) -> bool:
    """Verifica se a entidade é um Channel (tem atributo megagroup)."""
    return hasattr(entity, "megagroup") or hasattr(entity, "broadcast")


def _is_chat(entity: Any) -> bool:
    """Verifica se a entidade é um Chat (grupo legado, tem participants_count mas não megagroup)."""
    return hasattr(entity, "participants_count") and not hasattr(entity, "megagroup")


def _is_user(entity: Any) -> bool:
    """Verifica se a entidade é um User (tem first_name ou bot).

    Nota: User pode ter username mas não megagroup/broadcast (Channel)
    nem apenas participants_count (Chat legado).
    """
    return (
        hasattr(entity, "first_name")
        or hasattr(entity, "bot")
        or (hasattr(entity, "username") and not hasattr(entity, "megagroup"))
    ) and not _is_channel(entity) and not _is_chat(entity)


async def generate_groups_channels_report(
    client: TelegramClient,
    output_path: str | None = None,
    output_format: str = "csv",
) -> str:
    """Gera relatório de grupos e canais.

    Args:
        client: Cliente Telethon conectado.
        output_path: Caminho do arquivo de saída. Se None, usa padrão com timestamp.
        output_format: Formato do relatório (csv, json ou txt).

    Returns:
        Caminho do arquivo gerado.
    """
    # Coletar dados
    items = []

    async for dialog in client.iter_dialogs():
        entity = dialog.entity

        if not (_is_channel(entity) or _is_chat(entity)):
            continue

        item: dict[str, Any] = {
            "title": dialog.name or "(sem nome)",
            "id": entity.id,
        }

        if _is_channel(entity):
            item["type"] = "Channel"
            item["username"] = _safe_getattr(entity, "username", "")
            item["participants_count"] = _safe_getattr(entity, "participants_count", 0)
            item["is_megagroup"] = _safe_getattr(entity, "megagroup", False)
            item["is_broadcast"] = _safe_getattr(entity, "broadcast", False)
            item["creator"] = _safe_getattr(entity, "creator", False)
            item["admin_rights"] = _safe_getattr(entity, "admin_rights") is not None
            item["date"] = (
                _safe_getattr(entity, "date").isoformat()
                if _safe_getattr(entity, "date")
                else ""
            )
        else:  # Chat (grupo legado)
            item["type"] = "Chat"
            item["username"] = ""
            item["participants_count"] = _safe_getattr(entity, "participants_count", 0)
            item["is_megagroup"] = False
            item["is_broadcast"] = False
            item["creator"] = _safe_getattr(entity, "creator", False)
            item["admin_rights"] = False
            item["date"] = ""

        items.append(item)

    # Validar formato antes de processar
    valid_formats = {"csv", "json", "txt"}
    if output_format not in valid_formats:
        raise ValueError(f"Formato não suportado: {output_format}. Use um de: {', '.join(sorted(valid_formats))}")

    # Determinar caminho de saída
    if output_path is None:
        timestamp = _get_timestamp()
        suffix = output_format  # O formato já é a extensão
        output_path = f"relatorios/groups_channels_{timestamp}.{suffix}"

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Gerar relatório no formato solicitado
    if output_format == "csv":
        _write_csv_report(items, output_file)
    elif output_format == "json":
        _write_json_report(items, output_file, report_type="groups_channels")
    elif output_format == "txt":
        _write_txt_report(items, output_file, report_type="groups_channels")

    return str(output_file)


async def generate_contacts_report(
    client: TelegramClient,
    output_path: str | None = None,
    output_format: str = "csv",
) -> str:
    """Gera relatório de contatos e usuários.

    Args:
        client: Cliente Telethon conectado.
        output_path: Caminho do arquivo de saída. Se None, usa padrão com timestamp.
        output_format: Formato do relatório (csv, json ou txt).

    Returns:
        Caminho do arquivo gerado.
    """
    # Coletar dados
    items = []

    async for dialog in client.iter_dialogs():
        entity = dialog.entity

        if not _is_user(entity):
            continue

        # Formatar nome
        first_name = _safe_getattr(entity, "first_name", "")
        last_name = _safe_getattr(entity, "last_name", "")
        full_name = f"{first_name} {last_name}".strip() or first_name or "(sem nome)"

        # Status
        status = _safe_getattr(entity, "status", None)
        status_str = ""
        if status:
            if hasattr(status, "was_online"):
                status_str = f"Último acesso: {_format_status(status)}"
            elif hasattr(status, "expires"):
                status_str = "Online"
            else:
                status_str = str(type(status).__name__)

        item: dict[str, Any] = {
            "name": full_name,
            "id": entity.id,
            "username": f"@{_safe_getattr(entity, 'username', '')}" if _safe_getattr(entity, "username") else "",
            "is_bot": _safe_getattr(entity, "bot", False),
            "is_verified": _safe_getattr(entity, "verified", False),
            "is_premium": _safe_getattr(entity, "premium", False),
            "status": status_str,
            "phone": _safe_getattr(entity, "phone", ""),
        }

        items.append(item)

    # Validar formato antes de processar
    valid_formats = {"csv", "json", "txt"}
    if output_format not in valid_formats:
        raise ValueError(f"Formato não suportado: {output_format}. Use um de: {', '.join(sorted(valid_formats))}")

    # Determinar caminho de saída
    if output_path is None:
        timestamp = _get_timestamp()
        suffix = output_format  # O formato já é a extensão
        output_path = f"relatorios/contacts_{timestamp}.{suffix}"

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Gerar relatório no formato solicitado
    if output_format == "csv":
        _write_csv_report(items, output_file, report_type="contacts")
    elif output_format == "json":
        _write_json_report(items, output_file, report_type="contacts")
    elif output_format == "txt":
        _write_txt_report(items, output_file, report_type="contacts")
    #Nota: else removido pois a validação de formato garante que output_format é válido

    return str(output_file)


def _format_status(status) -> str:
    """Formata status de usuário para exibição."""
    if hasattr(status, "was_online") and status.was_online:
        return status.was_online.strftime("%d/%m/%Y %H:%M")
    return "Desconhecido"


def _write_csv_report(items: list[dict[str, Any]], output_file: Path, report_type: str = "groups_channels") -> None:
    """Escreve relatório em formato CSV."""
    if not items:
        # Criar arquivo vazio com cabeçalho
        with open(output_file, "w", newline="", encoding="utf-8") as f:
            if report_type == "groups_channels":
                writer = csv.DictWriter(
                    f,
                    fieldnames=[
                        "Tipo",
                        "Nome",
                        "ID",
                        "Username",
                        "Participantes",
                        "Megagrupo",
                        "Broadcast",
                        "Criador",
                        "Admin",
                        "Data Criação",
                    ],
                )
            else:
                writer = csv.DictWriter(
                    f,
                    fieldnames=[
                        "Nome",
                        "ID",
                        "Username",
                        "Bot",
                        "Verificado",
                        "Premium",
                        "Status",
                        "Telefone",
                    ],
                )
            writer.writeheader()
        return

    with open(output_file, "w", newline="", encoding="utf-8") as f:
        if report_type == "groups_channels":
            fieldnames = [
                "Tipo",
                "Nome",
                "ID",
                "Username",
                "Participantes",
                "Megagrupo",
                "Broadcast",
                "Criador",
                "Admin",
                "Data Criação",
            ]
            rows = [
                {
                    "Tipo": item["type"],
                    "Nome": item["title"],
                    "ID": item["id"],
                    "Username": item["username"],
                    "Participantes": item["participants_count"],
                    "Megagrupo": "Sim" if item["is_megagroup"] else "Não",
                    "Broadcast": "Sim" if item["is_broadcast"] else "Não",
                    "Criador": "Sim" if item["creator"] else "Não",
                    "Admin": "Sim" if item["admin_rights"] else "Não",
                    "Data Criação": item["date"],
                }
                for item in items
            ]
        else:  # contacts
            fieldnames = [
                "Nome",
                "ID",
                "Username",
                "Bot",
                "Verificado",
                "Premium",
                "Status",
                "Telefone",
            ]
            rows = [
                {
                    "Nome": item["name"],
                    "ID": item["id"],
                    "Username": item["username"],
                    "Bot": "Sim" if item["is_bot"] else "Não",
                    "Verificado": "Sim" if item["is_verified"] else "Não",
                    "Premium": "Sim" if item["is_premium"] else "Não",
                    "Status": item["status"],
                    "Telefone": item["phone"],
                }
                for item in items
            ]

        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_json_report(items: list[dict[str, Any]], output_file: Path, report_type: str) -> None:
    """Escreve relatório em formato JSON."""
    report = {
        "generated_at": datetime.now().isoformat(),
        "report_type": report_type,
        "total": len(items),
        "items": items,
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)


def _write_txt_report(items: list[dict[str, Any]], output_file: Path, report_type: str) -> None:
    """Escreve relatório em formato TXT formatado."""
    lines: list[str] = []

    if report_type == "groups_channels":
        title = "RELATÓRIO DE GRUPOS E CANAIS"
    else:
        title = "RELATÓRIO DE CONTATOS"

    lines.append("=" * 50)
    lines.append(title)
    lines.append(f"Gerado em: {datetime.now().strftime('%d/%m/%Y às %H:%M')}")
    lines.append(f"Total: {len(items)} item(ns)")
    lines.append("=" * 50)
    lines.append("")

    if not items:
        lines.append("(Nenhum item encontrado)")
    else:
        for i, item in enumerate(items, 1):
            if report_type == "groups_channels":
                lines.append(f"[{i}] {item['type']} - {item['title']}")
                if item["username"]:
                    lines.append(f"    Username: {item['username']}")
                lines.append(f"    ID: {item['id']}")
                lines.append(f"    Participantes: {item['participants_count']}")
                if item["type"] == "Channel":
                    lines.append(f"    Megagrupo: {'Sim' if item['is_megagroup'] else 'Não'}")
                    lines.append(f"    Broadcast: {'Sim' if item['is_broadcast'] else 'Não'}")
                lines.append(f"    Criador: {'Sim' if item['creator'] else 'Não'}")
                lines.append(f"    Admin: {'Sim' if item['admin_rights'] else 'Não'}")
                if item["date"]:
                    lines.append(f"    Data Criação: {item['date']}")
            else:  # contacts
                lines.append(f"[{i}] {item['name']}")
                if item["username"]:
                    lines.append(f"    Username: {item['username']}")
                lines.append(f"    ID: {item['id']}")
                lines.append(f"    Bot: {'Sim' if item['is_bot'] else 'Não'}")
                lines.append(f"    Verificado: {'Sim' if item['is_verified'] else 'Não'}")
                lines.append(f"    Premium: {'Sim' if item['is_premium'] else 'Não'}")
                if item["status"]:
                    lines.append(f"    Status: {item['status']}")
                if item["phone"]:
                    lines.append(f"    Telefone: {item['phone']}")

            lines.append("")

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


async def generate_all_reports(
    client: TelegramClient,
    output_format: str = "csv",
) -> dict[str, str]:
    """Gera todos os relatórios disponíveis.

    Args:
        client: Cliente Telethon conectado.
        output_format: Formato dos relatórios (csv, json ou txt).

    Returns:
        Dicionário com tipo de relatório e caminho do arquivo gerado.
    """
    results = {}

    # Gerar relatório de grupos e canais
    groups_path = await generate_groups_channels_report(client, output_format=output_format)
    results["groups_channels"] = groups_path

    # Gerar relatório de contatos
    contacts_path = await generate_contacts_report(client, output_format=output_format)
    results["contacts"] = contacts_path

    return results
