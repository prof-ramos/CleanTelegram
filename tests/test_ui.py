"""Testes para o módulo ui.py.

Cobre: suppress_telethon_logs, print_header, print_stats_table,
print_success/error/warning/info/tip, e spinner.
"""

import logging
from io import StringIO
from unittest import mock

from rich.console import Console

from clean_telegram.ui import (
    print_error,
    print_header,
    print_info,
    print_stats_table,
    print_success,
    print_tip,
    print_warning,
    spinner,
    suppress_telethon_logs,
)


# =============================================================================
# Testes: suppress_telethon_logs
# =============================================================================


class TestSuppressTelethonLogs:
    """Testes para suppress_telethon_logs()."""

    def test_suppresses_and_restores_log_level(self):
        telethon_logger = logging.getLogger("telethon")
        original = telethon_logger.level

        with suppress_telethon_logs():
            assert telethon_logger.level == logging.CRITICAL

        assert telethon_logger.level == original

    def test_restores_on_exception(self):
        telethon_logger = logging.getLogger("telethon")
        original = telethon_logger.level

        try:
            with suppress_telethon_logs():
                assert telethon_logger.level == logging.CRITICAL
                raise ValueError("test error")
        except ValueError:
            pass

        assert telethon_logger.level == original


# =============================================================================
# Testes: spinner
# =============================================================================


class TestSpinner:
    """Testes para spinner()."""

    def test_returns_context_manager(self):
        with mock.patch("clean_telegram.ui.console") as mock_console:
            mock_console.status.return_value = mock.MagicMock()
            result = spinner("Loading...")
            mock_console.status.assert_called_once_with("Loading...", spinner="dots")


# =============================================================================
# Testes: print_header
# =============================================================================


class TestPrintHeader:
    """Testes para print_header()."""

    def test_header_without_subtitle(self):
        with mock.patch("clean_telegram.ui.console") as mock_console:
            print_header("Test Title")
            mock_console.print.assert_called_once()

    def test_header_with_subtitle(self):
        with mock.patch("clean_telegram.ui.console") as mock_console:
            print_header("Test Title", subtitle="Sub")
            mock_console.print.assert_called_once()


# =============================================================================
# Testes: print_stats_table
# =============================================================================


class TestPrintStatsTable:
    """Testes para print_stats_table()."""

    def test_formats_integers(self):
        with mock.patch("clean_telegram.ui.console") as mock_console:
            print_stats_table("Stats", {"Count": 1000, "Name": "Test"})
            mock_console.print.assert_called_once()

    def test_handles_value_error_fallback(self):
        """Testa fallback quando :n formatter falha."""
        with mock.patch("clean_telegram.ui.console") as mock_console:
            # Usar um objeto custom que levanta ValueError ao formatar com :n
            class BadInt(int):
                def __format__(self, fmt):
                    if fmt == "n":
                        raise ValueError("bad locale")
                    return super().__format__(fmt)

            print_stats_table("Stats", {"Count": BadInt(1000)})

            mock_console.print.assert_called_once()

    def test_handles_string_values(self):
        with mock.patch("clean_telegram.ui.console") as mock_console:
            print_stats_table("Stats", {"Status": "OK", "Name": "Test"})
            mock_console.print.assert_called_once()


# =============================================================================
# Testes: print_success/error/warning/info/tip
# =============================================================================


class TestPrintFunctions:
    """Testes para funções de output formatado."""

    def test_print_success(self):
        with mock.patch("clean_telegram.ui.console") as mock_console:
            print_success("done")
            mock_console.print.assert_called_once()
            call_arg = mock_console.print.call_args[0][0]
            assert "done" in call_arg

    def test_print_error(self):
        with mock.patch("clean_telegram.ui.console") as mock_console:
            print_error("failed")
            call_arg = mock_console.print.call_args[0][0]
            assert "failed" in call_arg

    def test_print_warning(self):
        with mock.patch("clean_telegram.ui.console") as mock_console:
            print_warning("caution")
            call_arg = mock_console.print.call_args[0][0]
            assert "caution" in call_arg

    def test_print_info(self):
        with mock.patch("clean_telegram.ui.console") as mock_console:
            print_info("note")
            call_arg = mock_console.print.call_args[0][0]
            assert "note" in call_arg

    def test_print_tip(self):
        with mock.patch("clean_telegram.ui.console") as mock_console:
            print_tip("hint")
            call_arg = mock_console.print.call_args[0][0]
            assert "hint" in call_arg
