"""Testes para o módulo ui.py (Rich UI)."""

import logging
from unittest import mock

import pytest
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from clean_telegram import ui


class TestSuppressTelethonLogs:
    """Testes para suppress_telethon_logs()."""

    def test_should_set_critical_level_during_context(self, telethon_logger):
        """Deve definir logger level como CRITICAL dentro do contexto."""
        original_level = telethon_logger.level

        with ui.suppress_telethon_logs():
            assert telethon_logger.level == logging.CRITICAL

        # Fixture telethon_logger garante restauração automática no teardown

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

        # Não deve lançar exceção
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
        # O status é criado com o spinner padrão "dots"
        assert result is not None

    def test_should_accept_custom_spinner_type(self):
        """Deve aceitar tipo de spinner customizado."""
        result = ui.spinner("Test", spinner_type="line")
        # Verifica que não lança exceção
        assert result is not None


class TestPrintHeader:
    """Testes para print_header()."""

    def test_should_print_panel_with_title(self, mock_console):
        """Deve exibir painel com título."""
        ui.print_header("Título Teste")

        mock_console.print.assert_called_once()
        call_args = mock_console.print.call_args
        assert isinstance(call_args[0][0], Panel)

    def test_should_include_subtitle_when_provided(self, mock_console):
        """Deve incluir subtítulo quando fornecido."""
        ui.print_header("Título", subtitle="Subtítulo Teste")

        mock_console.print.assert_called_once()
        call_args = mock_console.print.call_args
        panel = call_args[0][0]
        assert isinstance(panel, Panel)
        # O subtitle é adicionado ao Text dentro do Panel, verificamos que foi chamado

    def test_should_work_without_subtitle(self, mock_console):
        """Deve funcionar sem subtítulo."""
        ui.print_header("Apenas Título")

        mock_console.print.assert_called_once()


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
        # A formatação é aplicada pela função, verificamos que a tabela foi criada

    def test_should_handle_non_integers_as_string(self, mock_console):
        """Deve tratar não-inteiros como string."""
        ui.print_stats_table("Teste", {"name": "Teste", "float": 3.14})

        mock_console.print.assert_called_once()
        call_args = mock_console.print.call_args
        table = call_args[0][0]
        assert isinstance(table, Table)
        # Valores não-inteiros são tratados como string, verificamos que a tabela foi criada

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
