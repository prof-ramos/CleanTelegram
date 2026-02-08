"""Testes estendidos para o módulo cli.py.

Cobre funções não testadas: env_int, parse_args, confirm_action,
run_report, run_clean, run_backup.
"""

import argparse
import sys
from unittest import mock

import pytest

from clean_telegram import cli


# =============================================================================
# Testes: env_int
# =============================================================================


class TestEnvInt:
    """Testes para env_int()."""

    def test_valid_integer(self, monkeypatch):
        monkeypatch.setenv("TEST_VAR", "12345")
        assert cli.env_int("TEST_VAR") == 12345

    def test_missing_variable_raises_system_exit(self, monkeypatch):
        monkeypatch.delenv("TEST_VAR", raising=False)
        with pytest.raises(SystemExit, match="Faltou TEST_VAR"):
            cli.env_int("TEST_VAR")

    def test_empty_string_raises_system_exit(self, monkeypatch):
        monkeypatch.setenv("TEST_VAR", "")
        with pytest.raises(SystemExit, match="Faltou TEST_VAR"):
            cli.env_int("TEST_VAR")

    def test_non_integer_raises_system_exit(self, monkeypatch):
        monkeypatch.setenv("TEST_VAR", "not_a_number")
        with pytest.raises(SystemExit, match="Valor inválido"):
            cli.env_int("TEST_VAR")

    def test_float_string_raises_system_exit(self, monkeypatch):
        monkeypatch.setenv("TEST_VAR", "3.14")
        with pytest.raises(SystemExit, match="Valor inválido"):
            cli.env_int("TEST_VAR")

    def test_negative_integer(self, monkeypatch):
        monkeypatch.setenv("TEST_VAR", "-42")
        assert cli.env_int("TEST_VAR") == -42


# =============================================================================
# Testes: parse_args
# =============================================================================


class TestParseArgs:
    """Testes para parse_args()."""

    def test_defaults(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["prog"])
        args = cli.parse_args()
        assert args.dry_run is False
        assert args.yes is False
        assert args.limit == 0
        assert args.interactive is False
        assert args.report is None
        assert args.report_format == "csv"
        assert args.backup_group is None
        assert args.backup_format == "json"
        assert args.backup_output == "backups"
        assert args.download_media is False
        assert args.media_types is None
        assert args.backup_to_cloud is False
        assert args.max_concurrent_downloads == 5

    def test_dry_run_flag(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["prog", "--dry-run"])
        args = cli.parse_args()
        assert args.dry_run is True

    def test_limit_flag(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["prog", "--limit", "10"])
        args = cli.parse_args()
        assert args.limit == 10

    def test_report_groups(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["prog", "--report", "groups", "--report-format", "json"])
        args = cli.parse_args()
        assert args.report == "groups"
        assert args.report_format == "json"

    def test_backup_group_with_media(self, monkeypatch):
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "prog",
                "--backup-group", "-100123",
                "--backup-format", "both",
                "--download-media",
                "--media-types", "photo,video",
                "--backup-to-cloud",
                "--max-concurrent-downloads", "3",
            ],
        )
        args = cli.parse_args()
        assert args.backup_group == "-100123"
        assert args.backup_format == "both"
        assert args.download_media is True
        assert args.media_types == "photo,video"
        assert args.backup_to_cloud is True
        assert args.max_concurrent_downloads == 3

    def test_interactive_flag(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["prog", "-i"])
        args = cli.parse_args()
        assert args.interactive is True


# =============================================================================
# Testes: confirm_action
# =============================================================================


class TestConfirmAction:
    """Testes para confirm_action()."""

    def test_accepts_correct_input(self, monkeypatch):
        monkeypatch.setattr(sys, "stdin", mock.Mock(readline=mock.Mock(return_value="APAGAR TUDO\n")))
        assert cli.confirm_action() is True

    def test_rejects_incorrect_input(self, monkeypatch):
        monkeypatch.setattr(sys, "stdin", mock.Mock(readline=mock.Mock(return_value="nao\n")))
        assert cli.confirm_action() is False

    def test_rejects_empty_input(self, monkeypatch):
        monkeypatch.setattr(sys, "stdin", mock.Mock(readline=mock.Mock(return_value="\n")))
        assert cli.confirm_action() is False


