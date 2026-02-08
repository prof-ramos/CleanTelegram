"""Testes para o módulo cleaner.py."""

from unittest import mock

import pytest
from telethon.errors import FloodWaitError, RPCError
from telethon.tl.functions.channels import LeaveChannelRequest
from telethon.tl.functions.messages import DeleteChatUserRequest, DeleteHistoryRequest
from telethon.tl.types import Channel, Chat, User

from clean_telegram import cleaner

# =============================================================================
# Mocks e Fixtures
# =============================================================================


@pytest.fixture
def mock_client():
    """Mock do cliente Telethon."""
    client = mock.AsyncMock()
    # iter_dialogs retorna um iterador, não é uma corrotina em si (no uso do loop)
    # mas o Telethon define como async def ou def que retorna RequestIter.
    # No código: async for d in client.iter_dialogs():
    # Se iter_dialogs for async def, ele retorna coroutine que DEVE ser awaited?
    # NÃO: async for x in func() -> func() deve retornar um async iterator.
    # Se func é async def, func() retorna coroutine. async for NÃO aceita coroutine diretamente.
    # O client.iter_dialogs do Telethon retorna um objeto RequestIter (síncrono na chamada).
    client.iter_dialogs = mock.Mock()

    # Configurar delete_dialog como AsyncMock também
    client.delete_dialog = mock.AsyncMock()
    return client


@pytest.fixture
def mock_channel():
    """Mock de um Channel/Megagroup."""
    channel = mock.Mock(spec=Channel)
    channel.id = 100
    channel.name = "Canal Teste"
    # Adicionar atributo entity para simular retorno de iter_dialogs
    dialog = mock.Mock()
    dialog.entity = channel
    dialog.name = "Canal Teste"
    return dialog


@pytest.fixture
def mock_chat():
    """Mock de um Chat (grupo legado)."""
    chat = mock.Mock(spec=Chat)
    chat.id = 200
    chat.name = "Grupo Legado"
    dialog = mock.Mock()
    dialog.entity = chat
    dialog.name = "Grupo Legado"
    return dialog


@pytest.fixture
def mock_user():
    """Mock de um User (DM)."""
    user = mock.Mock(spec=User)
    user.id = 300
    user.name = "Usuário Teste"
    dialog = mock.Mock()
    dialog.entity = user
    dialog.name = "Usuário Teste"
    return dialog


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


# =============================================================================
# Testes de Funções Helper
# =============================================================================


@pytest.mark.asyncio
async def test_delete_dialog_dry_run(mock_client):
    """Verifica que delete_dialog respeita dry_run."""
    await cleaner.delete_dialog(mock_client, "peer", dry_run=True)
    mock_client.assert_not_called()


@pytest.mark.asyncio
async def test_delete_dialog_execution(mock_client):
    """Verifica chamada correta de DeleteHistoryRequest."""
    await cleaner.delete_dialog(mock_client, "peer", dry_run=False)

    args, _ = mock_client.call_args
    request = args[0]
    assert isinstance(request, DeleteHistoryRequest)
    assert request.peer == "peer"
    assert request.revoke is True


@pytest.mark.asyncio
async def test_leave_channel_dry_run(mock_client):
    """Verifica que leave_channel respeita dry_run."""
    channel = mock.Mock(spec=Channel)
    await cleaner.leave_channel(mock_client, channel, dry_run=True)
    mock_client.assert_not_called()


@pytest.mark.asyncio
async def test_leave_channel_execution(mock_client):
    """Verifica chamada correta de LeaveChannelRequest."""
    channel = mock.Mock(spec=Channel)
    await cleaner.leave_channel(mock_client, channel, dry_run=False)

    args, _ = mock_client.call_args
    request = args[0]
    assert isinstance(request, LeaveChannelRequest)
    assert request.channel == channel


@pytest.mark.asyncio
async def test_leave_legacy_chat_dry_run(mock_client):
    """Verifica que leave_legacy_chat respeita dry_run."""
    chat = mock.Mock(spec=Chat)
    await cleaner.leave_legacy_chat(mock_client, chat, dry_run=True)
    mock_client.assert_not_called()


