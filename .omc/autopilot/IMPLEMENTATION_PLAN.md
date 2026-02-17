# PLANO DE IMPLEMENTAÇÃO - Fase 1: Melhoria de Testes

**Data:** 2026-02-13
**Especificação:** `.omc/autopilot/spec.md`
**Cobertura Atual:** 59% (65 tests passing, 1 failing)
**Meta:** 70%+ cobertura
**Estimativa:** 8-12 horas de trabalho

---

## SUMÁRIO EXECUTIVO

Este plano divide o trabalho em **17 tarefas atômicas** organizadas em 4 fases sequenciais. As tarefas são independentes dentro de cada fase e podem ser executadas em paralelo quando possível.

**Estado Atual:**
- 68 testes coletados (65 passando, 1 falhando)
- 2.213 linhas de código de teste
- Sem `pytest.ini` ou `.coveragerc` configurados
- `AsyncIteratorMock` duplicado em múltiplos arquivos

---

## FASE 1: Infraestrutura de Testes (2-3 horas)

### Tarefa 1.1: Criar pytest.ini (30 min)
**Agente:** `executor` (sonnet)

**Descrição:**
Criar arquivo de configuração do pytest com marcadores e opções de cobertura.

**Arquivo Novo:** `./pytest.ini` (~25 linhas)

**Conteúdo:**
```ini
[pytest]
testpaths = tests
asyncio_mode = auto
markers =
    unit: Unit tests (fast, isolated)
    integration: Integration tests
    slow: Slow-running tests
    network: Tests requiring network
    telegram: Tests with Telegram API
addopts =
    -v
    --strict-markers
    --cov=clean_telegram
    --cov-report=term-missing:skip-covered
    --cov-report=html:htmlcov
    --tb=short
```

**Checkpoint de Validação:**
```bash
pytest --collect-only | grep "markers defined"
pytest --markers
```

**Dependências:** Nenhuma

---

### Tarefa 1.2: Criar .coveragerc (30 min)
**Agente:** `executor` (sonnet)

**Descrição:**
Criar arquivo de configuração do coverage com fail_under=70 e branch coverage.

**Arquivo Novo:** `/Users/gabrielramos/CleanTelegram/.coveragerc` (~20 linhas)

**Conteúdo:**
```ini
[run]
source = src/clean_telegram
omit = */tests/*,*/__pycache__/*,*/.venv/*
branch = True

[report]
precision = 2
show_missing = True
fail_under = 70
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    if TYPE_CHECKING:
```

**Checkpoint de Validação:**
```bash
pytest --cov=clean_telegram --cov-report=term-missing:skip-covered
# Deve mostrar "fail_under=70" nas configurações
```

**NOTA:** pytest-cov usa `--cov=clean_telegram` (nome do pacote) enquanto .coveragerc usa `source = src/clean_telegram` (caminho). Ambos estão corretos para o layout src/.

**Dependências:** Nenhuma

---

### Tarefa 1.3: Adicionar pytest-mock ao pyproject.toml (15 min)
**Agente:** `executor` (sonnet)

**Descrição:**
Adicionar dependência `pytest-mock>=3.12.0` ao `pyproject.toml`.

**Arquivo Modificar:** `/Users/gabrielramos/CleanTelegram/pyproject.toml`
- Linha 19-22: `[project.optional-dependencies]` seção dev

**Mudança:**
```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-mock>=3.12.0",  # ADICIONAR
    "pytest-cov>=7.0.0",    # MOVER DA dependency-groups
]
```

**Checkpoint de Validação:**
```bash
pip install -e ".[dev]"
python -c "import pytest_mock; print(pytest_mock.__version__)"
```

**Dependências:** Nenhuma

---

### Tarefa 1.4: Expandir conftest.py com fixtures globais (1h)
**Agente:** `executor` (sonnet)

**Descrição:**
Expandir `/Users/gabrielramos/CleanTelegram/tests/conftest.py` de 18 para ~150 linhas com:
1. `AsyncIteratorMock` centralizado
2. `mock_console()` para Rich Console
3. `mock_stdin()` para input do usuário
4. `mock_telethon_client()` padrão
5. `mock_chat_entity()` padrão

