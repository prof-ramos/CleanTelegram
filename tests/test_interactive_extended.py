"""Testes estendidos para o módulo interactive.py.

Cobre: interactive_clean, interactive_reports, interactive_stats,
e fluxos completos de interactive_main e interactive_backup.
"""

from unittest import mock

import pytest

from clean_telegram.interactive import (
    interactive_backup,
    interactive_clean,
    interactive_main,
    interactive_reports,
    interactive_stats,
)


# =============================================================================
# Helpers
# =============================================================================


def _mock_questionary_module():
    """Cria um mock completo do módulo questionary."""
    return mock.patch("clean_telegram.interactive.questionary")


def _setup_select_responses(mock_q, responses):
    """Configura respostas sequenciais para questionary.select().ask_async()."""
    it = iter(responses)
    mock_q.select.return_value.ask_async = mock.AsyncMock(side_effect=it)


def _setup_confirm_responses(mock_q, responses):
    """Configura respostas sequenciais para questionary.confirm().ask_async()."""
    it = iter(responses)
    mock_q.confirm.return_value.ask_async = mock.AsyncMock(side_effect=it)


# =============================================================================
# Testes: interactive_clean
# =============================================================================


class TestInteractiveClean:
    """Testes para interactive_clean()."""

    @pytest.mark.asyncio
    async def test_cancel_at_initial_confirmation(self):
        """Cancelar na primeira confirmação."""
        client = mock.AsyncMock()

        with _mock_questionary_module() as mock_q:
            mock_q.confirm.return_value.ask_async = mock.AsyncMock(return_value=False)
            with mock.patch("builtins.print"):
                await interactive_clean(client)

        # Nenhum diálogo deve ser processado
        client.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_dry_run_execution(self):
        """Executa em modo dry-run."""
        client = mock.AsyncMock()

        with _mock_questionary_module() as mock_q:
            # Primeiro confirm: aceita aviso
            # Segundo confirm: dry_run = True
            confirm_responses = iter([True, True])
            mock_q.confirm.return_value.ask_async = mock.AsyncMock(side_effect=confirm_responses)

            # Selecionar todos os diálogos
            mock_q.select.return_value.ask_async = mock.AsyncMock(return_value=0)

            with mock.patch("clean_telegram.interactive.clean_all_dialogs", new_callable=mock.AsyncMock) as mock_clean:
                mock_clean.return_value = 3
                with mock.patch("builtins.print"):
                    await interactive_clean(client)

                mock_clean.assert_awaited_once_with(client, dry_run=True, limit=0)

    @pytest.mark.asyncio
    async def test_cancel_at_limit_selection(self):
        """Cancelar na seleção de limite."""
        client = mock.AsyncMock()

        with _mock_questionary_module() as mock_q:
            confirm_responses = iter([True, True])
            mock_q.confirm.return_value.ask_async = mock.AsyncMock(side_effect=confirm_responses)

            # Selecionar "Cancelar"
            mock_q.select.return_value.ask_async = mock.AsyncMock(return_value=None)

            with mock.patch("builtins.print"):
                await interactive_clean(client)

    @pytest.mark.asyncio
    async def test_real_execution_with_double_confirm(self):
        """Execução real requer dupla confirmação."""
        client = mock.AsyncMock()

        with _mock_questionary_module() as mock_q:
            # confirm_responses: aviso=True, dry_run=False, confirm_real=True
            confirm_responses = iter([True, False, True])
            mock_q.confirm.return_value.ask_async = mock.AsyncMock(side_effect=confirm_responses)

            # Selecionar "primeiros 10"
            mock_q.select.return_value.ask_async = mock.AsyncMock(return_value=10)

            with mock.patch("clean_telegram.interactive.clean_all_dialogs", new_callable=mock.AsyncMock) as mock_clean:
                mock_clean.return_value = 10
                with mock.patch("builtins.print"):
                    await interactive_clean(client)

                mock_clean.assert_awaited_once_with(client, dry_run=False, limit=10)

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Testa que erros durante limpeza são tratados."""
        client = mock.AsyncMock()

        with _mock_questionary_module() as mock_q:
            confirm_responses = iter([True, True])
            mock_q.confirm.return_value.ask_async = mock.AsyncMock(side_effect=confirm_responses)
            mock_q.select.return_value.ask_async = mock.AsyncMock(return_value=0)

            with mock.patch("clean_telegram.interactive.clean_all_dialogs", new_callable=mock.AsyncMock) as mock_clean:
                mock_clean.side_effect = RuntimeError("connection lost")
                with mock.patch("builtins.print"):
                    await interactive_clean(client)


# =============================================================================
# Testes: interactive_reports
# =============================================================================


class TestInteractiveReports:
    """Testes para interactive_reports()."""

    @pytest.mark.asyncio
    async def test_generate_groups_csv(self):
        """Gerar relatório de grupos em CSV."""
        client = mock.AsyncMock()

        with _mock_questionary_module() as mock_q:
            # Tipo: groups, formato: csv, custom path: no
            select_responses = iter(["groups", "csv"])
            mock_q.select.return_value.ask_async = mock.AsyncMock(side_effect=select_responses)
            mock_q.confirm.return_value.ask_async = mock.AsyncMock(return_value=False)

            with mock.patch("clean_telegram.interactive.generate_groups_channels_report", new_callable=mock.AsyncMock) as mock_gen:
                mock_gen.return_value = "/tmp/groups.csv"
                with mock.patch("builtins.print"):
                    await interactive_reports(client)

                mock_gen.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_generate_all_reports(self):
        """Gerar todos os relatórios."""
        client = mock.AsyncMock()

        with _mock_questionary_module() as mock_q:
            select_responses = iter(["all", "json"])
            mock_q.select.return_value.ask_async = mock.AsyncMock(side_effect=select_responses)
            mock_q.confirm.return_value.ask_async = mock.AsyncMock(return_value=False)

            with mock.patch("clean_telegram.interactive.generate_all_reports", new_callable=mock.AsyncMock) as mock_gen:
                mock_gen.return_value = {"groups_channels": "/tmp/g.json", "contacts": "/tmp/c.json"}
                with mock.patch("builtins.print"):
                    await interactive_reports(client)

                mock_gen.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_generate_contacts_report(self):
        """Gerar relatório de contatos."""
        client = mock.AsyncMock()

        with _mock_questionary_module() as mock_q:
            select_responses = iter(["contacts", "txt"])
            mock_q.select.return_value.ask_async = mock.AsyncMock(side_effect=select_responses)
            mock_q.confirm.return_value.ask_async = mock.AsyncMock(return_value=False)

            with mock.patch("clean_telegram.interactive.generate_contacts_report", new_callable=mock.AsyncMock) as mock_gen:
                mock_gen.return_value = "/tmp/contacts.txt"
                with mock.patch("builtins.print"):
                    await interactive_reports(client)

                mock_gen.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_cancel_when_no_type_selected(self):
        """Cancelar quando nenhum tipo é selecionado."""
        client = mock.AsyncMock()

        with _mock_questionary_module() as mock_q:
            mock_q.select.return_value.ask_async = mock.AsyncMock(return_value=None)

            await interactive_reports(client)

    @pytest.mark.asyncio
    async def test_cancel_when_no_format_selected(self):
        """Cancelar quando nenhum formato é selecionado."""
        client = mock.AsyncMock()

        with _mock_questionary_module() as mock_q:
            select_responses = iter(["groups", None])
            mock_q.select.return_value.ask_async = mock.AsyncMock(side_effect=select_responses)

            await interactive_reports(client)

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Erros durante geração são tratados."""
        client = mock.AsyncMock()

        with _mock_questionary_module() as mock_q:
            select_responses = iter(["groups", "csv"])
            mock_q.select.return_value.ask_async = mock.AsyncMock(side_effect=select_responses)
            mock_q.confirm.return_value.ask_async = mock.AsyncMock(return_value=False)

            with mock.patch("clean_telegram.interactive.generate_groups_channels_report", new_callable=mock.AsyncMock) as mock_gen:
                mock_gen.side_effect = RuntimeError("failed")
                with mock.patch("builtins.print"):
                    await interactive_reports(client)


