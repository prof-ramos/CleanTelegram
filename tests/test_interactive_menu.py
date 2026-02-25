"""Testes para funções do menu interativo (interactive_main, interactive_stats)."""

from unittest import mock

import pytest

from tests.conftest import AsyncIteratorMock


# =============================================================================
# Testes: interactive_stats
# =============================================================================


class TestInteractiveStats:
    """Testes para interactive_stats()."""

    @pytest.fixture
    def mock_client(self):
        """Mock de cliente com get_me e iter_dialogs configurados."""
        from telethon.tl.types import Channel, Chat, User

        client = mock.AsyncMock()

        me = mock.Mock()
        me.id = 999888
        me.username = "testuser"
        me.first_name = "Test"
        me.last_name = "User"
        me.verified = False
        me.bot = False
        client.get_me = mock.AsyncMock(return_value=me)

        # Criar entidades para diferentes tipos de diálogos
        supergroup = mock.Mock(spec=Channel)
        supergroup.broadcast = False
        supergroup.megagroup = True

        broadcast_channel = mock.Mock(spec=Channel)
        broadcast_channel.broadcast = True
        broadcast_channel.megagroup = False

        legacy_chat = mock.Mock(spec=Chat)

        regular_user = mock.Mock(spec=User)
        regular_user.bot = False

        bot_user = mock.Mock(spec=User)
        bot_user.bot = True

        # Criar diálogos
        dialogs = []
        for entity, unread in [
            (supergroup, 5),
            (broadcast_channel, 0),
            (legacy_chat, 2),
            (regular_user, 0),
            (bot_user, 1),
        ]:
            d = mock.Mock()
            d.entity = entity
            d.unread_count = unread
            dialogs.append(d)

        client.iter_dialogs = mock.Mock(return_value=AsyncIteratorMock(dialogs))
        return client

    @pytest.mark.asyncio
    async def test_should_display_account_stats(self, mock_client):
        """Deve exibir estatísticas da conta sem erros."""
        from clean_telegram.interactive import interactive_stats

        with mock.patch("clean_telegram.interactive.console") as mock_console:
            with mock.patch("clean_telegram.interactive.print_stats_table") as mock_table:
                with mock.patch("clean_telegram.interactive.print_tip"):
                    with mock.patch("clean_telegram.interactive.spinner") as mock_spinner:
                        cm = mock.MagicMock()
                        mock_spinner.return_value = cm
                        await interactive_stats(mock_client)

        # Deve chamar print_stats_table pelo menos duas vezes (conta + diálogos)
        assert mock_table.call_count >= 2

    @pytest.mark.asyncio
    async def test_should_count_dialog_types_correctly(self, mock_client):
        """Deve contar corretamente os tipos de diálogos."""
        from clean_telegram.interactive import interactive_stats

        captured_calls = []

        def capture_table(title, data, **kwargs):
            captured_calls.append((title, data))

        with mock.patch("clean_telegram.interactive.console"):
            with mock.patch("clean_telegram.interactive.print_stats_table", side_effect=capture_table):
                with mock.patch("clean_telegram.interactive.print_tip"):
                    with mock.patch("clean_telegram.interactive.spinner") as mock_spinner:
                        cm = mock.MagicMock()
                        mock_spinner.return_value = cm
                        await interactive_stats(mock_client)

        # Encontrar a chamada com dados de diálogos
        dialog_call = next(
            (title, data) for title, data in captured_calls if "Diálogos" in title
        )
        data = dialog_call[1]

        assert data["Total"] == 5
        assert data["Supergrupos"] == 1
        assert data["Canais broadcast"] == 1
        assert data["Grupos legados"] == 1
        assert data["Usuários (DM)"] == 1
        assert data["Bots"] == 1
        assert data["Com mensagens não lidas"] == 3  # unread: 5, 2, 1

    @pytest.mark.asyncio
    async def test_should_handle_empty_dialogs(self):
        """Deve funcionar corretamente com nenhum diálogo."""
        from clean_telegram.interactive import interactive_stats

        client = mock.AsyncMock()
        me = mock.Mock()
        me.id = 1
        me.username = "u"
        me.first_name = "F"
        me.last_name = None
        me.verified = False
        me.bot = False
        client.get_me = mock.AsyncMock(return_value=me)
        client.iter_dialogs = mock.Mock(return_value=AsyncIteratorMock([]))

        with mock.patch("clean_telegram.interactive.console"):
            with mock.patch("clean_telegram.interactive.print_stats_table"):
                with mock.patch("clean_telegram.interactive.print_tip"):
                    with mock.patch("clean_telegram.interactive.spinner") as mock_spinner:
                        cm = mock.MagicMock()
                        mock_spinner.return_value = cm
                        await interactive_stats(client)