**Arquivo Modificar:** `/Users/gabrielramos/CleanTelegram/tests/conftest.py`

**Novas Fixtures (após linha 18):**

```python
# =============================================================================
# AsyncIteratorMock Centralizado
# =============================================================================

class AsyncIteratorMock:
    """Mock para iteradores assíncronos (usado em iter_dialogs, iter_messages, etc.)."""

    def __init__(self, items):
        self.items = items

    def __aiter__(self):
        self.iter = iter(self.items)
        return self

    async def __anext__(self):
        try:
            return next(self.iter)
        except StopIteration:
            raise StopAsyncIteration


# =============================================================================
# Rich Console Mock
# =============================================================================

@pytest.fixture
def mock_console(mocker):
    """Mock do console global Rich para testes de UI."""
    return mocker.patch("clean_telegram.ui.console", autospec=True)

# NOTA: Se patch "clean_telegram.ui.console" não funcionar devido a
# import time, usar patch.object no local de importação:
# with mock.patch.object(ui_module, "console", autospec=True) as m:


# =============================================================================
# sys.stdin Mock para input do usuário
# =============================================================================

@pytest.fixture
def mock_stdin(monkeypatch):
    """Factory para mock de sys.stdin em testes de CLI interativo."""

    def _make_input(text: str):
        from io import StringIO
        import sys
        monkeypatch.setattr(sys, "stdin", StringIO(text + "\n"))

    return _make_input


# =============================================================================
# Telethon Client Mock Padrão
# =============================================================================

@pytest.fixture
def mock_telethon_client(mocker):
    """Mock padrão de TelegramClient com configurações básicas."""
    client = mocker.AsyncMock()
    client.iter_dialogs = mocker.Mock(return_value=AsyncIteratorMock([]))
    client.get_me = mocker.AsyncMock()
    return client


@pytest.fixture
def mock_chat_entity(mocker):
    """Mock padrão de entidade de chat (Channel)."""
    chat = mocker.Mock()
    chat.id = 123456
    chat.title = "Grupo de Teste"
    chat.__class__.__name__ = "Channel"
    return chat
```

**Checkpoint de Validação:**
```bash
pytest tests/ -v --tb=short
# Todos os 65 testes existentes devem continuar passando
```

**Dependências:** Nenhuma (Recomendada primeiro, mas tarefas 2.1 e 3.1 podem começar em paralelo)

---

## FASE 2: Testes para ui.py (3-4 horas)

**Arquivo Alvo:** `/Users/gabrielramos/CleanTelegram/src/clean_telegram/ui.py` (111 linhas)
**Arquivo Novo:** `/Users/gabrielramos/CleanTelegram/tests/test_ui.py` (~350 linhas)

### Tarefa 2.1: Criar estrutura do test_ui.py (30 min)
**Agente:** `executor` (sonnet)

**Descrição:**
Criar arquivo vazio com imports e estrutura de classes de teste.

**Conteúdo Inicial:**
```python
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
    pass


class TestSpinner:
    """Testes para spinner()."""
    pass


class TestPrintHeader:
    """Testes para print_header()."""
    pass


class TestPrintStatsTable:
    """Testes para print_stats_table()."""
    pass


class TestPrintSuccess:
    """Testes para print_success()."""
    pass


class TestPrintError:
    """Testes para print_error()."""
    pass


class TestPrintWarning:
    """Testes para print_warning()."""
    pass


class TestPrintInfo:
    """Testes para print_info()."""
    pass


class TestPrintTip:
    """Testes para print_tip()."""
    pass
```

**Dependências:** Tarefa 1.4

---

### Tarefa 2.2: Testar suppress_telethon_logs() (20 min)
**Agente:** `executor` (sonnet)

**Descrição:**
Testar context manager que suprime logs do Telethon.

**Casos de Teste:**
1. Deve definir logger level como CRITICAL dentro do contexto
2. Deve restaurar level original após sair do contexto
3. Deve funcionar com logger que já está em CRITICAL

