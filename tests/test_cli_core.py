"""Testes críticos para cli.py."""

import sys
from unittest import mock
from unittest.mock import AsyncMock

import pytest

from clean_telegram import cli


class TestEnvInt:
    """Testes para env_int()."""

    def test_should_return_int_when_valid(self, monkeypatch):
        """Deve retornar int quando valor é válido."""
        monkeypatch.setenv("TEST_VAR", "12345")
        result = cli.env_int("TEST_VAR")
        assert result == 12345

    def test_should_exit_when_missing(self, monkeypatch):
        """Deve lançar SystemExit quando variável não existe."""
        monkeypatch.delenv("TEST_VAR", raising=False)

        with pytest.raises(SystemExit, match="Faltou TEST_VAR no .env"):
            cli.env_int("TEST_VAR")

    def test_should_exit_when_non_numeric(self, monkeypatch):
        """Deve lançar SystemExit quando valor não é numérico."""
        monkeypatch.setenv("TEST_VAR", "abc")

        with pytest.raises(SystemExit, match="Valor inválido para TEST_VAR"):
            cli.env_int("TEST_VAR")

    def test_should_accept_zero(self, monkeypatch):
        """Deve aceitar zero."""
        monkeypatch.setenv("TEST_VAR", "0")
        result = cli.env_int("TEST_VAR")
        assert result == 0

    def test_should_accept_negative(self, monkeypatch):
        """Deve aceitar negativos."""
        monkeypatch.setenv("TEST_VAR", "-100")
        result = cli.env_int("TEST_VAR")
        assert result == -100


class TestConfirmAction:
    """Testes para confirm_action()."""

    def test_should_return_true_when_exact_match(self, mock_stdin):
        """Deve retornar True quando usuário digita 'CONFIRMAR'."""
        mock_stdin("CONFIRMAR")
        result = cli.confirm_action()
        assert result is True

    def test_should_return_false_for_wrong_input(self, mock_stdin):
        """Deve retornar False para qualquer outro input."""
        mock_stdin("confirmar")  # minúsculas
        result = cli.confirm_action()
        assert result is False

    def test_should_trim_whitespace(self, mock_stdin):
        """Deve fazer trim de whitespace."""
        mock_stdin("   CONFIRMAR   ")
        result = cli.confirm_action()
        assert result is True

    def test_should_be_case_sensitive(self, mock_stdin):
        """Deve ser case-sensitive."""
        mock_stdin("Confirmar")  # Mixed case
        result = cli.confirm_action()
        assert result is False

    def test_should_require_exact_match(self, mock_stdin):
        """Deve exigir match exato."""
        mock_stdin("CONFIRMADO")
        result = cli.confirm_action()
        assert result is False

    def test_should_return_false_on_eof(self, monkeypatch):
        """Deve retornar False ao receber EOFError (ambiente não-TTY)."""
        monkeypatch.setattr("builtins.input", lambda _="": (_ for _ in ()).throw(EOFError()))
        result = cli.confirm_action()
        assert result is False


