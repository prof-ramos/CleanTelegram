"""Testes unitários para o módulo de relatórios."""

import json
from datetime import datetime
from pathlib import Path
from unittest import mock

import pytest

from clean_telegram.reports import (
    _format_status,
    _write_csv_report,
    _write_json_report,
    _write_txt_report,
    generate_contacts_report,
    generate_groups_channels_report,
)


# Fixtures


@pytest.fixture
def mock_channel():
    """Cria um mock de Channel do Telethon."""
    channel = mock.Mock()
    channel.id = 123456
    channel.__class__.__name__ = "Channel"
    return channel


@pytest.fixture
def mock_chat():
    """Cria um mock de Chat do Telethon."""
    chat = mock.Mock()
    chat.id = 789012
    chat.__class__.__name__ = "Chat"
    return chat


@pytest.fixture
def mock_user():
    """Cria um mock de User do Telethon."""
    user = mock.Mock()
    user.id = 999888
    user.__class__.__name__ = "User"
    return user


@pytest.fixture
def mock_client_with_channels():
    """Cria um mock de TelegramClient com diálogos de grupos/canais."""
    client = mock.AsyncMock()

    # Criar classes simples para simular tipos do Telethon
    class MockChannel:
        id = 123456
        username = "grupoteste"
        participants_count = 150
        megagroup = True
        broadcast = False
        creator = False
        admin_rights = None
        date = datetime(2024, 1, 15, 10, 30)

    class MockChat:
        id = 789012
        participants_count = 25
        creator = True

    class MockUser:
        id = 999888

    # Mock de iter_dialogs
    async def mock_iter_dialogs():
        dialogs = []

        # Channel (megagrupo)
        dialog1 = mock.Mock()
        dialog1.name = "Grupo de Teste"
        dialog1.entity = MockChannel()
        dialogs.append(dialog1)

        # Chat (grupo legado)
        dialog2 = mock.Mock()
        dialog2.name = "Grupo Antigo"
        dialog2.entity = MockChat()
        dialogs.append(dialog2)

        # User (deve ser ignorado)
        dialog3 = mock.Mock()
        dialog3.name = "João Silva"
        dialog3.entity = MockUser()
        dialogs.append(dialog3)

        for d in dialogs:
            yield d

    client.iter_dialogs = mock_iter_dialogs
    return client


@pytest.fixture
def mock_client_with_users():
    """Cria um mock de TelegramClient com diálogos de usuários."""
    client = mock.AsyncMock()

    # Criar classes simples para simular tipos do Telethon
    class MockUser1:
        id = 111222
        first_name = "Maria"
        last_name = "Santos"
        username = "mariasantos"
        bot = False
        verified = True
        premium = False
        phone = "+5511999999999"

        class status:
            was_online = datetime(2024, 2, 7, 14, 30)

    class MockUser2:
        id = 333444
        first_name = "Bot"
        last_name = "de Teste"
        username = "testbot"
        bot = True
        verified = False
        premium = False
        phone = ""

        class status:
            expires = datetime.now().timestamp() + 3600

    class MockChannel:
        id = 555666
        megagroup = True

    # Mock de iter_dialogs
    async def mock_iter_dialogs():
        dialogs = []

        # Usuário comum
        dialog1 = mock.Mock()
        dialog1.name = "Maria Santos"
        dialog1.entity = MockUser1()
        dialogs.append(dialog1)

        # Bot
        dialog2 = mock.Mock()
        dialog2.name = "Bot de Teste"
        dialog2.entity = MockUser2()
        dialogs.append(dialog2)

        # Channel (deve ser ignorado)
        dialog3 = mock.Mock()
        dialog3.name = "Canal de Notícias"
        dialog3.entity = MockChannel()
        dialogs.append(dialog3)

        for d in dialogs:
            yield d

    client.iter_dialogs = mock_iter_dialogs
    return client


@pytest.fixture
def temp_output_file(tmp_path):
    """Cria um caminho temporário para arquivos de saída."""
    return tmp_path / "test_output"


# Testes das funções de escrita