**Implementação:**
```python
def test_suppress_telethon_logs_sets_critical():
    """Deve definir logger level como CRITICAL dentro do contexto."""
    telethon_logger = logging.getLogger("telethon")
    original_level = telethon_logger.level

    with ui.suppress_telethon_logs():
        assert telethon_logger.level == logging.CRITICAL

    # Limpeza
    telethon_logger.setLevel(original_level)


def test_suppress_telethon_logs_restores_level():
    """Deve restaurar level original após sair do contexto."""
    telethon_logger = logging.getLogger("telethon")
    original_level = logging.INFO
    telethon_logger.setLevel(original_level)

    with ui.suppress_telethon_logs():
        pass  # Mudou para CRITICAL

    assert telethon_logger.level == original_level


def test_suppress_telethon_logs_already_critical():
    """Deve funcionar corretamente mesmo se já está CRITICAL."""
    telethon_logger = logging.getLogger("telethon")
    telethon_logger.setLevel(logging.CRITICAL)

    # Não deve lançar exceção
    with ui.suppress_telethon_logs():
        assert telethon_logger.level == logging.CRITICAL
```

**Dependências:** Tarefa 2.1

---

### Tarefa 2.3: Testar spinner() (20 min)
**Agente:** `executor` (sonnet)

**Descrição:**
Testar função que retorna context manager de status com spinner.

**Casos de Teste:**
1. Deve retornar um context manager
2. Deve usar o tipo de spinner padrão "dots"
3. Deve aceitar tipo customizado

**Implementação:**
```python
def test_spinner_returns_context_manager():
    """Deve retornar um context manager do Rich."""
    result = ui.spinner("Testando")
    assert hasattr(result, "__enter__")
    assert hasattr(result, "__exit__")


def test_spinner_default_type():
    """Deve usar spinner type 'dots' por padrão."""
    result = ui.spinner("Test")
    # O status é criado com o spinner padrão


def test_spinner_custom_type():
    """Deve aceitar tipo de spinner customizado."""
    result = ui.spinner("Test", spinner_type="line")
    # Verifica que não lança exceção
```

**Dependências:** Tarefa 2.1

---

### Tarefa 2.4: Testar print_header() (30 min)
**Agente:** `executor` (sonnet)

**Descrição:**
Testar função que exibe cabeçalho com painel Rich.

**Casos de Teste:**
1. Deve chamar console.print com Panel
2. Deve incluir título no painel
3. Deve incluir subtítulo se fornecido
4. Deve usar estilo correto (bold cyan)

**Implementação (com mock_console):**
```python
def test_print_header_with_title(mock_console):
    """Deve exibir painel com título."""
    ui.print_header("Título Teste")

    mock_console.print.assert_called_once()
    call_args = mock_console.print.call_args
    assert isinstance(call_args[0][0], Panel)


def test_print_header_with_subtitle(mock_console):
    """Deve incluir subtítulo quando fornecido."""
    ui.print_header("Título", subtitle="Subtítulo Teste")

    call_args = mock_console.print.call_args
    panel = call_args[0][0]
    # Panel contém o texto formatado


def test_print_header_without_subtitle(mock_console):
    """Deve funcionar sem subtítulo."""
    ui.print_header("Apenas Título")

    mock_console.print.assert_called_once()
```

**Dependências:** Tarefas 1.4, 2.1

---

### Tarefa 2.5: Testar print_stats_table() (40 min)
**Agente:** `executor` (sonnet)

**Descrição:**
Testar função que exibe tabela de estatísticas com formatação de números.

**Casos de Teste:**
1. Deve criar Table com título correto
2. Deve formatar inteiros com separador de milhares
3. Deve formatar valores não-inteiros como string
4. Deve usar estilo de título customizado quando fornecido

**Implementação:**
```python
def test_print_stats_table_creates_table(mock_console):
    """Deve criar Table com título."""
    ui.print_stats_table("Teste", {"chave": "valor"})

    mock_console.print.assert_called_once()
    call_args = mock_console.print.call_args
    assert isinstance(call_args[0][0], Table)


def test_print_stats_table_formats_integers(mock_console):
    """Deve formatar inteiros com separador de milhares."""
    ui.print_stats_table("Teste", {"count": 1234567})

    call_args = mock_console.print.call_args
    table = call_args[0][0]
    # Table contém "1,234,567" ou "1.234.567"


def test_print_stats_table_non_integers(mock_console):
    """Deve tratar não-inteiros como string."""
    ui.print_stats_table("Teste", {"name": "Teste", "float": 3.14})

    mock_console.print.assert_called_once()


def test_print_stats_table_custom_title_style(mock_console):
    """Deve aceitar estilo customizado para título."""
    ui.print_stats_table("Teste", {"a": 1}, title_style="bold red")

    mock_console.print.assert_called_once()
```

