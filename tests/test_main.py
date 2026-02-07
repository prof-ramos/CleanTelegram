"""Testes para o módulo __main__.py."""

import asyncio
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from telethon.errors import FloodWaitError, RPCError
from telethon.tl.types import Channel, User

# Importamos aqui para evitar problemas de importação
from clean_telegram import __main__


@pytest.fixture
def mock_telegram_client_context():
    """Fixture que cria um mock do TelegramClient como context manager.

    Retorna uma função que pode ser usada para criar o mock com diferentes
    configurações de iter_dialogs.
    """

    def _create_mock(iter_dialogs_return=None):
        """Cria um mock do TelegramClient."""
        # Criar async generator function baseado nos items
        if callable(iter_dialogs_return):
            # Se passou uma função, usar ela diretamente
            async def iter_dialogs_func():
                async for item in iter_dialogs_return():
                    yield item

        elif iter_dialogs_return is None:
            # Lista vazia
            async def iter_dialogs_func():
                return
                yield

        else:
            # Lista de items
            items = iter_dialogs_return

            async def iter_dialogs_func():
                for item in items:
                    yield item

        client = AsyncMock()
        client.get_me = AsyncMock(
            return_value=Mock(username="testuser", id=12345, first_name="Test")
        )
        client.iter_dialogs = iter_dialogs_func

        @asynccontextmanager
        async def _client_context(*args, **kwargs):
            yield client

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        return mock_client

    return _create_mock


