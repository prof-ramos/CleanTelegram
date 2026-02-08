"""Testes estendidos para o módulo cleaner.py.

Cobre os caminhos de erro não testados: tipo de entidade desconhecido,
RPCError e Exception genérica no loop de retry.
"""

from unittest import mock

import pytest
from telethon.errors import RPCError

from clean_telegram import cleaner


class AsyncIterator:
    """Helper para iterar async em testes."""

    def __init__(self, items):
        self.items = items

    def __aiter__(self):
        self.iter = iter(self.items)
        return self

    async def __anext__(self):
        try:
            return next(self.iter)
        except StopIteration:
            raise StopAsyncIteration


@pytest.fixture
def mock_client():
    client = mock.AsyncMock()
    client.iter_dialogs = mock.Mock()
    client.delete_dialog = mock.AsyncMock()
    return client


# =============================================================================
# Testes: _process_dialog com tipo desconhecido
# =============================================================================


class TestProcessDialogUnknownType:
    """Testes para _process_dialog com entidade de tipo desconhecido."""

    @pytest.mark.asyncio
    async def test_unknown_entity_type_executes_delete_dialog(self, mock_client):
        """Entidade que não é Channel/Chat/User deve usar client.delete_dialog."""
        unknown_entity = mock.Mock()  # Sem spec -> não é Channel, Chat nem User

        dialog = mock.Mock()
        dialog.entity = unknown_entity
        dialog.name = "Unknown"

        mock_client.iter_dialogs.return_value = AsyncIterator([dialog])

        count = await cleaner.clean_all_dialogs(mock_client, dry_run=False)

        assert count == 1
        mock_client.delete_dialog.assert_awaited_once_with(unknown_entity)

    @pytest.mark.asyncio
    async def test_unknown_entity_type_dry_run(self, mock_client):
        """Entidade desconhecida em dry_run não deve chamar delete_dialog."""
        unknown_entity = mock.Mock()

        dialog = mock.Mock()
        dialog.entity = unknown_entity
        dialog.name = "Unknown"

        mock_client.iter_dialogs.return_value = AsyncIterator([dialog])

        count = await cleaner.clean_all_dialogs(mock_client, dry_run=True)

        assert count == 1
        mock_client.delete_dialog.assert_not_awaited()


# =============================================================================
# Testes: clean_all_dialogs error handlers
# =============================================================================


class TestCleanAllDialogsErrorHandlers:
    """Testes para os handlers de RPCError e Exception genérica no retry loop."""

    @pytest.mark.asyncio
    async def test_rpc_error_breaks_loop_for_dialog(self, mock_client):
        """RPCError (não FloodWait) deve logar e pular para o próximo diálogo."""
        from telethon.tl.types import Channel

        entity = mock.Mock(spec=Channel)
        dialog = mock.Mock()
        dialog.entity = entity
        dialog.name = "RPCError Channel"

        mock_client.iter_dialogs.return_value = AsyncIterator([dialog])

        # Forçar RPCError ao tentar sair do canal
        mock_client.side_effect = RPCError(None, "CHAT_WRITE_FORBIDDEN", 403)

        count = await cleaner.clean_all_dialogs(mock_client, dry_run=False)

        # Deve contar como processado mesmo com erro
        assert count == 1

    @pytest.mark.asyncio
    async def test_unexpected_exception_breaks_loop_for_dialog(self, mock_client):
        """Exception genérica deve logar e pular para o próximo diálogo."""
        from telethon.tl.types import Channel

        entity = mock.Mock(spec=Channel)
        dialog = mock.Mock()
        dialog.entity = entity
        dialog.name = "Exception Channel"

        mock_client.iter_dialogs.return_value = AsyncIterator([dialog])

        # Forçar exceção genérica
        mock_client.side_effect = RuntimeError("connection lost")

        count = await cleaner.clean_all_dialogs(mock_client, dry_run=False)

        assert count == 1

    @pytest.mark.asyncio
    async def test_error_does_not_stop_processing_other_dialogs(self, mock_client):
        """Erro em um diálogo não deve impedir processamento dos seguintes."""
        from telethon.tl.types import Channel, User

        error_entity = mock.Mock(spec=Channel)
        error_dialog = mock.Mock()
        error_dialog.entity = error_entity
        error_dialog.name = "Error Channel"

        ok_entity = mock.Mock(spec=User)
        ok_dialog = mock.Mock()
        ok_dialog.entity = ok_entity
        ok_dialog.name = "OK User"

        mock_client.iter_dialogs.return_value = AsyncIterator([error_dialog, ok_dialog])

        call_count = {"n": 0}

        async def side_effect(request):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise RPCError(None, "CHAT_WRITE_FORBIDDEN", 403)
            return None

        mock_client.side_effect = side_effect

        count = await cleaner.clean_all_dialogs(mock_client, dry_run=False)

        assert count == 2
        assert call_count["n"] == 2