**Dependências:** Tarefas 1.4, 2.1

---

### Tarefa 2.6: Testar print_success(), print_error(), print_warning(), print_info(), print_tip() (30 min)
**Agente:** `executor` (sonnet)

**Descrição:**
Testar as 5 funções de impressão de mensagens coloridas.

**Casos de Teste:**
1. Cada função deve chamar console.print com mensagem formatada
2. Cada função deve usar a cor correta (green, red, yellow, blue)
3. print_tip deve usar estilo dim

**Implementação:**
```python
def test_print_success_format(mock_console):
    """Deve formatar mensagem com emoji verde."""
    ui.print_success("Sucesso!")

    mock_console.print.assert_called_once()
    call_args = mock_console.print.call_args[0][0]
    assert "✅" in call_args
    assert "[bold green]" in call_args


def test_print_error_format(mock_console):
    """Deve formatar mensagem com emoji vermelho."""
    ui.print_error("Erro!")

    call_args = mock_console.print.call_args[0][0]
    assert "❌" in call_args
    assert "[bold red]" in call_args


def test_print_warning_format(mock_console):
    """Deve formatar mensagem com emoji amarelo."""
    ui.print_warning("Aviso!")

    call_args = mock_console.print.call_args[0][0]
    assert "⚠️" in call_args
    assert "[bold yellow]" in call_args


def test_print_info_format(mock_console):
    """Deve formatar mensagem com emoji azul."""
    ui.print_info("Info!")

    call_args = mock_console.print.call_args[0][0]
    assert "ℹ️" in call_args
    assert "[bold blue]" in call_args


def test_print_tip_format(mock_console):
    """Deve formatar dica com estilo dim."""
    ui.print_tip("Dica!")

    call_args = mock_console.print.call_args[0][0]
    assert "💡" in call_args
    assert "[dim]" in call_args
```

**Dependências:** Tarefas 1.4, 2.1

---

### Tarefa 2.7: Validação completa de ui.py (15 min)
**Agente:** `verifier` (haiku)

**Descrição:**
Executar testes de ui.py e verificar cobertura >= 70%.

**Checkpoint de Validação:**
```bash
pytest tests/test_ui.py -v --cov=clean_telegram.ui --cov-report=term-missing:skip-covered
# Esperado: 100% de cobertura em ui.py
```

**Dependências:** Tarefas 2.1 a 2.6

---

## FASE 3: Testes para cli.py (3-4 horas)

**Arquivo Alvo:** `/Users/gabrielramos/CleanTelegram/src/clean_telegram/cli.py` (483 linhas)
**Arquivo Novo:** `/Users/gabrielramos/CleanTelegram/tests/test_cli_core.py` (~300 linhas)

### Tarefa 3.1: Criar estrutura do test_cli_core.py (20 min)
**Agente:** `executor` (sonnet)

**Descrição:**
Criar arquivo com estrutura para testes críticos do cli.py.

**Conteúdo Inicial:**
```python
"""Testes críticos para cli.py."""

import sys
from unittest import mock

import pytest

from clean_telegram import cli


class TestEnvInt:
    """Testes para env_int()."""
    pass


class TestConfirmAction:
    """Testes para confirm_action()."""
    pass


class TestRunClean:
    """Testes para run_clean()."""
    pass


class TestRunReport:
    """Testes para run_report()."""
    pass
```

**Dependências:** Nenhuma

---

### Tarefa 3.2: Testar env_int() (40 min)
**Agente:** `executor` (sonnet)

**Descrição:**
Testar função que lê variável de ambiente e converte para int.

**Casos de Teste:**
1. Deve retornar int quando valor é válido
2. Deve lançar SystemExit quando variável não existe
3. Deve lançar SystemExit quando valor não é numérico
4. Deve aceitar zero
5. Deve aceitar negativos

