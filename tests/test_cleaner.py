"""Testes para o módulo cleaner.py."""

from unittest import mock

import pytest
from telethon.errors import FloodWaitError, RPCError
from telethon.tl.functions.channels import LeaveChannelRequest
from telethon.tl.functions.messages import DeleteChatUserRequest, DeleteHistoryRequest
from telethon.tl.types import Channel, Chat, User

from clean_telegram import cleaner
from clean_telegram.cleaner import CleanFilter
from tests.conftest import AsyncIteratorMock

# =============================================================================
# Mocks e Fixtures
# =============================================================================


@pytest.fixture
def mock_client():
    """Mock do cliente Telethon."""
    client = mock.AsyncMock()
    client.iter_dialogs = mock.Mock()
    client.delete_dialog = mock.AsyncMock()
    return client


@pytest.fixture
def mock_channel():
    """Mock de um Channel/Megagroup."""
    channel = mock.Mock(spec=Channel)
    channel.id = 100
    channel.username = None
    dialog = mock.Mock()
    dialog.entity = channel
    dialog.name = "Canal Teste"
    dialog.date = None
    return dialog


@pytest.fixture
def mock_chat():
    """Mock de um Chat (grupo legado)."""
    chat = mock.Mock(spec=Chat)
    chat.id = 200
    chat.username = None
    dialog = mock.Mock()
    dialog.entity = chat
    dialog.name = "Grupo Legado"
    dialog.date = None
    return dialog


@pytest.fixture
def mock_user():
    """Mock de um User (DM)."""
    user = mock.Mock(spec=User)
    user.id = 300
    user.username = None
    dialog = mock.Mock()
    dialog.entity = user
    dialog.name = "Usuário Teste"
    dialog.date = None
    return dialog


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
    mock_client.iter_dialogs.return_value = AsyncIteratorMock(
        [mock_channel, mock_chat, mock_user]
    )

    processed, skipped = await cleaner.clean_all_dialogs(mock_client, dry_run=True)

    assert processed == 3
    assert skipped == 0
    mock_client.assert_not_called()
    mock_client.delete_dialog.assert_not_called()


@pytest.mark.asyncio
async def test_clean_all_dialogs_limit(mock_client, mock_channel, mock_chat):
    """Verifica se o limite interrompe o processamento."""
    mock_client.iter_dialogs.return_value = AsyncIteratorMock(
        [mock_channel, mock_chat] * 10
    )

    processed, skipped = await cleaner.clean_all_dialogs(mock_client, dry_run=True, limit=5)

    assert processed == 5


@pytest.mark.asyncio
async def test_clean_all_dialogs_channel(mock_client, mock_channel):
    """Testa saída de canal."""
    mock_client.iter_dialogs.return_value = AsyncIteratorMock([mock_channel])

    await cleaner.clean_all_dialogs(mock_client, dry_run=False)

    args, _ = mock_client.call_args
    assert isinstance(args[0], LeaveChannelRequest)


@pytest.mark.asyncio
async def test_clean_all_dialogs_user(mock_client, mock_user):
    """Testa deleção de conversa com usuário (DM)."""
    mock_client.iter_dialogs.return_value = AsyncIteratorMock([mock_user])

    await cleaner.clean_all_dialogs(mock_client, dry_run=False)

    args, _ = mock_client.call_args
    assert isinstance(args[0], DeleteHistoryRequest)


@pytest.mark.asyncio
async def test_clean_all_dialogs_chat_fallback(mock_client, mock_chat):
    """Testa fallback para delete_dialog quando DeleteChatUserRequest falha."""
    mock_client.iter_dialogs.return_value = AsyncIteratorMock([mock_chat])

    async def side_effect(request):
        if isinstance(request, DeleteChatUserRequest):
            raise RPCError(None, "Start param required", 400)
        return

    mock_client.side_effect = side_effect

    await cleaner.clean_all_dialogs(mock_client, dry_run=False)

    mock_client.delete_dialog.assert_awaited_once_with(mock_chat.entity)


@pytest.mark.asyncio
async def test_clean_all_dialogs_flood_wait_retry(mock_client, mock_user):
    """Testa retry automático em caso de FloodWaitError."""
    mock_client.iter_dialogs.return_value = AsyncIteratorMock([mock_user])

    flood_error = FloodWaitError(request=None, capture=1)
    mock_client.side_effect = [flood_error, None]

    with mock.patch(
        "clean_telegram.cleaner.asyncio.sleep", new_callable=mock.AsyncMock
    ) as mock_sleep:
        await cleaner.clean_all_dialogs(mock_client, dry_run=False)
        assert mock_sleep.call_count >= 1

    assert mock_client.call_count == 2