# =============================================================================
# Testes: run_report
# =============================================================================


class TestRunReport:
    """Testes para run_report()."""

    @pytest.mark.asyncio
    async def test_run_report_groups(self):
        client = mock.AsyncMock()
        me = mock.Mock(username="user", id=1, first_name="User")
        client.get_me.return_value = me

        args = argparse.Namespace(
            report="groups",
            report_format="csv",
            report_output="/tmp/test_groups.csv",
        )

        with mock.patch("clean_telegram.cli.generate_groups_channels_report", new_callable=mock.AsyncMock) as mock_gen:
            mock_gen.return_value = "/tmp/test_groups.csv"
            await cli.run_report(args, client)
            mock_gen.assert_awaited_once_with(
                client,
                output_path="/tmp/test_groups.csv",
                output_format="csv",
            )

    @pytest.mark.asyncio
    async def test_run_report_contacts(self):
        client = mock.AsyncMock()
        client.get_me.return_value = mock.Mock(username="user", id=1, first_name="User")

        args = argparse.Namespace(
            report="contacts",
            report_format="json",
            report_output=None,
        )

        with mock.patch("clean_telegram.cli.generate_contacts_report", new_callable=mock.AsyncMock) as mock_gen:
            mock_gen.return_value = "/tmp/contacts.json"
            await cli.run_report(args, client)
            mock_gen.assert_awaited_once_with(
                client,
                output_path=None,
                output_format="json",
            )

    @pytest.mark.asyncio
    async def test_run_report_all(self):
        client = mock.AsyncMock()
        client.get_me.return_value = mock.Mock(username="user", id=1, first_name="User")

        args = argparse.Namespace(
            report="all",
            report_format="txt",
            report_output=None,
        )

        with mock.patch("clean_telegram.cli.generate_all_reports", new_callable=mock.AsyncMock) as mock_gen:
            mock_gen.return_value = {"groups_channels": "/tmp/g.txt", "contacts": "/tmp/c.txt"}
            await cli.run_report(args, client)
            mock_gen.assert_awaited_once_with(client, output_format="txt")


# =============================================================================
# Testes: run_clean
# =============================================================================


class TestRunClean:
    """Testes para run_clean()."""

    @pytest.mark.asyncio
    async def test_run_clean_dispatches_to_clean_all_dialogs(self):
        client = mock.AsyncMock()
        client.get_me.return_value = mock.Mock(username="user", id=1, first_name="User")

        args = argparse.Namespace(dry_run=True, limit=5)

        with mock.patch("clean_telegram.cli.clean_all_dialogs", new_callable=mock.AsyncMock) as mock_clean:
            mock_clean.return_value = 5
            await cli.run_clean(args, client)
            mock_clean.assert_awaited_once_with(client, dry_run=True, limit=5)


# =============================================================================
# Testes: run_backup
# =============================================================================