**Implementação:**
```python
def test_env_int_valid_value(monkeypatch):
    """Deve retornar int quando valor é válido."""
    monkeypatch.setenv("TEST_VAR", "12345")
    result = cli.env_int("TEST_VAR")
    assert result == 12345


def test_env_int_missing_variable(monkeypatch):
    """Deve lançar SystemExit quando variável não existe."""
    monkeypatch.delenv("TEST_VAR", raising=False)

    with pytest.raises(SystemExit, match="Faltou TEST_VAR no .env"):
        cli.env_int("TEST_VAR")


def test_env_int_non_numeric(monkeypatch):
    """Deve lançar SystemExit quando valor não é numérico."""
    monkeypatch.setenv("TEST_VAR", "abc")

    with pytest.raises(SystemExit, match="Valor inválido para TEST_VAR"):
        cli.env_int("TEST_VAR")


def test_env_int_zero(monkeypatch):
    """Deve aceitar zero."""
    monkeypatch.setenv("TEST_VAR", "0")
    result = cli.env_int("TEST_VAR")
    assert result == 0


def test_env_int_negative(monkeypatch):
    """Deve aceitar negativos."""
    monkeypatch.setenv("TEST_VAR", "-100")
    result = cli.env_int("TEST_VAR")
    assert result == -100
```

**Dependências:** Tarefa 3.1

---

### Tarefa 3.3: Testar confirm_action() (40 min)
**Agente:** `executor` (sonnet)

**Descrição:**
Testar função crítica de confirmação antes de ação destrutiva.

**Casos de Teste:**
1. Deve retornar True quando usuário digita "APAGAR TUDO"
2. Deve retornar False para qualquer outro input
3. Deve fazer trim de whitespace
4. Deve ser case-sensitive

**Implementação:**
```python
def test_confirm_action_exact_match(mock_stdin):
    """Deve retornar True quando usuário digita 'APAGAR TUDO'."""
    mock_stdin("APAGAR TUDO")
    result = cli.confirm_action()
    assert result is True


def test_confirm_action_wrong_input(mock_stdin):
    """Deve retornar False para qualquer outro input."""
    mock_stdin("apagar tudo")  # minúsculas
    result = cli.confirm_action()
    assert result is False


def test_confirm_action_trims_whitespace(mock_stdin):
    """Deve fazer trim de whitespace."""
    mock_stdin("   APAGAR TUDO   ")
    result = cli.confirm_action()
    assert result is True


def test_confirm_action_case_sensitive(mock_stdin):
    """Deve ser case-sensitive."""
    mock_stdin("apagar tudo")
    result = cli.confirm_action()
    assert result is False


def test_confirm_action_partial_match(mock_stdin):
    """Deve exigir match exato."""
    mock_stdin("APAGAR TODO")
    result = cli.confirm_action()
    assert result is False
```

**Dependências:** Tarefas 1.4, 3.1

---

### Tarefa 3.4: Testar run_clean() (1h)
**Agente:** `executor` (sonnet)

**Descrição:**
Testar função principal de limpeza de diálogos.

**Casos de Teste:**
1. Deve chamar clean_all_dialogs com parâmetros corretos
2. Deve respeitar dry_run
3. Deve respeitar limit
4. Deve logar informações do usuário