@pytest.mark.asyncio
async def test_leave_legacy_chat_execution(mock_client):
    """Verifica chamada correta de DeleteChatUserRequest."""
    chat = mock.Mock(spec=Chat)
    chat.id = 123
    await cleaner.leave_legacy_chat(mock_client, chat, dry_run=False)

    args, _ = mock_client.call_args
    request = args[0]
    assert isinstance(request, DeleteChatUserRequest)
    assert request.chat_id == 123


# =============================================================================
# Testes de clean_all_dialogs (Lógica Principal)
# =============================================================================


@pytest.mark.asyncio
async def test_clean_all_dialogs_dry_run_safety(
    mock_client, mock_channel, mock_chat, mock_user
):
    """Garante que NADA é chamado no client em dry_run."""
    mock_client.iter_dialogs.return_value = AsyncIterator(
        [mock_channel, mock_chat, mock_user]
    )

    count = await cleaner.clean_all_dialogs(mock_client, dry_run=True)

    assert count == 3
    # Nenhuma chamada de escrita deve ter ocorrido
    mock_client.assert_not_called()
    mock_client.delete_dialog.assert_not_called()


@pytest.mark.asyncio
async def test_clean_all_dialogs_limit(mock_client, mock_channel, mock_chat):
    """Verifica se o limite interrompe o processamento."""
    mock_client.iter_dialogs.return_value = AsyncIterator(
        [mock_channel, mock_chat] * 10
    )  # Muitos itens

    count = await cleaner.clean_all_dialogs(mock_client, dry_run=True, limit=5)

    assert count == 5


@pytest.mark.asyncio
async def test_clean_all_dialogs_channel(mock_client, mock_channel):
    """Testa saída de canal."""
    mock_client.iter_dialogs.return_value = AsyncIterator([mock_channel])

    await cleaner.clean_all_dialogs(mock_client, dry_run=False)

    args, _ = mock_client.call_args
    assert isinstance(args[0], LeaveChannelRequest)


@pytest.mark.asyncio
async def test_clean_all_dialogs_user(mock_client, mock_user):
    """Testa deleção de conversa com usuário (DM)."""
    mock_client.iter_dialogs.return_value = AsyncIterator([mock_user])

    await cleaner.clean_all_dialogs(mock_client, dry_run=False)

    args, _ = mock_client.call_args
    assert isinstance(args[0], DeleteHistoryRequest)


@pytest.mark.asyncio
async def test_clean_all_dialogs_chat_fallback(mock_client, mock_chat):
    """Testa fallback para delete_dialog quando DeleteChatUserRequest falha."""
    mock_client.iter_dialogs.return_value = AsyncIterator([mock_chat])

    # Configurar side_effect para lançar RPCError na primeira chamada
    # e sucesso na segunda (delete_dialog)
    async def side_effect(request):
        if isinstance(request, DeleteChatUserRequest):
            raise RPCError(None, "Start param required", 400)
        return

    mock_client.side_effect = side_effect

    await cleaner.clean_all_dialogs(mock_client, dry_run=False)

    # Verifica se chamou o fallback
    mock_client.delete_dialog.assert_awaited_once_with(mock_chat.entity)


@pytest.mark.asyncio
async def test_clean_all_dialogs_flood_wait_retry(mock_client, mock_user):
    """Testa retry automático em caso de FloodWaitError."""
    mock_client.iter_dialogs.return_value = AsyncIterator([mock_user])

    # Criar erro FloodWait simulado com assinatura correta do Telethon: (request, capture)
    # capture é usado para popular a propriedade .seconds
    flood_error = FloodWaitError(request=None, capture=1)

    # Simular FloodWait na primeira tentativa (em delete_dialog), sucesso na segunda
    mock_client.side_effect = [flood_error, None]

    # Patch no asyncio.sleep usado internamente pelo cleaner (tanto em safe_sleep quanto no handler de erro)
    with mock.patch(
        "clean_telegram.cleaner.asyncio.sleep", new_callable=mock.AsyncMock
    ) as mock_sleep:
        await cleaner.clean_all_dialogs(mock_client, dry_run=False)
        assert (
            mock_sleep.call_count >= 1
        )  # Garante que sleeper foi chamado (no mínimo no retry)

    # Deve ter chamado duas vezes (1 falha + 1 sucesso)
    assert mock_client.call_count == 2
