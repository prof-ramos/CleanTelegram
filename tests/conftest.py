"""Configuração de testes para CleanTelegram."""

import sys
from pathlib import Path

import pytest

# Adicionar src/ ao path ANTES de qualquer outra coisa para importar o módulo correto
src_path = Path(__file__).parent.parent / "src"
if src_path.exists() and src_path.is_dir():
    sys.path.insert(0, str(src_path))
else:
    raise RuntimeError(f"Diretório src/ não encontrado em {src_path}. Verifique a estrutura do projeto.")

# Remover o diretório raiz do path para evitar conflito
root_path = Path(__file__).parent.parent
root_path_str = str(root_path)
# Remover TODAS as ocorrências, não apenas a primeira
sys.path = [p for p in sys.path if p != root_path_str]

# =============================================================================
# AsyncIteratorMock Centralizado
# =============================================================================

class AsyncIteratorMock:
    """Mock para iteradores assíncronos (usado em iter_dialogs, iter_messages, etc.)."""

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
# Rich Console Mock
# =============================================================================

@pytest.fixture
def mock_console(mocker):
    """Mock do console global Rich para testes de UI.

    NOTA: Se patch "clean_telegram.ui.console" não funcionar devido a
    import time, usar patch.object no local de importação.
    """
    return mocker.patch("clean_telegram.ui.console", autospec=True)


# =============================================================================
# sys.stdin Mock para input do usuário
# =============================================================================

@pytest.fixture
def mock_stdin(monkeypatch):
    """Factory para mock de builtins.input em testes de CLI interativo."""
    def _make_input(text: str):
        monkeypatch.setattr("builtins.input", lambda _="": text)
    return _make_input


# =============================================================================
# Telethon Client Mock Padrão
# =============================================================================

@pytest.fixture
def mock_telethon_client(mocker):
    """Mock padrão de TelegramClient com configurações básicas."""
    client = mocker.AsyncMock()
    client.iter_dialogs = mocker.Mock(return_value=AsyncIteratorMock([]))
    client.get_me = mocker.AsyncMock()
    return client


@pytest.fixture
def mock_chat_entity(mocker):
    """Mock padrão de entidade de chat (Channel)."""
    # Criar classe sentinela para evitar mutação de Mock
    class FakeChannel:
        pass

    chat = mocker.Mock(spec=FakeChannel)
    chat.id = 123456
    chat.title = "Grupo de Teste"
    return chat


# =============================================================================
# Telethon Logger Fixture
# =============================================================================

@pytest.fixture
def telethon_logger():
    """Fixture para logger do Telethon com limpeza garantida."""
    import logging
    logger = logging.getLogger("telethon")
    original_level = logger.level
    yield logger
    # Teardown: sempre restaurar nível original
    logger.setLevel(original_level)