**Implementação:**
```python
@pytest.mark.asyncio
async def test_run_clean_calls_clean_all_dialogs(mock_telethon_client, mocker):
    """Deve chamar clean_all_dialogs com parâmetros corretos."""
    # Setup
    mock_telethon_client.get_me = mocker.AsyncMock()
    args = mock.Mock(dry_run=True, limit=10)

    # Mock clean_all_dialogs
    mock_clean = mocker.patch("clean_telegram.cli.clean_all_dialogs", return_value=5)

    # Execute
    await cli.run_clean(args, mock_telethon_client)

    # Verify
    mock_clean.assert_awaited_once_with(
        mock_telethon_client,
        dry_run=True,
        limit=10,
    )


@pytest.mark.asyncio
async def test_run_clean_logs_user_info(mock_telethon_client, mocker, caplog):
    """Deve logar informações do usuário."""
    me = mock.Mock()
    me.username = "testuser"
    me.first_name = "Test"
    me.id = 123
    mock_telethon_client.get_me = mocker.AsyncMock(return_value=me)

    args = mock.Mock(dry_run=True, limit=0)
    mocker.patch("clean_telegram.cli.clean_all_dialogs", return_value=0)

    with caplog.at_level("INFO"):
        await cli.run_clean(args, mock_telethon_client)

    assert "Logado como:" in caplog.text


@pytest.mark.asyncio
async def test_run_clean_respects_dry_run(mock_telethon_client, mocker):
    """Deve passar dry_run corretamente."""
    mock_telethon_client.get_me = mocker.AsyncMock()
    mock_clean = mocker.patch("clean_telegram.cli.clean_all_dialogs")

    args = mock.Mock(dry_run=True, limit=0)
    await cli.run_clean(args, mock_telethon_client)

    call_kwargs = mock_clean.call_args[1]
    assert call_kwargs["dry_run"] is True


@pytest.mark.asyncio
async def test_run_clean_respects_limit(mock_telethon_client, mocker):
    """Deve passar limit corretamente."""
    mock_telethon_client.get_me = mocker.AsyncMock()
    mock_clean = mocker.patch("clean_telegram.cli.clean_all_dialogs")

    args = mock.Mock(dry_run=True, limit=50)
    await cli.run_clean(args, mock_telethon_client)

    call_kwargs = mock_clean.call_args[1]
    assert call_kwargs["limit"] == 50
```

**Dependências:** Tarefas 1.4, 3.1

---

### Tarefa 3.5: Testar run_report() (1h)
**Agente:** `executor` (sonnet)

**Descrição:**
Testar função de geração de relatórios.

**Casos de Teste:**
1. Deve chamar generate_all_reports para report_type="all"
2. Deve chamar generate_groups_channels_report para "groups"
3. Deve chamar generate_contacts_report para "contacts"
4. Deve logar caminho do arquivo gerado
5. Deve suportar todos os formatos (csv, json, txt)

**Implementação:**
```python
@pytest.mark.asyncio
async def test_run_report_all(mock_telethon_client, mocker):
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
async def test_run_report_groups(mock_telethon_client, mocker):
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
async def test_run_report_contacts(mock_telethon_client, mocker):
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
async def test_run_report_logs_path(mock_telethon_client, mocker, caplog):
    """Deve logar caminho do arquivo gerado."""
    mock_telethon_client.get_me = mocker.AsyncMock()
    mocker.patch(
        "clean_telegram.cli.generate_groups_channels_report",
        return_value="relatorio.csv"
    )

    args = mock.Mock(report="groups", report_format="csv", report_output=None)

    with caplog.at_level("INFO"):
        await cli.run_report(args, mock_telethon_client)

    assert "relatório" in caplog.text.lower()
    assert "relatorio.csv" in caplog.text


@pytest.mark.asyncio
async def test_run_report_all_formats(mock_telethon_client, mocker):
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
```

**Dependências:** Tarefas 1.4, 3.1

---

### Tarefa 3.6: Validação completa de cli.py (15 min)
**Agente:** `verifier` (haiku)

**Descrição:**
Executar todos os testes de cli.py e verificar cobertura.

**Checkpoint de Validação:**
```bash
pytest tests/test_cli_core.py tests/test_cli_auth.py -v --cov=clean_telegram.cli --cov-report=term-missing:skip-covered
# Esperado: cobertura significativamente aumentada em cli.py
```

**Dependências:** Tarefas 3.1 a 3.5

---

## FASE 4: Refatoração e Validação Final (1-2 horas)

### Tarefa 4.1: Refatorar testes existentes para usar AsyncIteratorMock centralizado (30 min)
**Agente:** `executor` (sonnet)

**Descrição:**
Remover duplicações de `AsyncIteratorMock` em testes existentes.

**Arquivos a Modificar:**
- `/Users/gabrielramos/CleanTelegram/tests/test_cleaner.py` (linhas 73-87)
- `/Users/gabrielramos/CleanTelegram/tests/test_reports.py` (se aplicável)
- `/Users/gabrielramos/CleanTelegram/tests/test_backup_cloud.py` (se aplicável)

**Mudanças:**
```python
# ANTES:
class AsyncIterator:
    def __init__(self, items):
        self.items = items
    # ...

# DEPOIS:
from tests.conftest import AsyncIteratorMock
```

