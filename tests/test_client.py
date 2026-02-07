"""Testes para o módulo client.py."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from telethon.errors import BadRequestError, FloodWaitError
from telethon.tl.functions.channels import LeaveChannelRequest
from telethon.tl.functions.messages import DeleteChatUserRequest, DeleteHistoryRequest

from clean_telegram.client import (
    delete_dialog,
    leave_channel,
    leave_legacy_chat,
    process_dialog,
)


class TestDeleteDialog:
    """Testes para delete_dialog."""

    @pytest.mark.asyncio
    async def test_delete_dialog_dry_run(self, mock_telegram_client):
        """Testa que delete_dialog não executa em dry_run."""
        peer = MagicMock()

        await delete_dialog(mock_telegram_client, peer, dry_run=True)

        mock_telegram_client.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_delete_dialog_executes(self, mock_telegram_client):
        """Testa que delete_dialog executa DeleteHistoryRequest."""
        peer = MagicMock()
        mock_telegram_client.return_value = None

        await delete_dialog(mock_telegram_client, peer, dry_run=False)

        mock_telegram_client.assert_called_once()
        call_args = mock_telegram_client.call_args
        assert isinstance(call_args[0][0], DeleteHistoryRequest)


class TestLeaveChannel:
    """Testes para leave_channel."""

    @pytest.mark.asyncio
    async def test_leave_channel_dry_run(self, mock_telegram_client, mock_channel):
        """Testa que leave_channel não executa em dry_run."""
        await leave_channel(mock_telegram_client, mock_channel, dry_run=True)

        mock_telegram_client.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_leave_channel_executes(self, mock_telegram_client, mock_channel):
        """Testa que leave_channel executa LeaveChannelRequest."""
        mock_telegram_client.return_value = None

        await leave_channel(mock_telegram_client, mock_channel, dry_run=False)

        mock_telegram_client.assert_called_once()
        call_args = mock_telegram_client.call_args
        assert isinstance(call_args[0][0], LeaveChannelRequest)


class TestLeaveLegacyChat:
    """Testes para leave_legacy_chat."""

    @pytest.mark.asyncio
    async def test_leave_legacy_chat_dry_run(self, mock_telegram_client, mock_chat):
        """Testa que leave_legacy_chat não executa em dry_run."""
        await leave_legacy_chat(mock_telegram_client, mock_chat, dry_run=True)

        mock_telegram_client.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_leave_legacy_chat_executes(self, mock_telegram_client, mock_chat):
        """Testa que leave_legacy_chat executa DeleteChatUserRequest."""
        mock_telegram_client.return_value = None

        await leave_legacy_chat(mock_telegram_client, mock_chat, dry_run=False)

        mock_telegram_client.assert_called_once()
        call_args = mock_telegram_client.call_args
        assert isinstance(call_args[0][0], DeleteChatUserRequest)


class TestProcessDialog:
    """Testes para process_dialog."""

    @pytest.mark.asyncio
    async def test_process_channel(self, mock_telegram_client, mock_channel):
        """Testa process_dialog com Channel."""
        mock_telegram_client.return_value = None

        result = await process_dialog(
            mock_telegram_client,
            mock_channel,
            "Test Channel",
            1,
            dry_run=False,
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_process_channel_dry_run(self, mock_telegram_client, mock_channel):
        """Testa process_dialog com Channel em dry_run."""
        result = await process_dialog(
            mock_telegram_client,
            mock_channel,
            "Test Channel",
            1,
            dry_run=True,
        )

        assert result is True
        mock_telegram_client.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_process_chat(self, mock_telegram_client, mock_chat):
        """Testa process_dialog com Chat."""
        mock_telegram_client.return_value = None

        result = await process_dialog(
            mock_telegram_client,
            mock_chat,
            "Test Chat",
            1,
            dry_run=False,
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_process_chat_fallback_on_rpc_error(self, mock_telegram_client, mock_chat):
        """Testa fallback em process_dialog quando RPCError ocorre em Chat."""

        # Configura side_effect para a primeira chamada (DeleteChatUserRequest) levantar erro
        # e mock delete_dialog para o fallback
        mock_telegram_client.side_effect = BadRequestError(None, "Test error")
        mock_telegram_client.delete_dialog = AsyncMock()

        result = await process_dialog(
            mock_telegram_client,
            mock_chat,
            "Test Chat",
            1,
            dry_run=False,
        )

        assert result is True
        mock_telegram_client.delete_dialog.assert_called_once_with(mock_chat)

    @pytest.mark.asyncio
    async def test_process_user(self, mock_telegram_client, mock_user):
        """Testa process_dialog com User."""
        mock_telegram_client.return_value = None

        result = await process_dialog(
            mock_telegram_client,
            mock_user,
            "Test User",
            1,
            dry_run=False,
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_process_bot(self, mock_telegram_client, mock_bot):
        """Testa process_dialog com bot."""
        mock_telegram_client.return_value = None

        result = await process_dialog(
            mock_telegram_client,
            mock_bot,
            "TestBot",
            1,
            dry_run=False,
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_process_unknown_type(self, mock_telegram_client):
        """Testa process_dialog com tipo desconhecido."""
        unknown_entity = MagicMock(spec=object)
        mock_telegram_client.return_value = None

        result = await process_dialog(
            mock_telegram_client,
            unknown_entity,
            "Unknown",
            1,
            dry_run=False,
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_process_dialog_flood_wait_error(self, mock_telegram_client, mock_channel):
        """Testa process_dialog com FloodWaitError."""
        mock_telegram_client.side_effect = FloodWaitError(None, 60)

        result = await process_dialog(
            mock_telegram_client,
            mock_channel,
            "Test Channel",
            1,
            dry_run=False,
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_process_dialog_rpc_error(self, mock_telegram_client, mock_channel):
        """Testa process_dialog com RPCError."""
        mock_telegram_client.side_effect = BadRequestError(None, "Test error")

        result = await process_dialog(
            mock_telegram_client,
            mock_channel,
            "Test Channel",
            1,
            dry_run=False,
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_process_dialog_generic_exception(self, mock_telegram_client, mock_channel):
        """Testa process_dialog com exceção genérica."""
        mock_telegram_client.side_effect = Exception("Unexpected error")

        result = await process_dialog(
            mock_telegram_client,
            mock_channel,
            "Test Channel",
            1,
            dry_run=False,
        )

        assert result is False