# =============================================================================
# Testes: interactive_main com args pre-routing
# =============================================================================


class TestInteractiveMainArgsRouting:
    """Testes para routing de args em interactive_main."""

    @pytest.mark.asyncio
    async def test_should_route_to_reports_when_args_report_set(self):
        """Deve chamar interactive_reports quando args.report está definido."""
        from clean_telegram.interactive import interactive_main

        client = mock.AsyncMock()
        args = mock.Mock()
        args.report = "groups"
        args.backup_group = None

        with mock.patch(
            "clean_telegram.interactive.interactive_reports",
        ) as mock_reports:
            mock_reports.return_value = "ok"
            await interactive_main(client, args=args)

        mock_reports.assert_called_once_with(client)

    @pytest.mark.asyncio
    async def test_should_route_to_backup_when_args_backup_group_set(self):
        """Deve chamar interactive_backup com prefill quando args.backup_group está definido."""
        from clean_telegram.interactive import interactive_main

        client = mock.AsyncMock()
        args = mock.Mock()
        args.report = None
        args.backup_group = "-1001234567890"

        with mock.patch(
            "clean_telegram.interactive.interactive_backup",
        ) as mock_backup:
            mock_backup.return_value = "ok"
            await interactive_main(client, args=args)

        mock_backup.assert_called_once_with(client, prefill_chat="-1001234567890")

    @pytest.mark.asyncio
    async def test_should_show_session_summary_on_exit(self):
        """Deve mostrar resumo da sessão com histórico antes de sair."""
        from clean_telegram.interactive import interactive_main

        client = mock.AsyncMock()

        me = mock.Mock()
        me.id = 999
        me.username = "test"
        me.first_name = "Test"
        client.get_me = mock.AsyncMock(return_value=me)

        call_count = [0]

        async def mock_select_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return "stats"
            return "exit"

        with mock.patch("clean_telegram.interactive.questionary") as mock_q:
            mock_q.select.return_value.ask_async = mock.AsyncMock(
                side_effect=mock_select_side_effect
            )
            mock_q.press_any_key_to_continue.return_value.ask_async = mock.AsyncMock(
                return_value=None
            )

            with mock.patch(
                "clean_telegram.interactive.interactive_stats"
            ) as mock_stats:
                mock_stats.return_value = None
                with mock.patch("clean_telegram.interactive.console") as mock_console:
                    with mock.patch("clean_telegram.interactive.print_stats_table") as mock_table:
                        await interactive_main(client)

        # Deve ter chamado interactive_stats
        mock_stats.assert_called_once_with(client)
        # Deve ter mostrado o resumo da sessão (print_stats_table chamado para resumo)
        assert mock_table.call_count >= 1


    @pytest.mark.asyncio
    async def test_should_route_to_clean_action(self):
        """Deve chamar interactive_clean quando action == 'clean'."""
        from clean_telegram.interactive import interactive_main

        client = mock.AsyncMock()
        me = mock.Mock()
        me.id = 1
        me.username = "u"
        me.first_name = "F"
        client.get_me = mock.AsyncMock(return_value=me)

        call_count = [0]

        async def mock_select(action_count=call_count):
            action_count[0] += 1
            return "clean" if action_count[0] == 1 else "exit"

        with mock.patch("clean_telegram.interactive.questionary") as mock_q:
            mock_q.select.return_value.ask_async = mock.AsyncMock(side_effect=mock_select)
            mock_q.press_any_key_to_continue.return_value.ask_async = mock.AsyncMock(return_value=None)

            with mock.patch("clean_telegram.interactive.interactive_clean", return_value="concluído") as mock_clean:
                with mock.patch("clean_telegram.interactive.console"):
                    with mock.patch("clean_telegram.interactive.print_stats_table"):
                        await interactive_main(client)

        mock_clean.assert_called_once_with(client, args=None)

    @pytest.mark.asyncio
    async def test_should_route_to_reports_action(self):
        """Deve chamar interactive_reports quando action == 'reports'."""
        from clean_telegram.interactive import interactive_main

        client = mock.AsyncMock()
        me = mock.Mock()
        me.id = 1
        me.username = "u"
        me.first_name = "F"
        client.get_me = mock.AsyncMock(return_value=me)

        call_count = [0]

        async def mock_select(action_count=call_count):
            action_count[0] += 1
            return "reports" if action_count[0] == 1 else "exit"

        with mock.patch("clean_telegram.interactive.questionary") as mock_q:
            mock_q.select.return_value.ask_async = mock.AsyncMock(side_effect=mock_select)
            mock_q.press_any_key_to_continue.return_value.ask_async = mock.AsyncMock(return_value=None)

            with mock.patch("clean_telegram.interactive.interactive_reports", return_value="ok") as mock_reports:
                with mock.patch("clean_telegram.interactive.console"):
                    with mock.patch("clean_telegram.interactive.print_stats_table"):
                        await interactive_main(client)

        mock_reports.assert_called_once_with(client)

    @pytest.mark.asyncio
    async def test_should_route_to_settings_action(self):
        """Deve chamar interactive_settings quando action == 'settings'."""
        from clean_telegram.interactive import interactive_main

        client = mock.AsyncMock()
        me = mock.Mock()
        me.id = 1
        me.username = "u"
        me.first_name = "F"
        client.get_me = mock.AsyncMock(return_value=me)

        call_count = [0]

        async def mock_select(action_count=call_count):
            action_count[0] += 1
            return "settings" if action_count[0] == 1 else "exit"

        with mock.patch("clean_telegram.interactive.questionary") as mock_q:
            mock_q.select.return_value.ask_async = mock.AsyncMock(side_effect=mock_select)
            mock_q.press_any_key_to_continue.return_value.ask_async = mock.AsyncMock(return_value=None)

            with mock.patch("clean_telegram.interactive.interactive_settings", return_value=None) as mock_settings:
                with mock.patch("clean_telegram.interactive.console"):
                    with mock.patch("clean_telegram.interactive.print_stats_table"):
                        await interactive_main(client)

        mock_settings.assert_called_once_with(client)


