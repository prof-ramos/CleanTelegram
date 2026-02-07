"""Configuração e fixtures para testes do CleanTelegram."""

import os
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
from telethon.tl.types import Channel, Chat, Dialog, User


@pytest.fixture
def mock_telegram_client():
    """Fixture que retorna um mock do TelegramClient."""
    client = AsyncMock()
    client.get_me = AsyncMock(return_value=Mock(username="testuser", id=12345, first_name="Test"))
    client.iter_dialogs = AsyncMock()
    client.delete_dialog = AsyncMock()
    return client


@pytest.fixture
def mock_async_telegram_client():
    """Fixture que retorna um AsyncMock do TelegramClient como context manager.

    Este fixture simula o comportamento do TelegramClient quando usado com
    'async with', retornando um client que já implementa os métodos necessários.
    """
    client = AsyncMock()
    client.get_me = AsyncMock(return_value=Mock(username="testuser", id=12345, first_name="Test"))
    client.iter_dialogs = AsyncMock()
    client.delete_dialog = AsyncMock()
    client.return_value = client

    @asynccontextmanager
    async def _client_context(*args, **kwargs):
        yield client

    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    return mock_client


@pytest.fixture
def monkeypatch_env(temp_env_vars):
    """Fixture para monkeypatch variáveis de ambiente.

    Usa temp_env_vars como base e retorna uma função auxiliar para setar vars.
    """

    def set_env(**kwargs):
        for key, value in kwargs.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = str(value)

    return set_env


@pytest.fixture
def mock_channel():
    """Fixture que retorna um mock de Channel (canal/megagrupo)."""
    channel = MagicMock(spec=Channel)
    channel.id = 123456
    channel.title = "Test Channel"
    channel.username = "testchannel"
    return channel


@pytest.fixture
def mock_chat():
    """Fixture que retorna um mock de Chat (grupo legado)."""
    chat = MagicMock(spec=Chat)
    chat.id = 789012
    chat.title = "Test Chat"
    return chat


@pytest.fixture
def mock_user():
    """Fixture que retorna um mock de User (usuário/bot)."""
    user = MagicMock(spec=User)
    user.id = 345678
    user.first_name = "Test"
    user.last_name = "User"
    user.username = "testuser"
    user.bot = False
    return user


@pytest.fixture
def mock_bot():
    """Fixture que retorna um mock de bot."""
    bot = MagicMock(spec=User)
    bot.id = 456789
    bot.first_name = "TestBot"
    bot.last_name = ""  # Bots geralmente não têm last_name
    bot.username = "testbot"
    bot.bot = True
    return bot


@pytest.fixture
def mock_dialog():
    """Fixture que retorna um mock de Dialog."""
    dialog = MagicMock(spec=Dialog)
    dialog.name = "Test Dialog"
    dialog.entity = MagicMock()
    return dialog


@pytest.fixture
def temp_env_vars():
    """Fixture que limpa e restaura variáveis de ambiente."""
    original_env = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def mock_session_file(tmp_path):
    """Fixture que cria um arquivo de sessão temporário."""
    session_file = tmp_path / "test.session"
    session_file.touch()
    return session_file


@pytest.fixture
def mock_dialog_factory():
    """Factory function para criar mocks de Dialog.

    Retorna uma função que pode criar diálogos com parâmetros customizáveis.
    """

    def _create_dialog(
        name: str = "Test Dialog",
        entity=None,
        dialog_id: int = 12345,
    ):
        """Cria um mock de Dialog com parâmetros customizáveis."""
        dialog = MagicMock(spec=Dialog)
        dialog.name = name
        dialog.id = dialog_id
        dialog.entity = entity or MagicMock()
        return dialog

    return _create_dialog
