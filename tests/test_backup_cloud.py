"""Testes para funcionalidade de backup para Cloud Chat (Saved Messages)."""

import json
from datetime import datetime
from pathlib import Path
from unittest import mock

import pytest

from clean_telegram.backup import (
    backup_group_with_media,
    send_backup_to_cloud,
)

from tests.conftest import AsyncIteratorMock


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_chat_entity():
    """Cria um mock de entidade de chat."""
    chat = mock.Mock()
    chat.id = -1001234567890
    chat.title = "Grupo de Teste"
    return chat


@pytest.fixture
def mock_telethon_client():
    """Cria um mock de TelegramClient com comportamentos realistas."""
    client = mock.AsyncMock()

    # Mock de get_me
    async def mock_get_me():
        me = mock.Mock()
        me.id = 999888
        me.username = "testuser"
        me.first_name = "Test"
        me.last_name = "User"
        return me

    client.get_me = mock_get_me

    # Mock de iter_messages (retorna lista vazia por padrão)
    def mock_iter_messages(*args, **kwargs):
        return AsyncIteratorMock([])

    client.iter_messages = mock_iter_messages

    # Mock de iter_participants (retorna lista vazia por padrão)
    def mock_iter_participants(*args, **kwargs):
        return AsyncIteratorMock([])

    client.iter_participants = mock_iter_participants

    # Mock de send_file (para cloud chat)
    sent_files = []

    async def mock_send_file(entity, file, caption=None, **kwargs):
        """Mock que rastreia arquivos enviados para cloud chat."""
        sent_files.append(
            {
                "entity": entity,
                "file": file,
                "caption": caption,
            }
        )
        msg = mock.Mock()
        msg.id = len(sent_files)
        return msg

    client.send_file = mock_send_file

    # Mock de send_message (para resumo)
    sent_messages = []

    async def mock_send_message(entity, message, **kwargs):
        """Mock que rastreia mensagens enviadas."""
        sent_messages.append(
            {
                "entity": entity,
                "message": message,
            }
        )
        msg = mock.Mock()
        msg.id = len(sent_messages)
        return msg

    client.send_message = mock_send_message

    # Armazenar referências para verificação nos testes
    client._test_sent_files = sent_files
    client._test_sent_messages = sent_messages

    return client


@pytest.fixture
def mock_telethon_client_with_messages(mock_telethon_client):
    """Cria um client com mensagens de exemplo."""

    # Mock de mensagens
    class MockMessage:
        def __init__(self, msg_id, date, text=None, sender_id=None, media=None):
            self.id = msg_id
            self.date = date
            self.text = text
            self.sender_id = sender_id
            self.media = media
            self.sender = None
            self.reply_to = None

    def mock_iter_messages(*args, **kwargs):
        messages = [
            MockMessage(1, datetime(2024, 1, 1, 10, 0), "Olá!", 111),
            MockMessage(2, datetime(2024, 1, 1, 10, 5), "Como vai?", 222),
            MockMessage(3, datetime(2024, 1, 1, 10, 10), "Tudo bem?", 111),
        ]
        return AsyncIteratorMock(messages)

    mock_telethon_client.iter_messages = mock_iter_messages
    return mock_telethon_client


@pytest.fixture
def mock_telethon_client_with_participants(mock_telethon_client):
    """Cria um client com participantes de exemplo."""

    # Mock de participantes
    class MockParticipant:
        def __init__(self, user_id, first_name, last_name="", username=None):
            self.user = self
            self.id = user_id
            self.first_name = first_name
            self.last_name = last_name
            self.username = username
            self.bot = False
            self.verified = False
            self.premium = False
            self.phone = None
            self.status = None
            self.participant = None

    def mock_iter_participants(*args, **kwargs):
        participants = [
            MockParticipant(111, "João", "Silva", "joaosilva"),
            MockParticipant(222, "Maria", "Santos", "mariasantos"),
            MockParticipant(333, "Pedro", "", "pedro"),
        ]
        return AsyncIteratorMock(participants)

    mock_telethon_client.iter_participants = mock_iter_participants
    return mock_telethon_client


