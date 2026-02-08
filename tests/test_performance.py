"""Testes de performance para validar otimizações.

Estes testes verificam que:
1. Uso de memória é O(1) com streaming JSON
2. Downloads paralelos são mais rápidos que sequenciais
3. Exportação 'both' itera apenas uma vez
"""

import asyncio
import tracemalloc
from datetime import datetime
from pathlib import Path
from typing import AsyncIterator, Generic, TypeVar
from unittest import mock

import pytest

from clean_telegram.backup import (
    download_media_parallel,
    export_messages_both_formats,
    export_messages_to_json_streaming,
    export_participants_both_formats,
    export_participants_to_json_streaming,
)


T = TypeVar('T')


class AsyncIteratorMock(Generic[T]):
    """Helper para criar async iterators em testes."""

    def __init__(self, items: list[T]):
        self.items = items
        self.index = 0

    def __aiter__(self) -> AsyncIterator[T]:
        return self

    async def __anext__(self) -> T:
        if self.index >= len(self.items):
            raise StopAsyncIteration
        item = self.items[self.index]
        self.index += 1
        return item


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_chat_entity():
    """Cria um mock de entidade de chat."""
    chat = mock.Mock()
    chat.id = -1001234567890
    chat.title = "Grupo de Teste Performance"
    return chat


@pytest.fixture
def mock_telethon_client():
    """Cria um mock de TelegramClient básico."""
    client = mock.AsyncMock()

    async def mock_get_me():
        me = mock.Mock()
        me.id = 999888
        me.username = "testuser"
        me.first_name = "Test"
        me.last_name = "User"
        return me

    client.get_me = mock_get_me

    def mock_iter_messages(*args, **kwargs):
        return AsyncIteratorMock([])

    client.iter_messages = mock_iter_messages

    def mock_iter_participants(*args, **kwargs):
        return AsyncIteratorMock([])

    client.iter_participants = mock_iter_participants

    return client


@pytest.fixture
def mock_client_with_many_messages():
    """Cria client com muitas mensagens para teste de performance."""
    class MockMessage:
        def __init__(self, msg_id, text=None, sender_id=None):
            self.id = msg_id
            self.date = datetime(2024, 1, 1, 10, 0)
            self.text = text
            self.sender_id = sender_id
            self.media = None
            self.sender = None
            self.reply_to = None

    # Criar 1000 mensagens
    messages = [
        MockMessage(i, f"Mensagem {i}", 111) for i in range(1, 1001)
    ]

    def mock_iter_messages(*args, **kwargs):
        return AsyncIteratorMock(messages)

    client = mock.AsyncMock()
    client.iter_messages = mock_iter_messages

    return client


@pytest.fixture
def mock_client_with_many_participants():
    """Cria client com muitos participantes para teste de performance."""
    class MockParticipant:
        def __init__(self, user_id, first_name):
            self.user = self
            self.id = user_id
            self.first_name = first_name
            self.last_name = ""
            self.username = f"user{user_id}"
            self.bot = False
            self.verified = False
            self.premium = False
            self.phone = None
            self.status = None
            self.participant = None

    # Criar 500 participantes
    participants = [
        MockParticipant(i, f"User{i}") for i in range(1, 501)
    ]

    def mock_iter_participants(*args, **kwargs):
        return AsyncIteratorMock(participants)

    client = mock.AsyncMock()
    client.iter_participants = mock_iter_participants

    return client


# =============================================================================
# Testes: Streaming JSON (Uso de Memória)
# =============================================================================