class TestRunClean:
    """Testes para run_clean()."""

    @pytest.mark.asyncio
    async def test_should_call_clean_all_dialogs(self, mock_telethon_client, mocker):
        """Deve chamar clean_all_dialogs com parâmetros corretos."""
        # Setup
        mock_telethon_client.get_me = mocker.AsyncMock()
        args = mock.Mock(dry_run=True, limit=10)

        # Mock clean_all_dialogs — retorna (processed, skipped)
        mock_clean = mocker.patch("clean_telegram.cli.clean_all_dialogs", return_value=(5, 0))

        # Execute
        await cli.run_clean(args, mock_telethon_client)

        # Verify
        mock_clean.assert_awaited_once_with(
            mock_telethon_client,
            dry_run=True,
            limit=10,
        )

    @pytest.mark.asyncio
    async def test_should_log_user_info(self, mock_telethon_client, mocker, caplog):
        """Deve logar informações do usuário."""
        me = mock.Mock()
        me.username = "testuser"
        me.first_name = "Test"
        me.id = 123
        mock_telethon_client.get_me = mocker.AsyncMock(return_value=me)

        args = mock.Mock(dry_run=True, limit=0)
        mocker.patch("clean_telegram.cli.clean_all_dialogs", return_value=(0, 0))

        with caplog.at_level("INFO"):
            await cli.run_clean(args, mock_telethon_client)

        assert "Logado como:" in caplog.text

    @pytest.mark.asyncio
    async def test_should_respect_dry_run(self, mock_telethon_client, mocker):
        """Deve passar dry_run corretamente."""
        mock_telethon_client.get_me = mocker.AsyncMock()
        mock_clean = mocker.patch("clean_telegram.cli.clean_all_dialogs", return_value=(0, 0))

        args = mock.Mock(dry_run=True, limit=0)
        await cli.run_clean(args, mock_telethon_client)

        call_kwargs = mock_clean.call_args[1]
        assert call_kwargs["dry_run"] is True

    @pytest.mark.asyncio
    async def test_should_respect_limit(self, mock_telethon_client, mocker):
        """Deve passar limit corretamente."""
        mock_telethon_client.get_me = mocker.AsyncMock()
        mock_clean = mocker.patch("clean_telegram.cli.clean_all_dialogs", return_value=(0, 0))

        args = mock.Mock(dry_run=True, limit=50)
        await cli.run_clean(args, mock_telethon_client)

        call_kwargs = mock_clean.call_args[1]
        assert call_kwargs["limit"] == 50


class TestRunReport:
    """Testes para run_report()."""

    @pytest.mark.asyncio
    async def test_should_call_all_reports_for_type_all(self, mock_telethon_client, mocker):
        """Deve chamar generate_all_reports para report_type='all'."""
        mock_telethon_client.get_me = mocker.AsyncMock()
        mock_generate = mocker.patch(
            "clean_telegram.cli.generate_all_reports",
            return_value={"groups": "path1", "contacts": "path2"}
        )

        args = mock.Mock(report="all", report_format="csv", report_output=None)
        await cli.run_report(args, mock_telethon_client)

        mock_generate.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_should_call_groups_report_for_groups(self, mock_telethon_client, mocker):
        """Deve chamar generate_groups_channels_report para 'groups'."""
        mock_telethon_client.get_me = mocker.AsyncMock()
        mock_generate = mocker.patch(
            "clean_telegram.cli.generate_groups_channels_report",
            return_value="path.csv"
        )

        args = mock.Mock(report="groups", report_format="json", report_output="out.json")
        await cli.run_report(args, mock_telethon_client)

        mock_generate.assert_awaited_once_with(
            mock_telethon_client,
            output_path="out.json",
            output_format="json",
        )

    @pytest.mark.asyncio
    async def test_should_call_contacts_report_for_contacts(self, mock_telethon_client, mocker):
        """Deve chamar generate_contacts_report para 'contacts'."""
        mock_telethon_client.get_me = mocker.AsyncMock()
        mock_generate = mocker.patch(
            "clean_telegram.cli.generate_contacts_report",
            return_value="path.csv"
        )

        args = mock.Mock(report="contacts", report_format="txt", report_output=None)
        await cli.run_report(args, mock_telethon_client)

        mock_generate.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_should_log_generated_path(self, mock_telethon_client, mocker, caplog):
        """Deve logar caminho do arquivo gerado."""
        mock_telethon_client.get_me = mocker.AsyncMock()
        mocker.patch(
            "clean_telegram.cli.generate_groups_channels_report",
            return_value="relatorio.csv"
        )

        args = mock.Mock(report="groups", report_format="csv", report_output=None)

        with caplog.at_level("INFO"):
            await cli.run_report(args, mock_telethon_client)

        assert "relatorio.csv" in caplog.text

    @pytest.mark.asyncio
    async def test_should_support_all_formats(self, mock_telethon_client, mocker):
        """Deve suportar todos os formatos (csv, json, txt)."""
        mock_telethon_client.get_me = mocker.AsyncMock()
        mock_generate = mocker.patch(
            "clean_telegram.cli.generate_groups_channels_report"
        )

        for fmt in ["csv", "json", "txt"]:
            args = mock.Mock(report="groups", report_format=fmt, report_output=None)
            await cli.run_report(args, mock_telethon_client)

            call_kwargs = mock_generate.call_args[1]
            assert call_kwargs["output_format"] == fmt