def test_write_csv_report_groups_channels(temp_output_file, mock_client_with_channels):
    """Testa escrita de relatório CSV de grupos/canais."""
    items = [
        {
            "type": "Channel",
            "title": "Grupo de Teste",
            "id": 123456,
            "username": "@grupoteste",
            "participants_count": 150,
            "is_megagroup": True,
            "is_broadcast": False,
            "creator": False,
            "admin_rights": False,
            "date": "2024-01-15T10:30:00",
        }
    ]

    _write_csv_report(items, temp_output_file, report_type="groups_channels")

    assert temp_output_file.exists()

    content = temp_output_file.read_text(encoding="utf-8")
    lines = content.strip().split("\n")

    # Verificar cabeçalho
    assert "Tipo,Nome,ID,Username,Participantes" in lines[0]

    # Verificar conteúdo
    assert "Channel,Grupo de Teste,123456,@grupoteste,150" in lines[1]


def test_write_csv_report_contacts(temp_output_file):
    """Testa escrita de relatório CSV de contatos."""
    items = [
        {
            "name": "Maria Santos",
            "id": 111222,
            "username": "@mariasantos",
            "is_bot": False,
            "is_verified": True,
            "is_premium": False,
            "status": "Último acesso: 07/02/2024 14:30",
            "phone": "+5511999999999",
        }
    ]

    _write_csv_report(items, temp_output_file, report_type="contacts")

    assert temp_output_file.exists()

    content = temp_output_file.read_text(encoding="utf-8")
    lines = content.strip().split("\n")

    # Verificar cabeçalho
    assert "Nome,ID,Username,Bot,Verificado" in lines[0]

    # Verificar conteúdo
    assert "Maria Santos,111222,@mariasantos,Não,Sim" in lines[1]


def test_write_csv_report_empty(temp_output_file):
    """Testa escrita de relatório CSV vazio."""
    _write_csv_report([], temp_output_file, report_type="groups_channels")

    assert temp_output_file.exists()

    content = temp_output_file.read_text(encoding="utf-8")
    lines = content.strip().split("\n")

    # Deve ter apenas o cabeçalho
    assert len(lines) == 1
    assert "Tipo" in lines[0]


def test_write_json_report(temp_output_file):
    """Testa escrita de relatório JSON."""
    items = [
        {
            "type": "Channel",
            "title": "Grupo de Teste",
            "id": 123456,
        }
    ]

    _write_json_report(items, temp_output_file, report_type="groups_channels")

    assert temp_output_file.exists()

    with open(temp_output_file, encoding="utf-8") as f:
        data = json.load(f)

    assert data["report_type"] == "groups_channels"
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Grupo de Teste"
    assert "generated_at" in data


def test_write_txt_report(temp_output_file):
    """Testa escrita de relatório TXT formatado."""
    items = [
        {
            "type": "Channel",
            "title": "Grupo de Teste",
            "id": 123456,
            "username": "@grupoteste",
            "participants_count": 150,
            "is_megagroup": True,
            "is_broadcast": False,
            "creator": False,
            "admin_rights": False,
            "date": "2024-01-15T10:30:00",
        }
    ]

    _write_txt_report(items, temp_output_file, report_type="groups_channels")

    assert temp_output_file.exists()

    content = temp_output_file.read_text(encoding="utf-8")

    assert "RELATÓRIO DE GRUPOS E CANAIS" in content
    assert "[1] Channel - Grupo de Teste" in content
    assert "Username: @grupoteste" in content
    assert "ID: 123456" in content
    assert "Participantes: 150" in content


def test_write_txt_report_empty(temp_output_file):
    """Testa escrita de relatório TXT vazio."""
    _write_txt_report([], temp_output_file, report_type="groups_channels")

    assert temp_output_file.exists()

    content = temp_output_file.read_text(encoding="utf-8")

    assert "RELATÓRIO DE GRUPOS E CANAIS" in content
    assert "(Nenhum item encontrado)" in content


# Testes da função de formatação de status


def test_format_status_with_was_online():
    """Testa formatação de status com was_online."""
    status = mock.Mock()
    status.was_online = datetime(2024, 2, 7, 14, 30)

    result = _format_status(status)

    assert result == "07/02/2024 14:30"


def test_format_status_without_was_online():
    """Testa formatação de status sem was_online."""
    status = mock.Mock()
    delattr(status, "was_online")

    result = _format_status(status)

    assert result == "Desconhecido"


# Testes das funções principais (com mocks)


