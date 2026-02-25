"""Testes para o módulo ui.py (Rich UI)."""

import logging
from unittest import mock

import pytest
from rich.progress import Progress
from rich.table import Table

from clean_telegram import ui


class TestSuppressTelethonLogs:
    """Testes para suppress_telethon_logs()."""

    def test_should_set_critical_level_during_context(self, telethon_logger):
        """Deve definir logger level como CRITICAL dentro do contexto."""
        with ui.suppress_telethon_logs():
            assert telethon_logger.level == logging.CRITICAL

    def test_should_restore_level_after_context(self):
        """Deve restaurar level original após sair do contexto."""
        telethon_logger = logging.getLogger("telethon")
        original_level = logging.INFO
        telethon_logger.setLevel(original_level)

        with ui.suppress_telethon_logs():
            pass  # Mudou para CRITICAL

        assert telethon_logger.level == original_level

    def test_should_work_when_already_critical(self):
        """Deve funcionar corretamente mesmo se já está CRITICAL."""
        telethon_logger = logging.getLogger("telethon")
        telethon_logger.setLevel(logging.CRITICAL)

        with ui.suppress_telethon_logs():
            assert telethon_logger.level == logging.CRITICAL


class TestSpinner:
    """Testes para spinner()."""

    def test_should_return_context_manager(self):
        """Deve retornar um context manager do Rich."""
        result = ui.spinner("Testando")
        assert hasattr(result, "__enter__")
        assert hasattr(result, "__exit__")

    def test_should_use_default_spinner_type(self):
        """Deve usar spinner type 'dots' por padrão."""
        result = ui.spinner("Test")
        assert result is not None

    def test_should_accept_custom_spinner_type(self):
        """Deve aceitar tipo de spinner customizado."""
        result = ui.spinner("Test", spinner_type="line")
        assert result is not None


class TestProgressBar:
    """Testes para progress_bar()."""

    def test_should_return_context_manager(self):
        """Deve retornar um context manager."""
        cm = ui.progress_bar("Testando", total=10)
        assert hasattr(cm, "__enter__")
        assert hasattr(cm, "__exit__")

    def test_should_yield_progress_and_task(self):
        """Deve fornecer (Progress, task_id) ao entrar no contexto."""
        with ui.progress_bar("Testando", total=5) as (prog, task):
            assert isinstance(prog, Progress)
            assert task is not None

    def test_should_work_without_total(self):
        """Deve funcionar com total=None (indeterminado)."""
        with ui.progress_bar("Indeterminado") as (prog, task):
            assert isinstance(prog, Progress)

    def test_should_allow_advance(self):
        """Deve permitir avançar o progresso sem erros."""
        with ui.progress_bar("Avançando", total=3) as (prog, task):
            prog.advance(task)
            prog.advance(task)
            prog.advance(task)


class TestSetVerbosity:
    """Testes para set_verbosity()."""

    def teardown_method(self):
        """Restaurar verbosidade padrão após cada teste."""
        ui.set_verbosity()

    def test_defaults_are_false(self):
        """Por padrão, verbose e quiet são False."""
        ui.set_verbosity()
        assert ui.is_verbose() is False
        assert ui.is_quiet() is False

    def test_set_verbose(self):
        """Deve ativar modo verbose."""
        ui.set_verbosity(verbose=True)
        assert ui.is_verbose() is True
        assert ui.is_quiet() is False

    def test_set_quiet(self):
        """Deve ativar modo quiet."""
        ui.set_verbosity(quiet=True)
        assert ui.is_quiet() is True
        assert ui.is_verbose() is False

    def test_reset_after_setting(self):
        """Deve resetar ao chamar sem argumentos."""
        ui.set_verbosity(verbose=True)
        ui.set_verbosity()
        assert ui.is_verbose() is False