class TestStartClient:
    """Testes para start_client()."""

    @pytest.mark.asyncio
    async def test_should_start_with_bot_token_in_bot_mode(self):
        """Deve iniciar com bot_token em modo bot."""
        from clean_telegram.cli import AuthConfig

        auth_config = AuthConfig(mode="bot", session_name="bot_session", bot_token="test_token")
        mock_client = AsyncMock()

        await cli.start_client(mock_client, auth_config)

        mock_client.start.assert_called_once_with(bot_token="test_token")

    @pytest.mark.asyncio
    async def test_should_start_without_token_in_user_mode(self):
        """Deve iniciar sem token em modo usuário."""
        from clean_telegram.cli import AuthConfig

        auth_config = AuthConfig(mode="user", session_name="session")
        mock_client = AsyncMock()

        await cli.start_client(mock_client, auth_config)

        mock_client.start.assert_called_once_with()


class TestCreateClient:
    """Testes para create_client()."""

    def test_should_create_client_with_config(self, monkeypatch):
        """Deve criar TelegramClient com configuração do ambiente."""
        monkeypatch.setenv("API_ID", "12345")
        monkeypatch.setenv("API_HASH", "test_hash")

        client, auth_config = cli.create_client()

        assert auth_config.mode == "user"
        assert auth_config.session_name == "session"
        assert client is not None

    def test_should_exit_when_api_id_missing(self, monkeypatch):
        """Deve lançar SystemExit quando API_ID está faltando."""
        monkeypatch.delenv("API_ID", raising=False)
        monkeypatch.setenv("API_HASH", "test_hash")

        with pytest.raises(SystemExit, match="Faltou API_ID no .env"):
            cli.create_client()

    def test_should_exit_when_api_hash_missing(self, monkeypatch):
        """Deve lançar SystemExit quando API_HASH está faltando."""
        monkeypatch.setenv("API_ID", "12345")
        monkeypatch.delenv("API_HASH", raising=False)

        with pytest.raises(SystemExit, match="Faltou API_HASH no .env"):
            cli.create_client()

    def test_should_use_bot_mode_when_token_exists(self, monkeypatch):
        """Deve usar modo bot quando BOT_TOKEN existe."""
        monkeypatch.setenv("API_ID", "12345")
        monkeypatch.setenv("API_HASH", "test_hash")
        monkeypatch.setenv("BOT_TOKEN", "test_token")

        client, auth_config = cli.create_client()

        assert auth_config.mode == "bot"
        assert auth_config.bot_token == "test_token"


class TestErrorHandling:
    """Testes para funcoes de tratamento de erro."""

    def test_warn_bot_permissions_for_clean_in_bot_mode(self, caplog):
        """Deve avisar para clean mode em bot auth."""
        from clean_telegram.cli import AuthConfig

        auth_config = AuthConfig(mode="bot", session_name="bot", bot_token="token")

        with caplog.at_level("WARNING"):
            cli.warn_bot_permissions(
                auth_config=auth_config,
                is_clean_mode=True,
                is_backup_mode=False
            )

        assert "Modo bot ativo" in caplog.text

    def test_warn_bot_permissions_should_not_warn_for_reports(self, caplog):
        """Não deve avisar para relatórios."""
        from clean_telegram.cli import AuthConfig

        auth_config = AuthConfig(mode="bot", session_name="bot", bot_token="token")

        with caplog.at_level("WARNING"):
            cli.warn_bot_permissions(
                auth_config=auth_config,
                is_clean_mode=False,
                is_backup_mode=False
            )

        assert "Modo bot ativo" not in caplog.text

    def test_format_rpc_error_in_bot_mode(self):
        """Deve retornar mensagem amigavel em modo bot."""
        from clean_telegram.cli import AuthConfig
        from telethon.errors import RPCError

        auth_config = AuthConfig(mode="bot", session_name="bot", bot_token="token")
        error = RPCError(request=None, message="Test error")

        result = cli.format_rpc_error(error, auth_config)

        assert "modo bot" in result.lower()

    def test_format_rpc_error_in_user_mode(self):
        """Deve retornar mensagem generica em modo usuario."""
        from clean_telegram.cli import AuthConfig
        from telethon.errors import RPCError

        auth_config = AuthConfig(mode="user", session_name="session")
        error = RPCError(request=None, message="Test error")

        result = cli.format_rpc_error(error, auth_config)

        assert "Erro da API" in result