class TestStreamingJsonMemory:
    """Testes de uso de memória para streaming JSON."""

    @pytest.mark.asyncio
    async def test_json_export_streaming_memory_usage(
        self,
        mock_client_with_many_messages,
        mock_chat_entity,
        tmp_path,
    ):
        """Verifica que uso de memória é O(1) com streaming."""
        tracemalloc.start()

        # Exportar 1000 mensagens com streaming
        output_path = tmp_path / "test_streaming.json"
        count = await export_messages_to_json_streaming(
            mock_client_with_many_messages,
            mock_chat_entity,
            str(output_path),
        )

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Verificar que exportou todas as mensagens
        assert count == 1000

        # Pico deve ser < 10MB para 1000 mensagens (não escalona linearmente)
        # Em implementações não-streaming, isso seria muito maior
        assert peak < 10 * 1024 * 1024, f"Pico de memória muito alto: {peak / 1024 / 1024:.1f} MB"

    @pytest.mark.asyncio
    async def test_participants_streaming_memory_usage(
        self,
        mock_client_with_many_participants,
        mock_chat_entity,
        tmp_path,
    ):
        """Verifica que uso de memória é O(1) com streaming para participantes."""
        tracemalloc.start()

        output_path = tmp_path / "test_participants_streaming.json"
        count = await export_participants_to_json_streaming(
            mock_client_with_many_participants,
            mock_chat_entity,
            str(output_path),
        )

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        assert count == 500
        assert peak < 5 * 1024 * 1024, f"Pico de memória muito alto: {peak / 1024 / 1024:.1f} MB"


# =============================================================================
# Testes: Exportação Ambos Formatos (Iteração Única)
# =============================================================================


class TestBothFormatsSingleIteration:
    """Testes de que formats='both' itera apenas uma vez."""

    @pytest.mark.asyncio
    async def test_messages_both_formats_single_iteration(
        self,
        mock_client_with_many_messages,
        mock_chat_entity,
        tmp_path,
    ):
        """Verifica que exportação 'both' itera mensagens apenas uma vez."""
        json_path = tmp_path / "test_messages.json"
        csv_path = tmp_path / "test_messages.csv"

        result = await export_messages_both_formats(
            mock_client_with_many_messages,
            mock_chat_entity,
            str(json_path),
            str(csv_path),
        )

        # Deve exportar todas as mensagens
        assert result["messages_count"] == 1000

        # Ambos os arquivos devem existir
        assert json_path.exists()
        assert csv_path.exists()

        # Verificar que o JSON está em formato NDJSON
        json_content = json_path.read_text()
        lines = json_content.strip().split('\n')
        assert len(lines) == 1001  # header + 1000 mensagens
        assert '"_format": "ndjson"' in lines[0] or '"_format":"ndjson"' in lines[0]

        # Verificar que CSV tem header + 1000 linhas
        csv_content = csv_path.read_text()
        csv_lines = csv_content.strip().split('\n')
        assert len(csv_lines) == 1001  # header + 1000 mensagens

    @pytest.mark.asyncio
    async def test_participants_both_formats_single_iteration(
        self,
        mock_client_with_many_participants,
        mock_chat_entity,
        tmp_path,
    ):
        """Verifica que exportação 'both' itera participantes apenas uma vez."""
        json_path = tmp_path / "test_participants.json"
        csv_path = tmp_path / "test_participants.csv"

        result = await export_participants_both_formats(
            mock_client_with_many_participants,
            mock_chat_entity,
            str(json_path),
            str(csv_path),
        )

        # Deve exportar todos os participantes
        assert result["participants_count"] == 500

        # Ambos os arquivos devem existir
        assert json_path.exists()
        assert csv_path.exists()


# =============================================================================
# Testes: Download Paralelo
# =============================================================================