# =============================================================================
# Testes: interactive_clean (cancelamento)
# =============================================================================


class TestInteractiveClean:
    """Testes para interactive_clean()."""

    @pytest.mark.asyncio
    async def test_should_return_cancelado_when_initial_confirm_is_false(self):
        """Deve retornar 'cancelado' quando usuário nega confirmação inicial."""
        from clean_telegram.interactive import interactive_clean

        client = mock.AsyncMock()

        with mock.patch("clean_telegram.interactive.questionary") as mock_q:
            mock_q.confirm.return_value.ask_async = mock.AsyncMock(return_value=False)
            with mock.patch("clean_telegram.interactive.console"):
                with mock.patch("clean_telegram.interactive.load_config"):
                    result = await interactive_clean(client)

        assert result == "cancelado"

    @pytest.mark.asyncio
    async def test_should_return_cancelado_when_limit_is_none(self):
        """Deve retornar 'cancelado' quando usuário cancela na seleção de limite."""
        from clean_telegram.interactive import interactive_clean

        client = mock.AsyncMock()

        confirm_count = [0]

        async def mock_confirm():
            confirm_count[0] += 1
            if confirm_count[0] == 1:
                return True  # Confirma ação destrutiva
            return False  # Não usar whitelist

        with mock.patch("clean_telegram.interactive.questionary") as mock_q:
            mock_q.confirm.return_value.ask_async = mock.AsyncMock(side_effect=mock_confirm)
            mock_q.select.return_value.ask_async = mock.AsyncMock(return_value=None)  # Cancelado na seleção
            with mock.patch("clean_telegram.interactive.console"):
                with mock.patch("clean_telegram.interactive.load_config") as mock_cfg:
                    mock_cfg.return_value.clean_whitelist = []
                    mock_cfg.return_value.default_dry_run = True
                    mock_cfg.return_value.default_dialog_limit = 0
                    result = await interactive_clean(client)

        assert result == "cancelado"