@pytest.mark.asyncio
async def test_generate_groups_channels_report_csv(mock_client_with_channels, tmp_path):
    """Testa geração de relatório CSV de grupos/canais."""
    output_path = tmp_path / "test_groups.csv"

    result = await generate_groups_channels_report(
        mock_client_with_channels,
        output_path=str(output_path),
        output_format="csv",
    )

    assert result == str(output_path)
    assert output_path.exists()

    content = output_path.read_text(encoding="utf-8")
    assert "Grupo de Teste" in content
    assert "Grupo Antigo" in content


@pytest.mark.asyncio
async def test_generate_groups_channels_report_json(mock_client_with_channels, tmp_path):
    """Testa geração de relatório JSON de grupos/canais."""
    output_path = tmp_path / "test_groups.json"

    result = await generate_groups_channels_report(
        mock_client_with_channels,
        output_path=str(output_path),
        output_format="json",
    )

    assert result == str(output_path)
    assert output_path.exists()

    with open(output_path, encoding="utf-8") as f:
        data = json.load(f)

    assert data["total"] == 2  # Channel + Chat (User é ignorado)
    assert data["items"][0]["title"] == "Grupo de Teste"


@pytest.mark.asyncio
async def test_generate_groups_channels_report_txt(mock_client_with_channels, tmp_path):
    """Testa geração de relatório TXT de grupos/canais."""
    output_path = tmp_path / "test_groups.txt"

    result = await generate_groups_channels_report(
        mock_client_with_channels,
        output_path=str(output_path),
        output_format="txt",
    )

    assert result == str(output_path)
    assert output_path.exists()

    content = output_path.read_text(encoding="utf-8")
    assert "RELATÓRIO DE GRUPOS E CANAIS" in content
    assert "Grupo de Teste" in content


@pytest.mark.asyncio
async def test_generate_groups_channels_report_default_path(mock_client_with_channels, tmp_path, monkeypatch):
    """Testa geração de relatório com caminho padrão (timestamp)."""
    # Mudar diretório de trabalho para tmp_path
    monkeypatch.chdir(tmp_path)

    result = await generate_groups_channels_report(
        mock_client_with_channels,
        output_path=None,
        output_format="csv",
    )

    assert result.startswith("relatorios/groups_channels_")
    assert result.endswith(".csv")

    # Verificar que o arquivo foi criado
    output_file = Path(result)
    assert output_file.exists()


@pytest.mark.asyncio
async def test_generate_contacts_report_csv(mock_client_with_users, tmp_path):
    """Testa geração de relatório CSV de contatos."""
    output_path = tmp_path / "test_contacts.csv"

    result = await generate_contacts_report(
        mock_client_with_users,
        output_path=str(output_path),
        output_format="csv",
    )

    assert result == str(output_path)
    assert output_path.exists()

    content = output_path.read_text(encoding="utf-8")
    assert "Maria Santos" in content
    assert "Bot de Teste" in content


@pytest.mark.asyncio
async def test_generate_contacts_report_json(mock_client_with_users, tmp_path):
    """Testa geração de relatório JSON de contatos."""
    output_path = tmp_path / "test_contacts.json"

    result = await generate_contacts_report(
        mock_client_with_users,
        output_path=str(output_path),
        output_format="json",
    )

    assert result == str(output_path)
    assert output_path.exists()

    with open(output_path, encoding="utf-8") as f:
        data = json.load(f)

    assert data["report_type"] == "contacts"
    assert data["total"] == 2  # 2 usuários (Channel é ignorado)


@pytest.mark.asyncio
async def test_generate_contacts_report_txt(mock_client_with_users, tmp_path):
    """Testa geração de relatório TXT de contatos."""
    output_path = tmp_path / "test_contacts.txt"

    result = await generate_contacts_report(
        mock_client_with_users,
        output_path=str(output_path),
        output_format="txt",
    )

    assert result == str(output_path)
    assert output_path.exists()

    content = output_path.read_text(encoding="utf-8")
    assert "RELATÓRIO DE CONTATOS" in content
    assert "Maria Santos" in content


@pytest.mark.asyncio
async def test_generate_groups_channels_report_invalid_format(mock_client_with_channels, tmp_path):
    """Testa erro ao passar formato inválido."""
    output_path = tmp_path / "test.invalid"

    with pytest.raises(ValueError, match="Formato não suportado"):
        await generate_groups_channels_report(
            mock_client_with_channels,
            output_path=str(output_path),
            output_format="invalid",
        )