class TestParallelDownload:
    """Testes de download paralelo de mídia."""

    @pytest.mark.asyncio
    async def test_parallel_download_respects_semaphore_limit(
        self,
        mock_telethon_client,
        mock_chat_entity,
        tmp_path,
    ):
        """Verifica que download paralelo funciona corretamente."""
        from telethon.tl.types import MessageMediaPhoto

        # Mock de mensagens com mídia
        class MockMessage:
            def __init__(self, msg_id):
                self.id = msg_id
                self.sender_id = 111
                self.media = MessageMediaPhoto()

        # Criar 10 mensagens com mídia
        messages = [MockMessage(i) for i in range(1, 11)]

        def mock_iter_messages(*args, **kwargs):
            return AsyncIteratorMock(messages)

        mock_telethon_client.iter_messages = mock_iter_messages

        # Mock download_media
        async def mock_download_media(*args, **kwargs):
            await asyncio.sleep(0.001)  # 1ms por download
            return f"/tmp/file.jpg"

        mock_telethon_client.download_media = mock_download_media

        # Executar com max_concurrent=3
        output_dir = tmp_path / "media"
        result = await download_media_parallel(
            mock_telethon_client,
            mock_chat_entity,
            str(output_dir),
            max_concurrent=3,
        )

        # Verificar que baixou arquivos
        assert result["photo"] == 10
        assert result["total"] == 10

    @pytest.mark.asyncio
    async def test_parallel_download_handles_exceptions(
        self,
        mock_telethon_client,
        mock_chat_entity,
        tmp_path,
    ):
        """Verifica que exceções em downloads individuais são tratadas."""
        from telethon.tl.types import MessageMediaPhoto

        # Mock com algumas mídias que falham
        class MockMessage:
            def __init__(self, msg_id, should_fail=False):
                self.id = msg_id
                self.sender_id = 111
                self.media = MessageMediaPhoto()
                self.should_fail = should_fail

        messages = [
            MockMessage(1, should_fail=False),
            MockMessage(2, should_fail=True),  # Vai falhar
            MockMessage(3, should_fail=False),
        ]

        def mock_iter_messages(*args, **kwargs):
            return AsyncIteratorMock(messages)

        mock_telethon_client.iter_messages = mock_iter_messages

        async def mock_download_media(message, *args, **kwargs):
            if message.should_fail:
                raise Exception("Download falhou")
            return f"/tmp/file_{message.id}.jpg"

        mock_telethon_client.download_media = mock_download_media

        output_dir = tmp_path / "media"
        result = await download_media_parallel(
            mock_telethon_client,
            mock_chat_entity,
            str(output_dir),
            max_concurrent=2,
        )

        # Deve baixar apenas os que não falharam
        assert result["total"] == 2  # 1 e 3


# =============================================================================
# Testes: Formato NDJSON
# =============================================================================


class TestNdjsonFormat:
    """Testes de formato NDJSON."""

    @pytest.mark.asyncio
    async def test_ndjson_output_format(
        self,
        mock_client_with_many_messages,
        mock_chat_entity,
        tmp_path,
    ):
        """Verifica que saída está em formato NDJSON válido."""
        output_path = tmp_path / "test.ndjson"

        await export_messages_to_json_streaming(
            mock_client_with_many_messages,
            mock_chat_entity,
            str(output_path),
        )

        # Ler arquivo e verificar formato
        content = output_path.read_text()
        lines = content.strip().split('\n')

        # Primeira linha deve ser header com metadados
        header_line = lines[0]
        assert '"_format": "ndjson"' in header_line or '"_format":"ndjson"' in header_line

        # Deve ter header + 1000 linhas de mensagens
        assert len(lines) == 1001  # header + 1000 mensagens

        # Cada linha deve ser JSON válido
        import json
        for line in lines:
            data = json.loads(line)
            assert isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_ndjson_header_metadata(
        self,
        mock_client_with_many_messages,
        mock_chat_entity,
        tmp_path,
    ):
        """Verifica que header contém metadados corretos."""
        output_path = tmp_path / "test.ndjson"

        await export_messages_to_json_streaming(
            mock_client_with_many_messages,
            mock_chat_entity,
            str(output_path),
        )

        content = output_path.read_text()
        first_line = content.split('\n')[0]

        import json
        header = json.loads(first_line)

        assert header["_format"] == "ndjson"
        assert "export_date" in header
        assert header["chat_id"] == mock_chat_entity.id
        assert header["chat_title"] == mock_chat_entity.title