@pytest.fixture
def mock_client_with_both(
    mock_telethon_client_with_messages, mock_telethon_client_with_participants
):
    """Client completo com mensagens e participantes."""
    # Criar novo client combinando ambos
    combined = mock.AsyncMock()

    # Configurar send_file e send_message igual ao client de mensagens
    sent_files = []
    sent_messages = []

    async def mock_send_file(entity, file, caption=None, **kwargs):
        sent_files.append({"entity": entity, "file": file, "caption": caption})
        msg = mock.Mock()
        msg.id = len(sent_files)
        return msg

    async def mock_send_message(entity, message, **kwargs):
        sent_messages.append({"entity": entity, "message": message})
        msg = mock.Mock()
        msg.id = len(sent_messages)
        return msg

    combined.send_file = mock_send_file
    combined.send_message = mock_send_message

    # Armazenar referências para verificação
    combined._test_sent_files = sent_files
    combined._test_sent_messages = sent_messages

    # Copiar atributos importantes
    for attr in ["get_me", "iter_messages"]:
        setattr(combined, attr, getattr(mock_telethon_client_with_messages, attr))

    # Sobrescrever iter_participants com o do client de participantes
    combined.iter_participants = (
        mock_telethon_client_with_participants.iter_participants
    )

    return combined


@pytest.fixture
def temp_backup_dir(tmp_path):
    """Cria diretório temporário para backups."""
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir(exist_ok=True)
    return str(backup_dir)


# =============================================================================
# Testes: send_backup_to_cloud
# =============================================================================


class TestSendBackupToCloud:
    """Testes da função send_backup_to_cloud."""

    @pytest.mark.asyncio
    async def test_should_send_file_to_saved_messages(
        self, mock_telethon_client, tmp_path
    ):
        """Testa envio de arquivo para Saved Messages ('me')."""
        # Criar arquivo de teste
        test_file = tmp_path / "test_backup.json"
        test_file.write_text('{"test": "data"}')

        await send_backup_to_cloud(
            mock_telethon_client, str(test_file), "📦 Test Backup"
        )

        # Verificar que send_file foi chamado com 'me' como entidade
        assert len(mock_telethon_client._test_sent_files) == 1
        sent = mock_telethon_client._test_sent_files[0]
        assert sent["entity"] == "me"
        assert sent["file"] == str(test_file)
        assert sent["caption"] == "📦 Test Backup"

    @pytest.mark.asyncio
    async def test_should_include_caption_with_emoji(
        self, mock_telethon_client, tmp_path
    ):
        """Testa que caption inclui emojis para organização."""
        test_file = tmp_path / "test.json"
        test_file.write_text("{}")

        caption = "📦 Backup: Grupo Teste - Mensagens (100 msgs)"
        await send_backup_to_cloud(mock_telethon_client, str(test_file), caption)

        sent = mock_telethon_client._test_sent_files[0]
        assert "📦" in sent["caption"]
        assert "Grupo Teste" in sent["caption"]
        assert "100 msgs" in sent["caption"]


# =============================================================================
# Testes: backup_group_with_media com send_to_cloud
# =============================================================================