class TestParseArgs:
    """Testes para parse_args()."""

    def test_should_have_default_dry_run_false(self, monkeypatch):
        """Deve ter dry_run=False por padrão."""
        monkeypatch.setattr("sys.argv", ["prog"])
        args = cli.parse_args()
        assert args.dry_run is False

    def test_should_enable_dry_run_flag(self, monkeypatch):
        """Deve aceitar flag --dry-run."""
        monkeypatch.setattr("sys.argv", ["prog", "--dry-run"])
        args = cli.parse_args()
        assert args.dry_run is True

    def test_should_default_limit_to_zero(self, monkeypatch):
        """Deve ter limit=0 por padrão (todos os diálogos)."""
        monkeypatch.setattr("sys.argv", ["prog"])
        args = cli.parse_args()
        assert args.limit == 0

    def test_should_accept_limit_argument(self, monkeypatch):
        """Deve aceitar argumento --limit."""
        monkeypatch.setattr("sys.argv", ["prog", "--limit", "100"])
        args = cli.parse_args()
        assert args.limit == 100

    def test_should_accept_report_choices(self, monkeypatch):
        """Deve aceitar choices para --report."""
        for choice in ["groups", "contacts", "all"]:
            monkeypatch.setattr("sys.argv", ["prog", "--report", choice])
            args = cli.parse_args()
            assert args.report == choice

    def test_should_default_report_format_to_csv(self, monkeypatch):
        """Deve ter report_format='csv' por padrão."""
        monkeypatch.setattr("sys.argv", ["prog"])
        args = cli.parse_args()
        assert args.report_format == "csv"

    def test_should_accept_backup_format_choices(self, monkeypatch):
        """Deve aceitar choices para --backup-format."""
        for choice in ["json", "csv", "both"]:
            monkeypatch.setattr("sys.argv", ["prog", "--backup-format", choice])
            args = cli.parse_args()
            assert args.backup_format == choice

    def test_should_default_download_media_to_false(self, monkeypatch):
        """Deve ter download_media=False por padrão."""
        monkeypatch.setattr("sys.argv", ["prog"])
        args = cli.parse_args()
        assert args.download_media is False

    def test_should_enable_download_media_flag(self, monkeypatch):
        """Deve aceitar flag --download-media."""
        monkeypatch.setattr("sys.argv", ["prog", "--download-media"])
        args = cli.parse_args()
        assert args.download_media is True

    def test_should_default_max_concurrent_downloads_to_5(self, monkeypatch):
        """Deve ter max_concurrent_downloads=5 por padrão."""
        monkeypatch.setattr("sys.argv", ["prog"])
        args = cli.parse_args()
        assert args.max_concurrent_downloads == 5


