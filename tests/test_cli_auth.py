"""Testes de autenticação do CLI (modo usuário e modo bot)."""

from unittest import mock

import pytest
from telethon.errors import RPCError

from clean_telegram import cli


def get_mock_auth_config(
    overrides: dict[str, object] | None = None,
) -> cli.AuthConfig:
    """Factory de AuthConfig com defaults seguros."""
    data: dict[str, object] = {
        "mode": "user",
        "session_name": "session",
        "bot_token": None,
    }
    if overrides:
        data.update(overrides)
    return cli.AuthConfig(**data)


def get_mock_rpc_error(message: str = "CHAT_ADMIN_REQUIRED", code: int = 400) -> RPCError:
    """Factory de RPCError para cenários de erro Telegram."""
    return RPCError(None, message, code)


class TestResolveAuthConfig:
    def test_should_use_user_mode_by_default(self, monkeypatch):
        monkeypatch.delenv("BOT_TOKEN", raising=False)
        monkeypatch.delenv("SESSION_NAME", raising=False)
        monkeypatch.delenv("BOT_SESSION_NAME", raising=False)

        auth_config = cli.resolve_auth_config()

        assert auth_config.mode == "user"
        assert auth_config.session_name == "session"
        assert auth_config.bot_token is None

    def test_should_prioritize_bot_mode_when_bot_token_exists(self, monkeypatch):
        monkeypatch.setenv("BOT_TOKEN", "123456:abc-token")
        monkeypatch.setenv("BOT_SESSION_NAME", "my_bot_session")
        monkeypatch.setenv("SESSION_NAME", "user_session_should_be_ignored")

        auth_config = cli.resolve_auth_config()

        assert auth_config.mode == "bot"
        assert auth_config.session_name == "my_bot_session"
        assert auth_config.bot_token == "123456:abc-token"

    def test_should_use_default_bot_session_name_when_not_provided(self, monkeypatch):
        monkeypatch.setenv("BOT_TOKEN", "999:bot-token")
        monkeypatch.delenv("BOT_SESSION_NAME", raising=False)

        auth_config = cli.resolve_auth_config()

        assert auth_config.mode == "bot"
        assert auth_config.session_name == "bot_session"


class TestCreateClient:
    def test_should_create_client_with_bot_session_when_bot_token_exists(self, monkeypatch):
        monkeypatch.setenv("API_ID", "12345")
        monkeypatch.setenv("API_HASH", "hash123")
        monkeypatch.setenv("BOT_TOKEN", "999:bot-token")
        monkeypatch.setenv("BOT_SESSION_NAME", "bot_session_custom")

        telegram_client_ctor = mock.Mock(return_value=mock.sentinel.client)
        monkeypatch.setattr(cli, "TelegramClient", telegram_client_ctor)

        client, auth_config = cli.create_client()

        assert client is mock.sentinel.client
        assert auth_config.mode == "bot"
        assert auth_config.session_name == "bot_session_custom"
        telegram_client_ctor.assert_called_once_with(
            "bot_session_custom", 12345, "hash123"
        )

    def test_should_create_client_with_user_session_without_bot_token(self, monkeypatch):
        monkeypatch.setenv("API_ID", "67890")
        monkeypatch.setenv("API_HASH", "hash456")
        monkeypatch.setenv("SESSION_NAME", "legacy_user_session")
        monkeypatch.delenv("BOT_TOKEN", raising=False)

        telegram_client_ctor = mock.Mock(return_value=mock.sentinel.user_client)
        monkeypatch.setattr(cli, "TelegramClient", telegram_client_ctor)

        client, auth_config = cli.create_client()

        assert client is mock.sentinel.user_client
        assert auth_config.mode == "user"
        assert auth_config.session_name == "legacy_user_session"
        telegram_client_ctor.assert_called_once_with(
            "legacy_user_session", 67890, "hash456"
        )


class TestStartClient:
    @pytest.mark.asyncio
    async def test_should_start_with_bot_token_in_bot_mode(self):
        client = mock.AsyncMock()
        auth_config = get_mock_auth_config(
            {"mode": "bot", "session_name": "bot_session", "bot_token": "123:token"}
        )

        await cli.start_client(client, auth_config)

        client.start.assert_awaited_once_with(bot_token="123:token")

    @pytest.mark.asyncio
    async def test_should_start_without_bot_token_in_user_mode(self):
        client = mock.AsyncMock()
        auth_config = get_mock_auth_config()

        await cli.start_client(client, auth_config)

        client.start.assert_awaited_once_with()


class TestWarnBotPermissions:
    def test_should_warn_for_clean_mode_in_bot_auth(self, caplog):
        auth_config = get_mock_auth_config(
            {"mode": "bot", "session_name": "bot_session", "bot_token": "123:token"}
        )

        with caplog.at_level("WARNING"):
            cli.warn_bot_permissions(
                auth_config=auth_config,
                is_clean_mode=True,
                is_backup_mode=False,
            )

        assert "Modo bot ativo" in caplog.text

    def test_should_warn_for_backup_mode_in_bot_auth(self, caplog):
        auth_config = get_mock_auth_config(
            {"mode": "bot", "session_name": "bot_session", "bot_token": "123:token"}
        )

        with caplog.at_level("WARNING"):
            cli.warn_bot_permissions(
                auth_config=auth_config,
                is_clean_mode=False,
                is_backup_mode=True,
            )

        assert "Modo bot ativo" in caplog.text

    def test_should_not_warn_for_reports_in_bot_auth(self, caplog):
        auth_config = get_mock_auth_config(
            {"mode": "bot", "session_name": "bot_session", "bot_token": "123:token"}
        )

        with caplog.at_level("WARNING"):
            cli.warn_bot_permissions(
                auth_config=auth_config,
                is_clean_mode=False,
                is_backup_mode=False,
            )

        assert "Modo bot ativo" not in caplog.text

    def test_should_not_warn_in_user_mode(self, caplog):
        auth_config = get_mock_auth_config()

        with caplog.at_level("WARNING"):
            cli.warn_bot_permissions(
                auth_config=auth_config,
                is_clean_mode=True,
                is_backup_mode=True,
            )

        assert "Modo bot ativo" not in caplog.text


class TestFormatRpcError:
    def test_should_return_bot_friendly_message_in_bot_mode(self):
        error = get_mock_rpc_error()
        auth_config = get_mock_auth_config(
            {"mode": "bot", "session_name": "bot_session", "bot_token": "123:token"}
        )

        message = cli.format_rpc_error(error, auth_config)

        assert "Falha em modo bot" in message
        assert "permissões necessárias" in message
        assert "CHAT_ADMIN_REQUIRED" in message

    def test_should_return_generic_message_in_user_mode(self):
        error = get_mock_rpc_error("FLOOD_WAIT", 420)
        auth_config = get_mock_auth_config()

        message = cli.format_rpc_error(error, auth_config)

        assert "Erro da API do Telegram" in message
        assert "FLOOD_WAIT" in message