class TestRunBackup:
    """Testes para run_backup()."""

    def _make_args(self, **overrides):
        defaults = dict(
            backup_group=None,
            export_members=None,
            export_messages=None,
            backup_format="json",
            backup_output="/tmp/backups",
            download_media=False,
            media_types=None,
            backup_to_cloud=False,
            max_concurrent_downloads=5,
        )
        defaults.update(overrides)
        return argparse.Namespace(**defaults)

    @pytest.mark.asyncio
    async def test_run_backup_group_happy_path(self):
        client = mock.AsyncMock()
        client.get_me.return_value = mock.Mock(username="user", id=1, first_name="User")

        entity = mock.Mock(id=-100123, title="Test Group")
        client.get_entity.return_value = entity

        args = self._make_args(backup_group="-100123")

        with mock.patch("clean_telegram.cli.backup_group_with_media", new_callable=mock.AsyncMock) as mock_backup:
            mock_backup.return_value = {"messages_count": 10, "participants_count": 5}
            await cli.run_backup(args, client)
            mock_backup.assert_awaited_once()
            call_kwargs = mock_backup.call_args
            assert call_kwargs[0][1] == entity  # chat entity

    @pytest.mark.asyncio
    async def test_run_backup_entity_not_found(self, caplog):
        client = mock.AsyncMock()
        client.get_me.return_value = mock.Mock(username="user", id=1, first_name="User")
        client.get_entity.side_effect = ValueError("Entity not found")

        args = self._make_args(backup_group="-100123")

        with caplog.at_level("ERROR"):
            await cli.run_backup(args, client)

        assert "Erro ao resolver chat" in caplog.text

    @pytest.mark.asyncio
    async def test_run_backup_no_chat_specified(self, caplog):
        client = mock.AsyncMock()
        client.get_me.return_value = mock.Mock(username="user", id=1, first_name="User")

        args = self._make_args()  # All None

        with caplog.at_level("ERROR"):
            await cli.run_backup(args, client)

        assert "Nenhum chat especificado" in caplog.text

    @pytest.mark.asyncio
    async def test_run_backup_with_media_types(self):
        client = mock.AsyncMock()
        client.get_me.return_value = mock.Mock(username="user", id=1, first_name="User")

        entity = mock.Mock(id=-100123, title="Test Group")
        client.get_entity.return_value = entity

        args = self._make_args(
            backup_group="-100123",
            download_media=True,
            media_types="photo,video",
        )

        with mock.patch("clean_telegram.cli.backup_group_with_media", new_callable=mock.AsyncMock) as mock_backup:
            mock_backup.return_value = {
                "messages_count": 10,
                "participants_count": 5,
                "media": {"photo": 3, "video": 1, "total": 4},
            }
            await cli.run_backup(args, client)

            call_kwargs = mock_backup.call_args
            assert call_kwargs[1]["media_types"] == ["photo", "video"]
            assert call_kwargs[1]["download_media"] is True

    @pytest.mark.asyncio
    async def test_run_backup_export_members(self):
        client = mock.AsyncMock()
        client.get_me.return_value = mock.Mock(username="user", id=1, first_name="User")

        entity = mock.Mock(id=-100123, title="Test Group")
        client.get_entity.return_value = entity

        args = self._make_args(export_members="-100123", backup_format="json")

        with mock.patch("clean_telegram.backup.export_participants_to_json", new_callable=mock.AsyncMock) as mock_export:
            mock_export.return_value = 10
            await cli.run_backup(args, client)
            mock_export.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_run_backup_export_messages(self):
        client = mock.AsyncMock()
        client.get_me.return_value = mock.Mock(username="user", id=1, first_name="User")

        entity = mock.Mock(id=-100123, title="Test Group")
        client.get_entity.return_value = entity

        args = self._make_args(export_messages="-100123", backup_format="csv")

        with mock.patch("clean_telegram.backup.export_messages_to_csv", new_callable=mock.AsyncMock) as mock_export:
            mock_export.return_value = 25
            await cli.run_backup(args, client)
            mock_export.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_run_backup_export_members_both_formats(self):
        client = mock.AsyncMock()
        client.get_me.return_value = mock.Mock(username="user", id=1, first_name="User")

        entity = mock.Mock(id=-100123, title="Test Group")
        client.get_entity.return_value = entity

        args = self._make_args(export_members="-100123", backup_format="both")

        with mock.patch("clean_telegram.backup.export_participants_to_json", new_callable=mock.AsyncMock) as mock_json, \
             mock.patch("clean_telegram.backup.export_participants_to_csv", new_callable=mock.AsyncMock) as mock_csv:
            mock_json.return_value = 10
            mock_csv.return_value = 10
            await cli.run_backup(args, client)
            mock_json.assert_awaited_once()
            mock_csv.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_run_backup_export_messages_both_formats(self):
        client = mock.AsyncMock()
        client.get_me.return_value = mock.Mock(username="user", id=1, first_name="User")

        entity = mock.Mock(id=-100123, title="Test Group")
        client.get_entity.return_value = entity

        args = self._make_args(export_messages="-100123", backup_format="both")

        with mock.patch("clean_telegram.backup.export_messages_to_json", new_callable=mock.AsyncMock) as mock_json, \
             mock.patch("clean_telegram.backup.export_messages_to_csv", new_callable=mock.AsyncMock) as mock_csv:
            mock_json.return_value = 25
            mock_csv.return_value = 25
            await cli.run_backup(args, client)
            mock_json.assert_awaited_once()
            mock_csv.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_run_backup_cloud_logging(self, caplog):
        client = mock.AsyncMock()
        client.get_me.return_value = mock.Mock(username="user", id=1, first_name="User")

        entity = mock.Mock(id=-100123, title="Test Group")
        client.get_entity.return_value = entity

        args = self._make_args(backup_group="-100123", backup_to_cloud=True)

        with mock.patch("clean_telegram.cli.backup_group_with_media", new_callable=mock.AsyncMock) as mock_backup:
            mock_backup.return_value = {
                "messages_count": 10,
                "participants_count": 5,
                "cloud_backup": True,
                "cloud_files": ["messages_json", "participants_json"],
                "messages_json": "/tmp/msgs.json",
                "participants_json": "/tmp/parts.json",
            }
            with caplog.at_level("INFO"):
                await cli.run_backup(args, client)

            assert "Cloud Chat" in caplog.text