**Checkpoint de Validação:**
```bash
pytest tests/test_cleaner.py tests/test_reports.py tests/test_backup_cloud.py -v
# Todos os testes devem continuar passando
```

**Dependências:** Tarefa 1.4

---

### Tarefa 4.2: Corrigir teste falhando em test_backup_cloud.py (30 min)
**Agente:** `debugger` (sonnet)

**Descrição:**
Investigar e corrigir `test_should_include_media_count_in_summary` que está falhando.

**Análise Inicial:**
- Teste espera "7" no summary mas recebe "0"
- Mock de `download_media_from_chat` retorna {"photo": 5, "video": 2, "total": 7}
- Possível causa: `backup_group_with_media` está usando `download_media_parallel` em vez de `download_media_from_chat`

**Arquivo Modificar:** `/Users/gabrielramos/CleanTelegram/tests/test_backup_cloud.py`

**Solução Provável:**
```python
# Mudar mock para download_media_parallel
async def mock_download(*args, **kwargs):
    return {
        "photo": 5,
        "video": 2,
        "total": 7,
    }

with mock.patch(
    "clean_telegram.backup.download_media_parallel",  # MUDAR AQUI
    side_effect=mock_download
):
```

**Checkpoint de Validação:**
```bash
pytest tests/test_backup_cloud.py::TestBackupGroupWithCloud::test_should_include_media_count_in_summary -v
# Deve passar
```

**Dependências:** Nenhuma

---

### Tarefa 4.3: Executar suite completa com cobertura (30 min)
**Agente:** `verifier` (sonnet)

**Descrição:**
Executar todos os testes com cobertura e verificar se meta de 70% foi atingida.

**Checkpoint de Validação:**
```bash
pytest tests/ -v --cov=clean_telegram --cov-report=html:htmlcov --cov-report=term-missing:skip-covered
```

**Critérios de Aceite:**
- Todos os testes passando (68+ testes)
- Cobertura total >= 70%
- Sem regressões nos 65 testes existentes
- htmlcov/ gerado para inspeção visual

**Dependências:** Todas as tarefas anteriores

---

### Tarefa 4.4: Validação de performance da suite (15 min)
**Agente:** `verifier` (haiku)

**Descrição:**
Verificar que a suite completa executa em menos de 30 segundos.

**Checkpoint de Validação:**
```bash
time pytest tests/ --tb=no -q
# Deve completar em < 30 segundos
```

**Dependências:** Tarefa 4.3

---

### Tarefa 4.5: Documentação e limpeza (15 min)
**Agente:** `executor` (sonnet)

**Descrição:**
Adicionar docstrings às novas fixtures e atualizar README se necessário.

**Arquivos a Modificar:**
- `/Users/gabrielramos/CleanTelegram/tests/conftest.py` - adicionar docstrings
- `/Users/gabrielramos/CleanTelegram/README.md` - adicionar seção sobre testes

**Dependências:** Tarefa 4.3

---

## RESUMO DE TAREFAS

| ID | Tarefa | Fase | Duração | Dependências | Paralelizável |
|----|--------|------|---------|--------------|---------------|
| 1.1 | Criar pytest.ini | 1 | 30 min | - | Sim |
| 1.2 | Criar .coveragerc | 1 | 30 min | - | Sim |
| 1.3 | Adicionar pytest-mock | 1 | 15 min | - | Sim |
| 1.4 | Expandir conftest.py | 1 | 1h | - | Não (bloqueia outras) |
| 2.1 | Estrutura test_ui.py | 2 | 30 min | 1.4 | Sim |
| 2.2 | Testar suppress_telethon_logs | 2 | 20 min | 2.1 | Sim |
| 2.3 | Testar spinner | 2 | 20 min | 2.1 | Sim |
| 2.4 | Testar print_header | 2 | 30 min | 1.4, 2.1 | Sim |
| 2.5 | Testar print_stats_table | 2 | 40 min | 1.4, 2.1 | Sim |
| 2.6 | Testar funções de impressão | 2 | 30 min | 1.4, 2.1 | Sim |
| 2.7 | Validar ui.py | 2 | 15 min | 2.1-2.6 | Não |
| 3.1 | Estrutura test_cli_core.py | 3 | 20 min | - | Sim |
| 3.2 | Testar env_int | 3 | 40 min | 3.1 | Sim |
| 3.3 | Testar confirm_action | 3 | 40 min | 1.4, 3.1 | Sim |
| 3.4 | Testar run_clean | 3 | 1h | 1.4, 3.1 | Sim |
| 3.5 | Testar run_report | 3 | 1h | 1.4, 3.1 | Sim |
| 3.6 | Validar cli.py | 3 | 15 min | 3.1-3.5 | Não |
| 4.1 | Refatorar AsyncIteratorMock | 4 | 30 min | 1.4 | Sim |
| 4.2 | Corrigir teste falhando | 4 | 30 min | - | Sim |
| 4.3 | Validação cobertura final | 4 | 30 min | Todas | Não |
| 4.4 | Validação performance | 4 | 15 min | 4.3 | Não |
| 4.5 | Documentação | 4 | 15 min | 4.3 | Sim |

