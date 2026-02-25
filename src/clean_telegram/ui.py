"""Módulo de UI rica para o CleanTelegram.

Centraliza elementos visuais usando Rich para spinners, tabelas e formatação.
"""

import logging
from contextlib import contextmanager
from typing import Any, ContextManager, Generator

import questionary
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
)
from rich.table import Table

# Console global para uso em todo o projeto
console = Console()

# Estado de verbosidade global
_verbose: bool = False
_quiet: bool = False

# Estilo padrão para Questionary (compartilhado por todos os menus)
CUSTOM_STYLE = questionary.Style(
    [
        ("qmark", "fg:#67b7a1 bold"),
        ("question", "bold"),
        ("selected", "fg:#cc5454"),
        ("pointer", "fg:#67b7a1 bold"),
        ("highlighted", "fg:#67b7a1 bold"),
        ("answer", "fg:#f6b93b bold"),
        ("separator", "fg:#6e6e6e"),
    ]
)


def set_verbosity(*, verbose: bool = False, quiet: bool = False) -> None:
    """Configura nível de verbosidade global da UI.

    Args:
        verbose: Se True, ativa saída detalhada.
        quiet: Se True, suprime mensagens informativas.
    """
    global _verbose, _quiet
    _verbose = verbose
    _quiet = quiet


def is_verbose() -> bool:
    """Retorna True se modo verbose está ativo."""
    return _verbose


def is_quiet() -> bool:
    """Retorna True se modo quiet está ativo."""
    return _quiet


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


def spinner(message: str, spinner_type: str = "dots") -> ContextManager[Any]:
    """Retorna context manager de status com spinner animado.

    Args:
        message: Texto a exibir junto ao spinner
        spinner_type: Tipo do spinner (dots, line, bouncingBall, etc.)

    Returns:
        Context manager do Rich status
    """
    return console.status(message, spinner=spinner_type)


@contextmanager
def progress_bar(
    description: str,
    total: int | None = None,
) -> Generator[tuple[Progress, Any], None, None]:
    """Context manager de barra de progresso Rich.

    Args:
        description: Texto da tarefa.
        total: Total de itens (None = indeterminado).

    Example:
        with progress_bar("Processando", total=100) as (prog, task):
            for item in items:
                process(item)
                prog.advance(task)
    """
    columns = [
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
    ]
    with Progress(*columns, console=console) as prog:
        task = prog.add_task(description, total=total)
        yield prog, task


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
        # Formatar números com separador de milhares (respeitando locale)
        if isinstance(value, int):
            try:
                formatted_value = f"[bold]{value:n}[/]"
            except ValueError:
                formatted_value = f"[bold]{value:,}[/]".replace(",", ".")
        else:
            formatted_value = str(value)
        table.add_row(key, formatted_value)

    console.print(table)


def print_success(message: str) -> None:
    """Exibe mensagem de sucesso formatada."""
    console.print(f"[bold green]✅ {message}[/]")


def print_error(message: str, hint: str | None = None) -> None:
    """Exibe mensagem de erro formatada.

    Args:
        message: Mensagem de erro principal.
        hint: Dica opcional de como resolver o problema.
    """
    console.print(f"[bold red]❌ {message}[/]")
    if hint:
        console.print(f"[dim]   💡 {hint}[/]")


def print_warning(message: str) -> None:
    """Exibe mensagem de aviso formatada."""
    console.print(f"[bold yellow]⚠️  {message}[/]")


def print_info(message: str) -> None:
    """Exibe mensagem informativa formatada."""
    console.print(f"[bold blue]ℹ️  {message}[/]")


def print_tip(message: str) -> None:
    """Exibe dica formatada."""
    console.print(f"[dim]💡 {message}[/]")


def print_floodwait(
    dialog_name: str, wait_seconds: int, attempt: int, max_retries: int
) -> None:
    """Exibe aviso de FloodWait visível ao usuário durante modo interativo."""
    console.print(
        f"[bold yellow]⏳ Rate limit (FloodWait) em '[cyan]{dialog_name}[/cyan]'. "
        f"Aguardando [bold]{wait_seconds}s[/bold] "
        f"(tentativa {attempt}/{max_retries})...[/]"
    )