# =============================================================================
# Testes: interactive_stats
# =============================================================================


class TestInteractiveStats:
    """Testes para interactive_stats()."""

    @pytest.mark.asyncio
    async def test_displays_stats(self):
        """Testa que estatísticas são coletadas e exibidas."""
        client = mock.AsyncMock()

        me = mock.Mock()
        me.first_name = "Test"
        me.last_name = "User"
        me.username = "testuser"
        me.id = 12345
        me.verified = False
        me.bot = False
        client.get_me.return_value = me

        # Mock iter_dialogs com diferentes tipos
        from telethon.tl.types import Channel, Chat, User

        channel = mock.Mock(spec=Channel)
        channel.broadcast = True

        group = mock.Mock(spec=Channel)
        group.broadcast = False

        chat = mock.Mock(spec=Chat)

        user = mock.Mock(spec=User)

        async def mock_iter_dialogs():
            for entity in [channel, group, chat, user]:
                d = mock.Mock()
                d.entity = entity
                yield d

        client.iter_dialogs = mock_iter_dialogs

        with mock.patch("clean_telegram.interactive.console"):
            with mock.patch("clean_telegram.interactive.print_stats_table") as mock_table:
                with mock.patch("clean_telegram.interactive.print_tip"):
                    with mock.patch("clean_telegram.interactive.spinner", return_value=mock.MagicMock()):
                        await interactive_stats(client)

        # print_stats_table é chamado duas vezes (info da conta e diálogos)
        assert mock_table.call_count == 2


