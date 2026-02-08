"""Módulo de UI rica para o CleanTelegram.

Centraliza elementos visuais usando Rich para spinners, tabelas e formatação.
"""

import logging
from contextlib import contextmanager
from typing import Any, Generator

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

# Console global para uso em todo o projeto
console = Console()


@contextmanager
def suppress_telethon_logs() -> Generator[None, None, None]:
    """Suprime logs do Telethon temporariamente durante interações.

    Útil para evitar que mensagens de log poluam a UI durante prompts.
    """
    telethon_logger = logging.getLogger("telethon")
    original_level = telethon_logger.level
    telethon_logger.setLevel(logging.CRITICAL)
    try:
        yield
    finally:
        telethon_logger.setLevel(original_level)


def spinner(message: str, spinner_type: str = "dots"):
    """Retorna context manager de status com spinner animado.

    Args:
        message: Texto a exibir junto ao spinner
        spinner_type: Tipo do spinner (dots, line, bouncingBall, etc.)

    Returns:
        Context manager do Rich status
    """
    return console.status(message, spinner=spinner_type)


def print_header(title: str, subtitle: str | None = None) -> None:
    """Exibe cabeçalho formatado com painel.

    Args:
        title: Título principal
        subtitle: Subtítulo opcional
    """
    text = Text(title, style="bold cyan")
    if subtitle:
        text.append(f"\n{subtitle}", style="dim")
    console.print(Panel(text, border_style="cyan"))


def print_stats_table(
    title: str, data: dict[str, Any], title_style: str = "bold"
) -> None:
    """Exibe tabela formatada de estatísticas.

    Args:
        title: Título da tabela
        data: Dicionário com chave-valor para exibir
        title_style: Estilo do título
    """
    table = Table(title=title, show_header=False, title_style=title_style)
    table.add_column("Campo", style="dim")
    table.add_column("Valor", justify="right")

    for key, value in data.items():
        # Formatar números com separador de milhares
        if isinstance(value, int):
            formatted_value = f"[bold]{value:,}[/]".replace(",", ".")
        else:
            formatted_value = str(value)
        table.add_row(key, formatted_value)

    console.print(table)


def print_success(message: str) -> None:
    """Exibe mensagem de sucesso formatada."""
    console.print(f"[bold green]✅ {message}[/]")


def print_error(message: str) -> None:
    """Exibe mensagem de erro formatada."""
    console.print(f"[bold red]❌ {message}[/]")


def print_warning(message: str) -> None:
    """Exibe mensagem de aviso formatada."""
    console.print(f"[bold yellow]⚠️  {message}[/]")


def print_info(message: str) -> None:
    """Exibe mensagem informativa formatada."""
    console.print(f"[bold blue]ℹ️  {message}[/]")


def print_tip(message: str) -> None:
    """Exibe dica formatada."""
    console.print(f"[dim]💡 {message}[/]")