@pytest.mark.asyncio
async def test_clean_all_dialogs_flood_wait_calls_callback(mock_client, mock_user):
    """Testa que on_floodwait callback é chamado ao receber FloodWaitError."""
    mock_client.iter_dialogs.return_value = AsyncIteratorMock([mock_user])

    flood_error = FloodWaitError(request=None, capture=10)
    mock_client.side_effect = [flood_error, None]

    callback = mock.Mock()

    with mock.patch("clean_telegram.cleaner.asyncio.sleep", new_callable=mock.AsyncMock):
        await cleaner.clean_all_dialogs(
            mock_client, dry_run=False, on_floodwait=callback
        )

    # Callback deve ter sido chamado com (nome, segundos, tentativa, max_retries)
    callback.assert_called_once()
    args = callback.call_args[0]
    assert args[0] == "Usuário Teste"  # dialog name
    assert args[1] >= 5               # wait_seconds (mínimo 5)
    assert args[2] == 1               # attempt
    assert args[3] == 5               # max_retries


# =============================================================================
# Testes de CleanFilter
# =============================================================================


class TestCleanFilter:
    """Testes para filtragem seletiva via CleanFilter."""

    @pytest.mark.asyncio
    async def test_filter_by_type_user_only(self, mock_client, mock_channel, mock_chat, mock_user):
        """Deve processar apenas Users quando types=['user']."""
        mock_client.iter_dialogs.return_value = AsyncIteratorMock(
            [mock_channel, mock_chat, mock_user]
        )

        f = CleanFilter(types=["user"])
        processed, skipped = await cleaner.clean_all_dialogs(
            mock_client, dry_run=True, clean_filter=f
        )

        assert processed == 1
        assert skipped == 2

    @pytest.mark.asyncio
    async def test_filter_whitelist_by_id(self, mock_client, mock_user):
        """Deve pular diálogos com ID na whitelist."""
        mock_client.iter_dialogs.return_value = AsyncIteratorMock([mock_user])

        f = CleanFilter(whitelist=["300"])  # user.id = 300
        processed, skipped = await cleaner.clean_all_dialogs(
            mock_client, dry_run=True, clean_filter=f
        )

        assert processed == 0
        assert skipped == 1

    @pytest.mark.asyncio
    async def test_filter_whitelist_by_name(self, mock_client, mock_user):
        """Deve pular diálogos com nome na whitelist."""
        mock_client.iter_dialogs.return_value = AsyncIteratorMock([mock_user])

        f = CleanFilter(whitelist=["Usuário Teste"])
        processed, skipped = await cleaner.clean_all_dialogs(
            mock_client, dry_run=True, clean_filter=f
        )

        assert processed == 0
        assert skipped == 1

    @pytest.mark.asyncio
    async def test_filter_name_pattern(self, mock_client, mock_channel, mock_user):
        """Deve processar apenas diálogos com padrão de nome."""
        mock_client.iter_dialogs.return_value = AsyncIteratorMock([mock_channel, mock_user])

        f = CleanFilter(name_pattern="Canal")  # Só "Canal Teste"
        processed, skipped = await cleaner.clean_all_dialogs(
            mock_client, dry_run=True, clean_filter=f
        )

        assert processed == 1
        assert skipped == 1

    @pytest.mark.asyncio
    async def test_empty_filter_processes_all(self, mock_client, mock_channel, mock_user):
        """Filtro vazio deve processar todos os diálogos."""
        mock_client.iter_dialogs.return_value = AsyncIteratorMock([mock_channel, mock_user])

        f = CleanFilter()
        processed, skipped = await cleaner.clean_all_dialogs(
            mock_client, dry_run=True, clean_filter=f
        )

        assert processed == 2
        assert skipped == 0

    @pytest.mark.asyncio
    async def test_no_filter_processes_all(self, mock_client, mock_channel, mock_user):
        """Sem filtro, deve processar todos os diálogos."""
        mock_client.iter_dialogs.return_value = AsyncIteratorMock([mock_channel, mock_user])

        processed, skipped = await cleaner.clean_all_dialogs(mock_client, dry_run=True)

        assert processed == 2
        assert skipped == 0

    @pytest.mark.asyncio
    async def test_dialog_name_fallback_when_none(self, mock_client):
        """Deve usar title/first_name quando d.name é None."""
        user = mock.Mock(spec=User)
        user.id = 999
        user.username = None
        user.first_name = "João"

        dialog = mock.Mock()
        dialog.entity = user
        dialog.name = None  # name é None
        dialog.date = None

        mock_client.iter_dialogs.return_value = AsyncIteratorMock([dialog])

        # Não deve lançar erro
        processed, skipped = await cleaner.clean_all_dialogs(mock_client, dry_run=True)
        assert processed == 1