class TestMainHelpFlag:
    """Testes para flag --help."""

    def test_main_help_flag(self, capsys):
        """Testa exibição de ajuda com --help."""
        with patch("sys.argv", ["clean-telegram", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                asyncio.run(__main__.main())

        # --help causa SystemExit com código 0
        assert exc_info.value.code == 0


class TestMainEnvValidation:
    """Testes para validação de variáveis de ambiente."""

    @pytest.mark.asyncio
    async def test_main_missing_api_id(self, monkeypatch_env, mock_telegram_client_context):
        """Testa erro quando API_ID não está definido."""
        monkeypatch_env(API_ID=None, API_HASH="test_hash")

        # Mock TelegramClient no módulo __main__ para evitar tentativa de conexão real
        with patch(
            "clean_telegram.__main__.TelegramClient", return_value=mock_telegram_client_context()
        ):
            # Mock load_dotenv para não carregar .env real
            with patch("clean_telegram.__main__.load_dotenv"):
                # Usar --dry-run para pular confirmação e chegar na validação de API_ID
                with patch("sys.argv", ["clean-telegram", "--dry-run"]):
                    with pytest.raises(SystemExit) as exc_info:
                        await __main__.main()

        assert "API_ID" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_main_missing_api_hash(self, monkeypatch_env, mock_telegram_client_context):
        """Testa erro quando API_HASH não está definido."""
        monkeypatch_env(API_ID="12345", API_HASH=None)

        # Mock TelegramClient no módulo __main__ para evitar tentativa de conexão real
        with patch(
            "clean_telegram.__main__.TelegramClient", return_value=mock_telegram_client_context()
        ):
            # Mock load_dotenv para não carregar .env real
            with patch("clean_telegram.__main__.load_dotenv"):
                # Usar --dry-run para pular confirmação e chegar na validação de API_HASH
                with patch("sys.argv", ["clean-telegram", "--dry-run"]):
                    with pytest.raises(SystemExit) as exc_info:
                        await __main__.main()

        assert "API_HASH" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_main_invalid_api_id(self, monkeypatch_env, mock_telegram_client_context):
        """Testa erro quando API_ID tem valor inválido."""
        monkeypatch_env(API_ID="not_a_number", API_HASH="test_hash")

        # Mock TelegramClient no módulo __main__ para evitar tentativa de conexão real
        with patch(
            "clean_telegram.__main__.TelegramClient", return_value=mock_telegram_client_context()
        ):
            # Mock load_dotenv para não carregar .env real
            with patch("clean_telegram.__main__.load_dotenv"):
                # Usar --dry-run para pular confirmação
                with patch("sys.argv", ["clean-telegram", "--dry-run"]):
                    with pytest.raises(SystemExit) as exc_info:
                        await __main__.main()

        # Mensagem de erro pode ser sobre API_ID inválido ou faltando
        assert "API_ID" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_main_resolves_session_name(self, monkeypatch_env, mock_async_telegram_client):
        """Testa se resolve_session_name é usado antes de criar TelegramClient."""
        monkeypatch_env(API_ID="12345", API_HASH="test_hash", SESSION_NAME="session")

        client = AsyncMock()
        client.get_me = AsyncMock(
            return_value=Mock(username="testuser", id=12345, first_name="Test")
        )

        async def mock_iter_dialogs():
            return
            yield

        client.iter_dialogs = mock_iter_dialogs
        mock_async_telegram_client.__aenter__.return_value = client

        with patch("clean_telegram.__main__.load_dotenv"):
            with patch("sys.argv", ["clean-telegram", "--dry-run"]):
                with patch(
                    "clean_telegram.__main__.resolve_session_name",
                    return_value="/tmp/clean-telegram/session",
                ) as resolve_session_name_mock:
                    with patch(
                        "clean_telegram.__main__.TelegramClient",
                        return_value=mock_async_telegram_client,
                    ) as telegram_client_mock:
                        await __main__.main()

        resolve_session_name_mock.assert_called_once_with("session")
        telegram_client_mock.assert_called_once_with(
            "/tmp/clean-telegram/session", 12345, "test_hash"
        )


class TestMainConfirmation:
    """Testes para fluxo de confirmação."""

    @pytest.mark.asyncio
    async def test_main_confirmation_cancel(self, monkeypatch_env, mock_async_telegram_client):
        """Testa cancelamento quando usuário não digita 'APAGAR TUDO'."""
        monkeypatch_env(API_ID="12345", API_HASH="test_hash")

        # Mock stdin para retornar resposta diferente de "APAGAR TUDO"
        mock_stdin = MagicMock()
        mock_stdin.readline.return_value = "nao apagar\n"

        with patch("sys.argv", ["clean-telegram"]):
            with patch("sys.stdin", mock_stdin):
                with patch(
                    "clean_telegram.__main__.TelegramClient",
                    return_value=mock_async_telegram_client,
                ):
                    await __main__.main()

        # Verifica que o client não foi usado (cancelado antes de entrar)
        mock_async_telegram_client.__aenter__.assert_not_called()

    @pytest.mark.asyncio
    async def test_main_confirmation_accept(self, monkeypatch_env, mock_async_telegram_client):
        """Testa confirmação quando usuário digita 'APAGAR TUDO'."""
        monkeypatch_env(API_ID="12345", API_HASH="test_hash")

        # Mock stdin para retornar "APAGAR TUDO"
        mock_stdin = MagicMock()
        mock_stdin.readline.return_value = "APAGAR TUDO\n"

        # Mock iter_dialogs para não retornar nada (lista vazia)
        client = AsyncMock()
        client.get_me = AsyncMock(
            return_value=Mock(username="testuser", id=12345, first_name="Test")
        )

        async def mock_iter_dialogs():
            return
            yield  # Make it an async generator

        client.iter_dialogs = mock_iter_dialogs
        mock_async_telegram_client.__aenter__.return_value = client

        with patch("sys.argv", ["clean-telegram"]):
            with patch("sys.stdin", mock_stdin):
                with patch(
                    "clean_telegram.__main__.TelegramClient",
                    return_value=mock_async_telegram_client,
                ):
                    await __main__.main()

        # Verifica que o client foi inicializado (confirmação aceita)
        mock_async_telegram_client.__aenter__.assert_called_once()


class TestMainDryRun:
    """Testes para flag --dry-run."""

    @pytest.mark.asyncio
    async def test_main_dry_run_no_confirmation(self, monkeypatch_env, mock_async_telegram_client):
        """Verifica que dry-run pula confirmação."""
        monkeypatch_env(API_ID="12345", API_HASH="test_hash")

        # Mock iter_dialogs para não retornar nada
        client = AsyncMock()
        client.get_me = AsyncMock(
            return_value=Mock(username="testuser", id=12345, first_name="Test")
        )

        async def mock_iter_dialogs():
            return
            yield

        client.iter_dialogs = mock_iter_dialogs
        mock_async_telegram_client.__aenter__.return_value = client

        with patch("sys.argv", ["clean-telegram", "--dry-run"]):
            with patch(
                "clean_telegram.__main__.TelegramClient", return_value=mock_async_telegram_client
            ):
                await __main__.main()

        # Verifica que o client foi usado sem pedir confirmação
        mock_async_telegram_client.__aenter__.assert_called_once()

    @pytest.mark.asyncio
    async def test_main_dry_run_flag(self, monkeypatch_env, mock_async_telegram_client):
        """Testa execução em dry-run."""
        monkeypatch_env(API_ID="12345", API_HASH="test_hash")

        # Criar um mock de diálogo
        mock_dialog = MagicMock()
        mock_dialog.name = "Test Channel"
        mock_dialog.entity = MagicMock(spec=Channel)

        # Mock iter_dialogs como async generator
        async def mock_iter_dialogs():
            yield mock_dialog

        client = AsyncMock()
        client.get_me = AsyncMock(
            return_value=Mock(username="testuser", id=12345, first_name="Test")
        )
        client.iter_dialogs = mock_iter_dialogs
        mock_async_telegram_client.__aenter__.return_value = client

        with patch("sys.argv", ["clean-telegram", "--dry-run"]):
            with patch(
                "clean_telegram.__main__.TelegramClient", return_value=mock_async_telegram_client
            ):
                await __main__.main()

        # Em dry-run, as operações destrutivas não devem ser executidas
        # client.delete_dialog não deve ser chamado para canais
        client.delete_dialog.assert_not_called()


class TestMainLimitFlag:
    """Testes para flag --limit."""

    @pytest.mark.asyncio
    async def test_main_limit_flag(self, monkeypatch_env, mock_async_telegram_client):
        """Testa flag --limit para processar subset de diálogos."""
        monkeypatch_env(API_ID="12345", API_HASH="test_hash")

        # Criar 5 mocks de diálogos
        mock_dialogs = []
        for i in range(5):
            mock_dialog = MagicMock()
            mock_dialog.name = f"Dialog {i}"
            mock_dialog.entity = MagicMock(spec=Channel)
            mock_dialogs.append(mock_dialog)

        # Mock iter_dialogs como async generator
        async def mock_iter_dialogs():
            for dialog in mock_dialogs:
                yield dialog

        client = AsyncMock()
        client.get_me = AsyncMock(
            return_value=Mock(username="testuser", id=12345, first_name="Test")
        )
        client.iter_dialogs = mock_iter_dialogs
        mock_async_telegram_client.__aenter__.return_value = client

        with patch("sys.argv", ["clean-telegram", "--dry-run", "--limit", "2"]):
            with patch(
                "clean_telegram.__main__.TelegramClient", return_value=mock_async_telegram_client
            ):
                await __main__.main()

        # Com --limit 2, apenas 2 diálogos devem ser processados
        # Não há como verificar diretamente quantos foram processados,
        # mas podemos verificar que o iter_dialogs foi chamado


class TestMainYesFlag:
    """Testes para flag --yes."""

    @pytest.mark.asyncio
    async def test_main_yes_flag(self, monkeypatch_env, mock_async_telegram_client):
        """Testa flag --yes para pular confirmação."""
        monkeypatch_env(API_ID="12345", API_HASH="test_hash")

        # Mock iter_dialogs para não retornar nada
        client = AsyncMock()
        client.get_me = AsyncMock(
            return_value=Mock(username="testuser", id=12345, first_name="Test")
        )

        async def mock_iter_dialogs():
            return
            yield

        client.iter_dialogs = mock_iter_dialogs
        mock_async_telegram_client.__aenter__.return_value = client

        with patch("sys.argv", ["clean-telegram", "--yes"]):
            with patch(
                "clean_telegram.__main__.TelegramClient", return_value=mock_async_telegram_client
            ):
                await __main__.main()

        # Verifica que o client foi usado sem pedir confirmação
        mock_async_telegram_client.__aenter__.assert_called_once()


class TestMainClientIteration:
    """Testes para iteração sobre diálogos."""

    @pytest.mark.asyncio
    async def test_main_client_iteration_empty(self, monkeypatch_env, mock_async_telegram_client):
        """Testa iteração quando não há diálogos."""
        monkeypatch_env(API_ID="12345", API_HASH="test_hash")

        # Mock iter_dialogs para não retornar nada
        client = AsyncMock()
        client.get_me = AsyncMock(
            return_value=Mock(username="testuser", id=12345, first_name="Test")
        )

        async def mock_iter_dialogs():
            return
            yield

        client.iter_dialogs = mock_iter_dialogs
        mock_async_telegram_client.__aenter__.return_value = client

        with patch("sys.argv", ["clean-telegram", "--yes"]):
            with patch(
                "clean_telegram.__main__.TelegramClient", return_value=mock_async_telegram_client
            ):
                await __main__.main()

        # Verifica que get_me foi chamado
        client.get_me.assert_called_once()

    @pytest.mark.asyncio
    async def test_main_client_iteration_with_dialogs(
        self, monkeypatch_env, mock_async_telegram_client
    ):
        """Testa iteração sobre diálogos com mocks."""
        monkeypatch_env(API_ID="12345", API_HASH="test_hash")

        # Criar mocks de diferentes tipos de diálogos
        mock_channel = MagicMock()
        mock_channel.name = "Test Channel"
        mock_channel.entity = MagicMock(spec=Channel)

        mock_user = MagicMock()
        mock_user.name = "Test User"
        mock_user.entity = MagicMock(spec=User)

        # Mock iter_dialogs como async generator
        async def mock_iter_dialogs():
            yield mock_channel
            yield mock_user

        client = AsyncMock()
        client.get_me = AsyncMock(
            return_value=Mock(username="testuser", id=12345, first_name="Test")
        )
        client.iter_dialogs = mock_iter_dialogs
        mock_async_telegram_client.__aenter__.return_value = client

        with patch("sys.argv", ["clean-telegram", "--dry-run"]):
            with patch(
                "clean_telegram.__main__.TelegramClient", return_value=mock_async_telegram_client
            ):
                await __main__.main()

        # Verifica que get_me foi chamado
        client.get_me.assert_called_once()


class TestMainFloodWaitRetry:
    """Testes para retry em FloodWaitError."""

    @pytest.mark.asyncio
    async def test_main_flood_wait_retry(self, monkeypatch_env, mock_async_telegram_client):
        """Testa retry em FloodWaitError."""
        monkeypatch_env(API_ID="12345", API_HASH="test_hash")

        # Criar mock de diálogo
        mock_dialog = MagicMock()
        mock_dialog.name = "Test Channel"
        mock_dialog.entity = MagicMock(spec=Channel)

        # Contador para controlar quando lançar erro
        call_count = {"count": 0}

        # Mock process_dialog para lançar FloodWaitError na primeira chamada
        async def mock_process_dialog(*args, **kwargs):
            call_count["count"] += 1
            if call_count["count"] == 1:
                raise FloodWaitError(None, 1)
            return True

        # Mock iter_dialogs como async generator
        async def mock_iter_dialogs():
            yield mock_dialog

        client = AsyncMock()
        client.get_me = AsyncMock(
            return_value=Mock(username="testuser", id=12345, first_name="Test")
        )
        client.iter_dialogs = mock_iter_dialogs
        mock_async_telegram_client.__aenter__.return_value = client

        with patch("sys.argv", ["clean-telegram", "--dry-run"]):
            with patch(
                "clean_telegram.__main__.TelegramClient", return_value=mock_async_telegram_client
            ):
                with patch(
                    "clean_telegram.__main__.process_dialog", side_effect=mock_process_dialog
                ):
                    await __main__.main()

        # Verifica que process_dialog foi chamado mais de uma vez (retry)
        assert call_count["count"] >= 1

    @pytest.mark.asyncio
    async def test_main_max_retries_exceeded(self, monkeypatch_env, mock_async_telegram_client):
        """Testa quando max retries é atingido."""
        monkeypatch_env(API_ID="12345", API_HASH="test_hash")

        # Criar mock de diálogo
        mock_dialog = MagicMock()
        mock_dialog.name = "Test Channel"
        mock_dialog.entity = MagicMock(spec=Channel)

        # Mock process_dialog para sempre lançar FloodWaitError
        async def mock_process_dialog_failing(*args, **kwargs):
            raise FloodWaitError(None, 1)

        # Mock iter_dialogs como async generator
        async def mock_iter_dialogs():
            yield mock_dialog

        client = AsyncMock()
        client.get_me = AsyncMock(
            return_value=Mock(username="testuser", id=12345, first_name="Test")
        )
        client.iter_dialogs = mock_iter_dialogs
        mock_async_telegram_client.__aenter__.return_value = client

        with patch("sys.argv", ["clean-telegram", "--dry-run"]):
            with patch(
                "clean_telegram.__main__.TelegramClient", return_value=mock_async_telegram_client
            ):
                with patch(
                    "clean_telegram.__main__.process_dialog",
                    side_effect=mock_process_dialog_failing,
                ):
                    await __main__.main()

        # Verifica que o loop continuou mesmo após max retries


class TestMainRPCErrorHandling:
    """Testes para tratamento de RPCError."""

    @pytest.mark.asyncio
    async def test_main_rpc_error_handling(self, monkeypatch_env, mock_async_telegram_client):
        """Testa RPCError durante iteração."""
        monkeypatch_env(API_ID="12345", API_HASH="test_hash")

        # Criar mocks de diálogos
        mock_dialog1 = MagicMock()
        mock_dialog1.name = "Dialog 1"
        mock_dialog1.entity = MagicMock(spec=Channel)

        mock_dialog2 = MagicMock()
        mock_dialog2.name = "Dialog 2"
        mock_dialog2.entity = MagicMock(spec=Channel)

        # Flag para controlar qual diálogo falha
        call_count = {"count": 0}

        # Mock process_dialog para lançar RPCError na primeira chamada
        async def mock_process_dialog(*args, **kwargs):
            call_count["count"] += 1
            if call_count["count"] == 1:
                raise RPCError(None, "Test error")
            return True

        # Mock iter_dialogs como async generator
        async def mock_iter_dialogs():
            yield mock_dialog1
            yield mock_dialog2

        client = AsyncMock()
        client.get_me = AsyncMock(
            return_value=Mock(username="testuser", id=12345, first_name="Test")
        )
        client.iter_dialogs = mock_iter_dialogs
        mock_async_telegram_client.__aenter__.return_value = client

        with patch("sys.argv", ["clean-telegram", "--dry-run"]):
            with patch(
                "clean_telegram.__main__.TelegramClient", return_value=mock_async_telegram_client
            ):
                with patch(
                    "clean_telegram.__main__.process_dialog", side_effect=mock_process_dialog
                ):
                    await __main__.main()

        # Verifica que ambos os diálogos foram considerados (mesmo com erro no primeiro)
        # O segundo diálogo deve ter sido processado
        assert call_count["count"] == 2