class TestRunBackup:
    """Testes para run_backup()."""

    @pytest.mark.asyncio
    async def test_should_log_user_info(self, mock_telethon_client, mocker, caplog):
        """Deve logar informações do usuário."""
        me = mock.Mock()
        me.username = "testuser"
        me.first_name = "Test"
        me.id = 123
        mock_telethon_client.get_me = mocker.AsyncMock(return_value=me)

        args = mock.Mock(
            backup_group="-1001234567890",
            export_members=None,
            export_messages=None,
            backup_output="backups",
            backup_format="json",
            download_media=False,
            media_types=None,
            backup_to_cloud=False,
            max_concurrent_downloads=5
        )

        with caplog.at_level("INFO"):
            # Mock get_entity and backup to avoid actual work
            mock_entity = mock.Mock()
            mock_entity.title = "Test Group"
            mock_telethon_client.get_entity = mocker.AsyncMock(return_value=mock_entity)
            mocker.patch("clean_telegram.cli.backup_group_with_media", return_value={})

            await cli.run_backup(args, mock_telethon_client)

        assert "Logado como:" in caplog.text

    @pytest.mark.asyncio
    async def test_should_resolve_chat_entity(self, mock_telethon_client, mocker):
        """Deve resolver entidade do chat."""
        mock_telethon_client.get_me = mocker.AsyncMock()

        mock_entity = mock.Mock()
        mock_entity.title = "Test Group"
        mock_telethon_client.get_entity = mocker.AsyncMock(return_value=mock_entity)

        args = mock.Mock(
            backup_group="-1001234567890",
            export_members=None,
            export_messages=None,
            backup_output="backups",
            backup_format="json",
            download_media=False,
            media_types=None,
            backup_to_cloud=False,
            max_concurrent_downloads=5
        )

        mocker.patch("clean_telegram.cli.backup_group_with_media", return_value={})

        await cli.run_backup(args, mock_telethon_client)

        mock_telethon_client.get_entity.assert_called_once_with("-1001234567890")

    @pytest.mark.asyncio
    async def test_should_handle_missing_chat_id(self, mock_telethon_client, mocker, caplog):
        """Deve lidar com chat_id não especificado."""
        mock_telethon_client.get_me = mocker.AsyncMock()

        args = mock.Mock(
            backup_group=None,
            export_members=None,
            export_messages=None,
            backup_output="backups",
            backup_format="json",
            download_media=False,
            media_types=None,
            backup_to_cloud=False,
            max_concurrent_downloads=5
        )

        with caplog.at_level("ERROR"):
            await cli.run_backup(args, mock_telethon_client)

        assert "Nenhum chat especificado" in caplog.text

    @pytest.mark.asyncio
    async def test_should_handle_get_entity_error(self, mock_telethon_client, mocker, caplog):
        """Deve lidar com erro ao resolver chat."""
        mock_telethon_client.get_me = mocker.AsyncMock()
        mock_telethon_client.get_entity = mocker.AsyncMock(side_effect=Exception("Chat not found"))

        args = mock.Mock(
            backup_group="-1001234567890",
            export_members=None,
            export_messages=None,
            backup_output="backups",
            backup_format="json",
            download_media=False,
            media_types=None,
            backup_to_cloud=False,
            max_concurrent_downloads=5
        )

        with caplog.at_level("ERROR"):
            await cli.run_backup(args, mock_telethon_client)

        assert "Erro ao resolver chat" in caplog.text

    @pytest.mark.asyncio
    async def test_should_call_backup_group_with_media(self, mock_telethon_client, mocker):
        """Deve chamar backup_group_with_media com parâmetros corretos."""
        mock_telethon_client.get_me = mocker.AsyncMock()

        mock_entity = mock.Mock()
        mock_entity.title = "Test Group"
        mock_telethon_client.get_entity = mocker.AsyncMock(return_value=mock_entity)

        args = mock.Mock(
            backup_group="-1001234567890",
            export_members=None,
            export_messages=None,
            backup_output="backups",
            backup_format="json",
            download_media=True,
            media_types="photo,video",
            backup_to_cloud=True,
            max_concurrent_downloads=10
        )

        mock_backup = mocker.patch("clean_telegram.cli.backup_group_with_media", return_value={
            "messages_count": 100,
            "participants_count": 50
        })

        await cli.run_backup(args, mock_telethon_client)

        mock_backup.assert_awaited_once()
        call_args = mock_backup.call_args
        assert call_args[0][1] == mock_entity  # entity
        assert call_args[1]["download_media"] is True
        assert call_args[1]["media_types"] == ["photo", "video"]
        assert call_args[1]["send_to_cloud"] is True
        assert call_args[1]["max_concurrent_downloads"] == 10

    @pytest.mark.asyncio
    async def test_should_export_members_only(self, mock_telethon_client, mocker):
        """Deve exportar apenas participantes quando export_members especificado."""
        mock_telethon_client.get_me = mocker.AsyncMock()

        mock_entity = mock.Mock()
        mock_entity.title = "Test Group"
        mock_telethon_client.get_entity = mocker.AsyncMock(return_value=mock_entity)

        args = mock.Mock(
            backup_group=None,
            export_members="-1001234567890",
            export_messages=None,
            backup_format="json",
            backup_output="backups",
            download_media=False,
            media_types=None,
            backup_to_cloud=False,
            max_concurrent_downloads=5
        )

        # Patch at the backup module level since it's imported inside run_backup
        mock_export = mocker.patch("clean_telegram.backup.export_participants_to_json", return_value=10)

        await cli.run_backup(args, mock_telethon_client)

        mock_export.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_should_export_messages_only(self, mock_telethon_client, mocker):
        """Deve exportar apenas mensagens quando export_messages especificado."""
        mock_telethon_client.get_me = mocker.AsyncMock()

        mock_entity = mock.Mock()
        mock_entity.title = "Test Group"
        mock_telethon_client.get_entity = mocker.AsyncMock(return_value=mock_entity)

        args = mock.Mock(
            backup_group=None,
            export_members=None,
            export_messages="-1001234567890",
            backup_format="json",
            backup_output="backups",
            download_media=False,
            media_types=None,
            backup_to_cloud=False,
            max_concurrent_downloads=5
        )

        # Patch at the backup module level since it's imported inside run_backup
        mock_export = mocker.patch("clean_telegram.backup.export_messages_to_json", return_value=100)

        await cli.run_backup(args, mock_telethon_client)

        mock_export.assert_awaited_once()