class TestPrintStatsTable:
    """Testes para print_stats_table()."""

    def test_should_create_table_with_title(self, mock_console):
        """Deve criar Table com título."""
        ui.print_stats_table("Teste", {"chave": "valor"})

        mock_console.print.assert_called_once()
        call_args = mock_console.print.call_args
        assert isinstance(call_args[0][0], Table)

    def test_should_format_integers_with_separator(self, mock_console):
        """Deve formatar inteiros com separador de milhares."""
        ui.print_stats_table("Teste", {"count": 1234567})

        mock_console.print.assert_called_once()
        call_args = mock_console.print.call_args
        table = call_args[0][0]
        assert isinstance(table, Table)

    def test_should_handle_non_integers_as_string(self, mock_console):
        """Deve tratar não-inteiros como string."""
        ui.print_stats_table("Teste", {"name": "Teste", "float": 3.14})

        mock_console.print.assert_called_once()
        call_args = mock_console.print.call_args
        table = call_args[0][0]
        assert isinstance(table, Table)

    def test_should_accept_custom_title_style(self, mock_console):
        """Deve aceitar estilo customizado para título."""
        ui.print_stats_table("Teste", {"a": 1}, title_style="bold red")

        mock_console.print.assert_called_once()


class TestPrintSuccess:
    """Testes para print_success()."""

    def test_should_format_with_green_emoji(self, mock_console):
        """Deve formatar mensagem com emoji verde."""
        ui.print_success("Sucesso!")

        mock_console.print.assert_called_once()
        call_args = mock_console.print.call_args[0][0]
        assert "✅" in call_args
        assert "[bold green]" in call_args


class TestPrintError:
    """Testes para print_error()."""

    def test_should_format_with_red_emoji(self, mock_console):
        """Deve formatar mensagem com emoji vermelho."""
        ui.print_error("Erro!")

        mock_console.print.assert_called_once()
        call_args = mock_console.print.call_args[0][0]
        assert "❌" in call_args
        assert "[bold red]" in call_args

    def test_should_print_hint_when_provided(self, mock_console):
        """Deve exibir dica quando hint é fornecido."""
        ui.print_error("Erro!", hint="Tente novamente.")

        assert mock_console.print.call_count == 2
        hint_call = mock_console.print.call_args_list[1][0][0]
        assert "💡" in hint_call
        assert "Tente novamente." in hint_call

    def test_should_not_print_hint_when_none(self, mock_console):
        """Não deve imprimir segunda linha se hint=None."""
        ui.print_error("Erro!")

        assert mock_console.print.call_count == 1


class TestPrintWarning:
    """Testes para print_warning()."""

    def test_should_format_with_yellow_emoji(self, mock_console):
        """Deve formatar mensagem com emoji amarelo."""
        ui.print_warning("Aviso!")

        call_args = mock_console.print.call_args[0][0]
        assert "⚠️" in call_args
        assert "[bold yellow]" in call_args


class TestPrintInfo:
    """Testes para print_info()."""

    def test_should_format_with_blue_emoji(self, mock_console):
        """Deve formatar mensagem com emoji azul."""
        ui.print_info("Info!")

        call_args = mock_console.print.call_args[0][0]
        assert "ℹ️" in call_args
        assert "[bold blue]" in call_args


class TestPrintTip:
    """Testes para print_tip()."""

    def test_should_format_with_dim_emoji(self, mock_console):
        """Deve formatar dica com estilo dim."""
        ui.print_tip("Dica!")

        call_args = mock_console.print.call_args[0][0]
        assert "💡" in call_args
        assert "[dim]" in call_args


class TestPrintFloodwait:
    """Testes para print_floodwait()."""

    def test_should_print_floodwait_message(self, mock_console):
        """Deve exibir mensagem de FloodWait formatada."""
        ui.print_floodwait("Grupo Teste", 10, 1, 5)

        mock_console.print.assert_called_once()
        call_args = mock_console.print.call_args[0][0]
        assert "FloodWait" in call_args
        assert "Grupo Teste" in call_args
        assert "10s" in call_args
        assert "1/5" in call_args


class TestCustomStyle:
    """Testes para CUSTOM_STYLE."""

    def test_custom_style_is_defined(self):
        """CUSTOM_STYLE deve estar definido em ui.py."""
        import questionary
        assert isinstance(ui.CUSTOM_STYLE, questionary.Style)