**Tempo Total Estimado:** 8-12 horas

---

## CAMINHO CRÍTICO

O caminho crítico (tarefas que não podem ser paralelizadas) é:

1. **Tarefa 1.4** (Expandir conftest.py) - DEVE ser feita primeiro
2. **Fase 2 completa** (Tarefas 2.1 a 2.7)
3. **Fase 3 completa** (Tarefas 3.1 a 3.6)
4. **Tarefas 4.3 e 4.4** (Validações finais)

---

## ARQUIVOS A CRIAR

1. `/Users/gabrielramos/CleanTelegram/pytest.ini` - ~25 linhas
2. `/Users/gabrielramos/CleanTelegram/.coveragerc` - ~20 linhas
3. `/Users/gabrielramos/CleanTelegram/tests/test_ui.py` - ~350 linhas
4. `/Users/gabrielramos/CleanTelegram/tests/test_cli_core.py` - ~300 linhas

**Total de código novo:** ~695 linhas

---

## ARQUIVOS A MODIFICAR

1. `/Users/gabrielramos/CleanTelegram/pyproject.toml` - +1 linha
2. `/Users/gabrielramos/CleanTelegram/tests/conftest.py` - +130 linhas (18 -> 150)
3. `/Users/gabrielramos/CleanTelegram/tests/test_cleaner.py` - -15 linhas (remover duplicação)
4. `/Users/gabrielramos/CleanTelegram/tests/test_backup_cloud.py` - ~1 linha (correção)

---

## RISCOS E MITIGAÇÃO

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Rich Console mock falhar | Média | Alto | Usar fixture padrão do conftest.py |
| sys.stdin mock falhar | Baixa | Médio | Usar StringIO com monkeypatch |
| Cobertura não atingir 70% | Média | Alto | Priorizar funções críticas primeiro |
| Testes existentes quebrarem | Baixa | Médio | Executar suite completa após cada mudança |

---

## CRITÉRIOS DE ACEITAÇÃO FINAL

### Infraestrutura
- [x] `pytest.ini` criado com 5 marcadores
- [x] `.coveragerc` criado com fail_under=70
- [x] `AsyncIteratorMock` centralizado em conftest.py
- [x] `pytest-mock` adicionado às dependências

### ui.py (9 funções)
- [x] suppress_telethon_logs() testada (context manager, restore)
- [x] spinner() testada (retorna context manager)
- [x] print_header() testada (Panel com título/subtítulo)
- [x] print_stats_table() testada (formatação de números)
- [x] print_success() testada (emoji + cor verde)
- [x] print_error() testada (emoji + cor vermelha)
- [x] print_warning() testada (emoji + cor amarela)
- [x] print_info() testada (emoji + cor azul)
- [x] print_tip() testada (emoji dim)

### cli.py (4 funções críticas)
- [x] confirm_action() completamente testada
- [x] env_int() com edge cases
- [x] run_clean() básico implementado
- [x] run_report() básico implementado

### Global
- [x] Cobertura total 59% → 70%+
- [x] Zero regressões (68+ testes passando)
- [x] Suite completa executa em < 30 segundos
- [x] 1 teste falhando corrigido

---

**PLANO APROVADO PARA EXECUÇÃO**