class TestGetTimestamp:
    """Testes para _get_timestamp()."""

    def test_should_return_string_in_correct_format(self):
        """Deve retornar string no formato YYYYMMDD_HHMMSS."""
        result = cli._get_timestamp()
        assert isinstance(result, str)
        assert len(result) == 15  # YYYYMMDD_HHMMSS
        assert "_" in result

    def test_should_return_different_values_on_consecutive_calls(self):
        """Deve retornar valores diferentes em chamadas consecutivas."""
        import time
        result1 = cli._get_timestamp()
        time.sleep(1.1)  # Pausa suficiente para garantir timestamp diferente
        result2 = cli._get_timestamp()
        # Valores devem ser diferentes (pelo menos o segundo mudou)
        assert result1 != result2
        assert isinstance(result1, str)
        assert isinstance(result2, str)
        assert len(result1) == 15
        assert len(result2) == 15


class TestResolveAuthConfig:
    """Testes para resolve_auth_config()."""

    def test_should_return_user_config_by_default(self, monkeypatch):
        """Deve retornar configuração de usuário por padrão."""
        monkeypatch.delenv("BOT_TOKEN", raising=False)

        config = cli.resolve_auth_config()

        assert config.mode == "user"
        assert config.session_name == "session"
        assert config.bot_token is None

    def test_should_return_bot_config_when_token_exists(self, monkeypatch):
        """Deve retornar configuração de bot quando BOT_TOKEN existe."""
        monkeypatch.setenv("BOT_TOKEN", "test_token")

        config = cli.resolve_auth_config()

        assert config.mode == "bot"
        assert config.bot_token == "test_token"

    def test_should_use_custom_bot_session_name(self, monkeypatch):
        """Deve usar nome de sessão customizado quando BOT_SESSION_NAME existe."""
        monkeypatch.setenv("BOT_TOKEN", "test_token")
        monkeypatch.setenv("BOT_SESSION_NAME", "custom_bot_session")

        config = cli.resolve_auth_config()

        assert config.session_name == "custom_bot_session"

    def test_should_use_custom_user_session_name(self, monkeypatch):
        """Deve usar nome de sessão customizado quando SESSION_NAME existe."""
        monkeypatch.delenv("BOT_TOKEN", raising=False)
        monkeypatch.setenv("SESSION_NAME", "custom_session")

        config = cli.resolve_auth_config()

        assert config.session_name == "custom_session"