# =============================================================================
# Testes: main (integration)
# =============================================================================


class TestMainIntegration:
    """Testes de integração para main()."""

    @pytest.mark.asyncio
    async def test_main_report_mode(self, monkeypatch):
        """main() no modo relatório chama run_report."""
        monkeypatch.setenv("API_ID", "12345")
        monkeypatch.setenv("API_HASH", "testhash")
        monkeypatch.setenv("SESSION_NAME", "test_session")
        monkeypatch.delenv("BOT_TOKEN", raising=False)
        monkeypatch.setattr(sys, "argv", ["prog", "--report", "groups"])

        with mock.patch("clean_telegram.cli.load_dotenv"), \
             mock.patch("clean_telegram.cli.TelegramClient") as mock_tc, \
             mock.patch("clean_telegram.cli.start_client", new_callable=mock.AsyncMock), \
             mock.patch("clean_telegram.cli.run_report", new_callable=mock.AsyncMock) as mock_report:
            # Set up async context manager
            mock_client = mock.AsyncMock()
            mock_tc.return_value.__aenter__ = mock.AsyncMock(return_value=mock_client)
            mock_tc.return_value.__aexit__ = mock.AsyncMock(return_value=None)

            await cli.main()

            mock_report.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_main_clean_mode_with_yes(self, monkeypatch):
        """main() no modo limpeza com --yes pula confirmação."""
        monkeypatch.setenv("API_ID", "12345")
        monkeypatch.setenv("API_HASH", "testhash")
        monkeypatch.setenv("SESSION_NAME", "test_session")
        monkeypatch.delenv("BOT_TOKEN", raising=False)
        monkeypatch.setattr(sys, "argv", ["prog", "--yes"])

        with mock.patch("clean_telegram.cli.load_dotenv"), \
             mock.patch("clean_telegram.cli.TelegramClient") as mock_tc, \
             mock.patch("clean_telegram.cli.start_client", new_callable=mock.AsyncMock), \
             mock.patch("clean_telegram.cli.run_clean", new_callable=mock.AsyncMock) as mock_clean:
            mock_client = mock.AsyncMock()
            mock_tc.return_value.__aenter__ = mock.AsyncMock(return_value=mock_client)
            mock_tc.return_value.__aexit__ = mock.AsyncMock(return_value=None)

            await cli.main()

            mock_clean.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_main_clean_mode_cancelled(self, monkeypatch):
        """main() no modo limpeza cancelado pelo usuário."""
        monkeypatch.setenv("API_ID", "12345")
        monkeypatch.setenv("API_HASH", "testhash")
        monkeypatch.setenv("SESSION_NAME", "test_session")
        monkeypatch.delenv("BOT_TOKEN", raising=False)
        monkeypatch.setattr(sys, "argv", ["prog"])

        with mock.patch("clean_telegram.cli.load_dotenv"), \
             mock.patch("clean_telegram.cli.confirm_action", return_value=False), \
             mock.patch("clean_telegram.cli.TelegramClient") as mock_tc, \
             mock.patch("clean_telegram.cli.run_clean", new_callable=mock.AsyncMock) as mock_clean:
            await cli.main()

            mock_clean.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_main_backup_mode(self, monkeypatch):
        """main() no modo backup não pede confirmação."""
        monkeypatch.setenv("API_ID", "12345")
        monkeypatch.setenv("API_HASH", "testhash")
        monkeypatch.setenv("SESSION_NAME", "test_session")
        monkeypatch.delenv("BOT_TOKEN", raising=False)
        monkeypatch.setattr(sys, "argv", ["prog", "--backup-group", "-100123"])

        with mock.patch("clean_telegram.cli.load_dotenv"), \
             mock.patch("clean_telegram.cli.TelegramClient") as mock_tc, \
             mock.patch("clean_telegram.cli.start_client", new_callable=mock.AsyncMock), \
             mock.patch("clean_telegram.cli.run_backup", new_callable=mock.AsyncMock) as mock_backup, \
             mock.patch("clean_telegram.cli.confirm_action") as mock_confirm:
            mock_client = mock.AsyncMock()
            mock_tc.return_value.__aenter__ = mock.AsyncMock(return_value=mock_client)
            mock_tc.return_value.__aexit__ = mock.AsyncMock(return_value=None)

            await cli.main()

            mock_backup.assert_awaited_once()
            mock_confirm.assert_not_called()

    @pytest.mark.asyncio
    async def test_main_interactive_mode(self, monkeypatch):
        """main() no modo interativo chama interactive_main."""
        monkeypatch.setenv("API_ID", "12345")
        monkeypatch.setenv("API_HASH", "testhash")
        monkeypatch.setenv("SESSION_NAME", "test_session")
        monkeypatch.delenv("BOT_TOKEN", raising=False)
        monkeypatch.setattr(sys, "argv", ["prog", "-i"])

        with mock.patch("clean_telegram.cli.load_dotenv"), \
             mock.patch("clean_telegram.cli.TelegramClient") as mock_tc, \
             mock.patch("clean_telegram.cli.start_client", new_callable=mock.AsyncMock), \
             mock.patch("clean_telegram.cli.interactive_main", new_callable=mock.AsyncMock) as mock_interactive:
            mock_client = mock.AsyncMock()
            mock_tc.return_value.__aenter__ = mock.AsyncMock(return_value=mock_client)
            mock_tc.return_value.__aexit__ = mock.AsyncMock(return_value=None)

            await cli.main()

            mock_interactive.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_main_rpc_error_handling(self, monkeypatch):
        """main() trata RPCError com mensagem amigável."""
        from telethon.errors import RPCError

        monkeypatch.setenv("API_ID", "12345")
        monkeypatch.setenv("API_HASH", "testhash")
        monkeypatch.setenv("SESSION_NAME", "test_session")
        monkeypatch.delenv("BOT_TOKEN", raising=False)
        monkeypatch.setattr(sys, "argv", ["prog", "--yes"])

        with mock.patch("clean_telegram.cli.load_dotenv"), \
             mock.patch("clean_telegram.cli.TelegramClient") as mock_tc, \
             mock.patch("clean_telegram.cli.start_client", new_callable=mock.AsyncMock), \
             mock.patch("clean_telegram.cli.run_clean", new_callable=mock.AsyncMock) as mock_clean:
            mock_client = mock.AsyncMock()
            mock_tc.return_value.__aenter__ = mock.AsyncMock(return_value=mock_client)
            mock_tc.return_value.__aexit__ = mock.AsyncMock(return_value=None)
            mock_clean.side_effect = RPCError(None, "FLOOD_WAIT", 420)

            # Shouldn't raise - error is caught and logged
            await cli.main()