# =============================================================================
# Testes: interactive_main menu dispatch
# =============================================================================


class TestInteractiveMainDispatch:
    """Testes para verificar que interactive_main despacha ações corretamente."""

    def _make_me_mock(self):
        me = mock.Mock()
        me.id = 12345
        me.username = "testuser"
        me.first_name = "Test"
        me.last_name = "User"
        return me

    @pytest.mark.asyncio
    async def test_clean_dispatch(self):
        """Menu principal despacha para interactive_clean."""
        client = mock.AsyncMock()
        client.get_me.return_value = self._make_me_mock()

        call_count = {"n": 0}

        async def select_side_effect(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return "clean"
            return "exit"

        with _mock_questionary_module() as mock_q:
            mock_q.select.return_value.ask_async = mock.AsyncMock(side_effect=select_side_effect)
            mock_q.press_any_key_to_continue.return_value.ask_async = mock.AsyncMock(return_value=None)

            with mock.patch("clean_telegram.interactive.suppress_telethon_logs", return_value=mock.MagicMock()):
                with mock.patch("clean_telegram.interactive.interactive_clean", new_callable=mock.AsyncMock) as mock_clean:
                    with mock.patch("builtins.print"):
                        await interactive_main(client)

                    mock_clean.assert_awaited_once_with(client)

    @pytest.mark.asyncio
    async def test_reports_dispatch(self):
        """Menu principal despacha para interactive_reports."""
        client = mock.AsyncMock()
        client.get_me.return_value = self._make_me_mock()

        call_count = {"n": 0}

        async def select_side_effect(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return "reports"
            return "exit"

        with _mock_questionary_module() as mock_q:
            mock_q.select.return_value.ask_async = mock.AsyncMock(side_effect=select_side_effect)
            mock_q.press_any_key_to_continue.return_value.ask_async = mock.AsyncMock(return_value=None)

            with mock.patch("clean_telegram.interactive.suppress_telethon_logs", return_value=mock.MagicMock()):
                with mock.patch("clean_telegram.interactive.interactive_reports", new_callable=mock.AsyncMock) as mock_reports:
                    with mock.patch("builtins.print"):
                        await interactive_main(client)

                    mock_reports.assert_awaited_once_with(client)

    @pytest.mark.asyncio
    async def test_stats_dispatch(self):
        """Menu principal despacha para interactive_stats."""
        client = mock.AsyncMock()
        client.get_me.return_value = self._make_me_mock()

        call_count = {"n": 0}

        async def select_side_effect(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return "stats"
            return "exit"

        with _mock_questionary_module() as mock_q:
            mock_q.select.return_value.ask_async = mock.AsyncMock(side_effect=select_side_effect)
            mock_q.press_any_key_to_continue.return_value.ask_async = mock.AsyncMock(return_value=None)

            with mock.patch("clean_telegram.interactive.suppress_telethon_logs", return_value=mock.MagicMock()):
                with mock.patch("clean_telegram.interactive.interactive_stats", new_callable=mock.AsyncMock) as mock_stats:
                    with mock.patch("builtins.print"):
                        await interactive_main(client)

                    mock_stats.assert_awaited_once_with(client)

    @pytest.mark.asyncio
    async def test_exit_immediately(self):
        """Menu principal sai imediatamente ao selecionar exit."""
        client = mock.AsyncMock()
        client.get_me.return_value = self._make_me_mock()

        with _mock_questionary_module() as mock_q:
            mock_q.select.return_value.ask_async = mock.AsyncMock(return_value="exit")

            with mock.patch("clean_telegram.interactive.suppress_telethon_logs", return_value=mock.MagicMock()):
                with mock.patch("builtins.print"):
                    await interactive_main(client)

    @pytest.mark.asyncio
    async def test_none_selection_exits(self):
        """Menu principal sai se a seleção retornar None (Ctrl+C)."""
        client = mock.AsyncMock()
        client.get_me.return_value = self._make_me_mock()

        with _mock_questionary_module() as mock_q:
            mock_q.select.return_value.ask_async = mock.AsyncMock(return_value=None)

            with mock.patch("clean_telegram.interactive.suppress_telethon_logs", return_value=mock.MagicMock()):
                with mock.patch("builtins.print"):
                    await interactive_main(client)


# =============================================================================
# Testes: interactive_backup (happy path)
# =============================================================================


class TestInteractiveBackupHappyPath:
    """Testes para o fluxo completo de interactive_backup."""

    @pytest.mark.asyncio
    async def test_backup_json_without_media(self):
        """Backup completo em JSON sem mídia."""
        client = mock.AsyncMock()

        entity = mock.Mock()
        entity.id = -1001234567890
        entity.title = "Test Group"

        async def mock_get_entity(chat_id):
            return entity

        client.get_entity = mock_get_entity

        with _mock_questionary_module() as mock_q:
            # text: chat_id
            mock_q.text.return_value.ask_async = mock.AsyncMock(return_value="@test")

            # select: json format
            mock_q.select.return_value.ask_async = mock.AsyncMock(return_value="json")

            # confirm: no media, no cloud, yes to confirm
            confirm_responses = iter([False, False, True])
            mock_q.confirm.return_value.ask_async = mock.AsyncMock(side_effect=confirm_responses)

            with mock.patch("clean_telegram.interactive.backup_group_with_media", new_callable=mock.AsyncMock) as mock_backup:
                mock_backup.return_value = {
                    "messages_count": 10,
                    "participants_count": 5,
                }
                with mock.patch("builtins.print"):
                    await interactive_backup(client)

                mock_backup.assert_awaited_once()
                call_kwargs = mock_backup.call_args
                assert call_kwargs[0][2] == "backups"  # output dir
                assert call_kwargs[0][3] == "json"  # format

    @pytest.mark.asyncio
    async def test_backup_cancel_at_final_confirm(self):
        """Cancelar na confirmação final."""
        client = mock.AsyncMock()

        entity = mock.Mock()
        entity.id = -100
        entity.title = "Test"

        async def mock_get_entity(chat_id):
            return entity

        client.get_entity = mock_get_entity

        with _mock_questionary_module() as mock_q:
            mock_q.text.return_value.ask_async = mock.AsyncMock(return_value="@test")
            mock_q.select.return_value.ask_async = mock.AsyncMock(return_value="json")

            # confirm: no media, no cloud, NO to final confirm
            confirm_responses = iter([False, False, False])
            mock_q.confirm.return_value.ask_async = mock.AsyncMock(side_effect=confirm_responses)

            with mock.patch("builtins.print"):
                await interactive_backup(client)

    @pytest.mark.asyncio
    async def test_backup_error_handling(self):
        """Erros durante backup são tratados."""
        client = mock.AsyncMock()

        entity = mock.Mock()
        entity.id = -100
        entity.title = "Test"

        async def mock_get_entity(chat_id):
            return entity

        client.get_entity = mock_get_entity

        with _mock_questionary_module() as mock_q:
            mock_q.text.return_value.ask_async = mock.AsyncMock(return_value="@test")
            mock_q.select.return_value.ask_async = mock.AsyncMock(return_value="csv")

            confirm_responses = iter([False, False, True])
            mock_q.confirm.return_value.ask_async = mock.AsyncMock(side_effect=confirm_responses)

            with mock.patch("clean_telegram.interactive.backup_group_with_media", new_callable=mock.AsyncMock) as mock_backup:
                mock_backup.side_effect = RuntimeError("failed")
                with mock.patch("builtins.print"):
                    await interactive_backup(client)