class TestBackupGroupWithCloud:
    """Testes de backup com envio para Cloud Chat."""

    @pytest.mark.asyncio
    async def test_should_send_json_files_to_cloud(
        self,
        mock_client_with_both,
        mock_chat_entity,
        temp_backup_dir,
    ):
        """Testa envio de arquivos JSON para Cloud Chat."""
        results = await backup_group_with_media(
            mock_client_with_both,
            mock_chat_entity,
            temp_backup_dir,
            formats="json",
            send_to_cloud=True,
        )

        # Verificar que arquivos foram enviados
        assert results["cloud_backup"] is True
        assert len(results["cloud_files"]) == 2  # messages_json, participants_json
        assert "messages_json" in results["cloud_files"]
        assert "participants_json" in results["cloud_files"]

        # Verificar captions
        sent_files = mock_client_with_both._test_sent_files
        captions = [f["caption"] for f in sent_files]

        assert any("📦" in c and "Mensagens" in c for c in captions)
        assert any("👥" in c and "Participantes" in c for c in captions)

    @pytest.mark.asyncio
    async def test_should_send_csv_files_to_cloud(
        self,
        mock_client_with_both,
        mock_chat_entity,
        temp_backup_dir,
    ):
        """Testa envio de arquivos CSV para Cloud Chat."""
        results = await backup_group_with_media(
            mock_client_with_both,
            mock_chat_entity,
            temp_backup_dir,
            formats="csv",
            send_to_cloud=True,
        )

        assert results["cloud_backup"] is True
        assert len(results["cloud_files"]) == 2  # messages_csv, participants_csv

        # Verificar que captions mencionam CSV
        sent_files = mock_client_with_both._test_sent_files
        captions = [f["caption"] for f in sent_files]

        assert any("CSV" in c for c in captions)

    @pytest.mark.asyncio
    async def test_should_send_all_formats_to_cloud(
        self,
        mock_client_with_both,
        mock_chat_entity,
        temp_backup_dir,
    ):
        """Testa envio de todos os formatos (JSON e CSV) para Cloud Chat."""
        results = await backup_group_with_media(
            mock_client_with_both,
            mock_chat_entity,
            temp_backup_dir,
            formats="both",
            send_to_cloud=True,
        )

        # Deve enviar 4 arquivos: 2 JSON + 2 CSV
        assert results["cloud_backup"] is True
        assert len(results["cloud_files"]) == 4

    @pytest.mark.asyncio
    async def test_should_send_summary_message_to_cloud(
        self,
        mock_client_with_both,
        mock_chat_entity,
        temp_backup_dir,
    ):
        """Testa envio de mensagem de resumo para Cloud Chat."""
        _results = await backup_group_with_media(
            mock_client_with_both,
            mock_chat_entity,
            temp_backup_dir,
            formats="json",
            send_to_cloud=True,
        )

        # Verificar que mensagem de resumo foi enviada
        sent_messages = mock_client_with_both._test_sent_messages
        assert len(sent_messages) == 1

        summary = sent_messages[0]["message"]
        assert "📊" in summary
        assert "Resumo do Backup" in summary
        assert "Grupo de Teste" in summary
        assert "Mensagens:" in summary
        assert "Participantes:" in summary
        assert "Saved Messages" in summary

    @pytest.mark.asyncio
    async def test_should_not_send_to_cloud_when_disabled(
        self,
        mock_client_with_both,
        mock_chat_entity,
        temp_backup_dir,
    ):
        """Testa que nada é enviado para Cloud Chat quando send_to_cloud=False."""
        results = await backup_group_with_media(
            mock_client_with_both,
            mock_chat_entity,
            temp_backup_dir,
            formats="json",
            send_to_cloud=False,
        )

        # Verificar que nada foi enviado
        assert results.get("cloud_backup") is not True
        assert "cloud_files" not in results
        assert len(mock_client_with_both._test_sent_files) == 0
        assert len(mock_client_with_both._test_sent_messages) == 0

    @pytest.mark.asyncio
    async def test_should_include_media_count_in_summary(
        self,
        mock_client_with_both,
        mock_chat_entity,
        temp_backup_dir,
    ):
        """Testa que resumo inclui contagem de mídia quando baixada."""

        # Mock de download_media_parallel
        async def mock_download(*args, **kwargs):
            return {
                "photo": 5,
                "video": 2,
                "total": 7,
            }

        with mock.patch(
            "clean_telegram.backup.download_media_parallel", side_effect=mock_download
        ):
            _results = await backup_group_with_media(
                mock_client_with_both,
                mock_chat_entity,
                temp_backup_dir,
                formats="json",
                download_media=True,
                send_to_cloud=True,
            )

        # Verificar resumo inclui mídia
        summary = mock_client_with_both._test_sent_messages[0]["message"]
        assert "Arquivos de mídia:" in summary
        assert "7" in summary

    @pytest.mark.asyncio
    async def test_should_skip_nonexistent_files(
        self,
        mock_telethon_client,
        mock_chat_entity,
        temp_backup_dir,
    ):
        """Testa que arquivos inexistentes são ignorados no envio para cloud."""
        # Adicionar send_file mock ao client
        sent_files = []

        async def mock_send_file(entity, file, caption=None, **kwargs):
            sent_files.append({"entity": entity, "file": file, "caption": caption})
            msg = mock.Mock()
            msg.id = len(sent_files)
            return msg

        async def mock_send_message(entity, message, **kwargs):
            msg = mock.Mock()
            msg.id = 1
            return msg

        mock_telethon_client.send_file = mock_send_file
        mock_telethon_client.send_message = mock_send_message

        # Simular situação onde arquivo JSON não foi criado (retorna vazio)
        # As funções de exportação não criam arquivos, então não haverá arquivos para enviar
        async def mock_export_msgs(client, entity, path):
            # Não cria arquivo
            return 0

        async def mock_export_parts(client, entity, path):
            # Não cria arquivo
            return 0

        # Mockar as funções corretas que agora são usadas por backup_group_with_media
        with mock.patch(
            "clean_telegram.backup.export_messages_to_json_streaming",
            side_effect=mock_export_msgs,
        ):
            with mock.patch(
                "clean_telegram.backup.export_participants_to_json_streaming",
                side_effect=mock_export_parts,
            ):
                results = await backup_group_with_media(
                    mock_telethon_client,
                    mock_chat_entity,
                    temp_backup_dir,
                    formats="json",
                    send_to_cloud=True,
                )

        # Como os arquivos não foram criados, nenhum arquivo de backup foi enviado
        # Apenas a mensagem de resumo pode ter sido enviada
        # Verificar que cloud_files está vazio (nenhum arquivo de backup enviado)
        assert results.get("cloud_files", []) == []


# =============================================================================
# Testes de Integração: CLI
# =============================================================================


class TestBackupCloudCLIIntegration:
    """Testes de integração do CLI com backup para cloud."""

    @pytest.mark.asyncio
    async def test_cli_argument_backup_to_cloud(
        self,
        mock_telethon_client,
        mock_chat_entity,
        temp_backup_dir,
        monkeypatch,
    ):
        """Testa que argumento --backup-to-cloud é processado corretamente."""
        from clean_telegram import cli

        # Mock environment
        monkeypatch.setenv("API_ID", "12345")
        monkeypatch.setenv("API_HASH", "test_hash")

        # Mock parse_args com backup_to_cloud=True
        args = mock.Mock()
        args.backup_group = "-1001234567890"
        args.export_members = None
        args.export_messages = None
        args.backup_format = "json"
        args.backup_output = temp_backup_dir
        args.download_media = False
        args.media_types = None
        args.backup_to_cloud = True  # Argumento sendo testado

        # Mock client.get_entity
        async def mock_get_entity(chat_id):
            return mock_chat_entity

        mock_telethon_client.get_entity = mock_get_entity

        async def mock_export_msgs(client, entity, path):
            # Criar arquivo JSON
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w") as f:
                json.dump({"messages": []}, f)
            return 0

        async def mock_export_parts(client, entity, path):
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w") as f:
                json.dump({"participants": []}, f)
            return 0

        with mock.patch(
            "clean_telegram.backup.export_messages_to_json",
            side_effect=mock_export_msgs,
        ):
            with mock.patch(
                "clean_telegram.backup.export_participants_to_json",
                side_effect=mock_export_parts,
            ):
                await cli.run_backup(args, mock_telethon_client)

        # Verificar que arquivos foram enviados para cloud
        assert len(mock_telethon_client._test_sent_files) > 0


# =============================================================================
# Testes: Cenários de Erro
# =============================================================================


class TestBackupCloudErrorHandling:
    """Testes de tratamento de erros no backup para cloud."""

    @pytest.mark.asyncio
    async def test_should_handle_send_file_error_gracefully(
        self,
        mock_telethon_client,
        mock_chat_entity,
        temp_backup_dir,
    ):
        """Testa que erro ao enviar arquivo é tratado adequadamente."""

        # Mock para criar arquivos locais
        async def mock_export_msgs(client, entity, path):
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w") as f:
                json.dump({"messages": []}, f)
            return 0

        async def mock_export_parts(client, entity, path):
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w") as f:
                json.dump({"participants": []}, f)
            return 0

        # Mock send_file que levanta exceção
        async def mock_send_file_error(*args, **kwargs):
            raise Exception("Network error")

        mock_telethon_client.send_file = mock_send_file_error

        with mock.patch(
            "clean_telegram.backup.export_messages_to_json",
            side_effect=mock_export_msgs,
        ):
            with mock.patch(
                "clean_telegram.backup.export_participants_to_json",
                side_effect=mock_export_parts,
            ):
                # A função deve propagar o erro
                with pytest.raises(Exception, match="Network error"):
                    await backup_group_with_media(
                        mock_telethon_client,
                        mock_chat_entity,
                        temp_backup_dir,
                        formats="json",
                        send_to_cloud=True,
                    )

    @pytest.mark.asyncio
    async def test_should_caption_with_special_characters(
        self,
        mock_client_with_both,
        temp_backup_dir,
    ):
        """Testa caption com caracteres especiais no nome do grupo."""
        # Grupo com caracteres especiais
        chat = mock.Mock()
        chat.id = -1001234567890
        chat.title = "Grupo 🎉 Teste & Coisa (2024)"

        results = await backup_group_with_media(
            mock_client_with_both,
            chat,
            temp_backup_dir,
            formats="json",
            send_to_cloud=True,
        )

        # Deve completar sem erro e incluir caracteres especiais no caption
        assert results["cloud_backup"] is True
        sent_files = mock_client_with_both._test_sent_files
        captions = [f["caption"] for f in sent_files]
        # Verificar que algum caption contém o título especial
        assert any("Grupo" in c for c in captions)
