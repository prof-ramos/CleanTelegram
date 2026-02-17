# Plano de Melhoria de Cobertura de Testes - Fase 1
**Projeto:** CleanTelegram
**Data:** 2025-02-13
**Timeline:** 1-2 semanas
**Objetivo:** Aumentar cobertura de 59% para 70%+ focando em componentes críticos de segurança

---

## 📊 Estado Atual

| Métrica | Valor | Status |
|---------|-------|--------|
| Cobertura Atual | ~59% | ⚠️ Abaixo do ideal |
| Componentes Críticos Sem Testes | ui.py (0%), confirm_action() | 🔴 Urgente |
| Testes Totais | 28 | Baixo |
| Módulos Fonte | 8 | - |

---

## 🎯 Fase 1: Foco em Componentes Críticos

**Escopo:** Infraestrutura de testes + Componentes de segurança críticos
**Deferido para Fase 2:** Testes de integração com Telegram real (20h+ de trabalho)

---

## 📋 Tarefas Detalhadas

### 1. Configuração de Infraestrutura (2 horas)

#### 1.1 Criar pytest.ini (30 min)
**Arquivo:** `pytest.ini` na raiz do projeto

```ini
[pytest]
testpaths = tests
asyncio_mode = auto
python_files = test_*.py
python_classes = Test*
python_functions = test_*
markers =
    unit: Fast unit tests
    integration: Integration tests
    slow: Slow-running tests
    telegram: Tests requiring Telegram API
    security: Security-critical tests

# Coverage settings via pytest-cov
addopts =
    --cov=src/clean_telegram
    --cov-report=term-missing
    --cov-report=html
    --cov-report=json
    --strict-markers
    -v
```

**Aceitação:**
- [ ] `pytest --markers` mostra todos os marcadores definidos
- [ ] `pytest` executa todos os testes sem erros de configuração

#### 1.2 Criar .coveragerc (15 min)
**Arquivo:** `.coveragerc` na raiz do projeto

```ini
[run]
source = src/clean_telegram
omit =
    */__init__.py
    */__main__.py
    */conftest.py
branch = True

[report]
precision = 2
show_missing = True
skip_covered = False
fail_under = 70

[html]
directory = htmlcov

[json]
output = coverage.json
```

**Aceitação:**
- [ ] `coverage report` mostra relatório com 70% como mínimo
- [ ] Arquivo HTML gerado em `htmlcov/`

#### 1.3 Extrair AsyncIteratorMock para conftest.py (1h)
**Arquivo:** `tests/conftest.py`

**Problema:** `AsyncIteratorMock` duplicado em 3 arquivos de teste

**Solução:** Centralizar no conftest.py:

```python
from typing import Any, AsyncIterator, Generator
from unittest.mock import AsyncMock
import pytest

class AsyncIteratorMock:
    """Mock para async generators que preserva o padrão AAA."""

    def __init__(self, items: list[Any]) -> None:
        self.items = items
        self.index = 0

    def __aiter__(self) -> AsyncIterator[Any]:
        return self

    async def __anext__(self) -> Any:
        if self.index >= len(self.items):
            raise StopAsyncIteration
        item = self.items[self.index]
        self.index += 1
        return item

@pytest.fixture
def async_iterator_mock():
    """Factory para criar mocks de iteradores assíncronos."""
    return AsyncIteratorMock
```

**Arquivos a atualizar:**
- `tests/test_cli_auth.py`
- `tests/test_backup_cloud.py`
- `tests/test_cleaner.py`

**Aceitação:**
- [ ] AsyncIteratorMock centralizado em conftest.py
- [ ] 3 arquivos de teste atualizados para usar fixture
- [ ] Todos os testes continuam passando

---

### 2. Testar ui.py Completamente (4 horas)

**Status Atual:** 0% cobertura, 9 funções sem testes
**Prioridade:** URGENTE (funções de UI/UX afetam experiência do usuário)

#### 2.1 Criar arquivo de teste
**Arquivo:** `tests/test_ui.py` (NOVO)

#### 2.2 Testes por função

**Função:** `print_success(message)`
```python
def test_print_success_outputs_to_stdout(caplog):
    """Deve imprimir mensagem com emoji de check verde."""
    from clean_telegram.ui import print_success
    print_success("Operação concluída")
    assert "✓" in caplog.text or "Operação concluída" in caplog.text
```

**Função:** `print_error(message)`
```python
def test_print_error_outputs_to_stderr(caplog):
    """Deve imprimir mensagem com emoji de X vermelho."""
    from clean_telegram.ui import print_error
    print_error("Erro fatal")
    assert "✗" in caplog.text or "Erro fatal" in caplog.text
```

**Função:** `print_warning(message)`
```python
def test_print_warning_outputs_to_stdout(caplog):
    """Deve imprimir mensagem com emoji de alerta."""
    from clean_telegram.ui import print_warning
    print_warning("Atenção")
    assert "⚠" in caplog.text
```

**Função:** `print_info(message)`
```python
def test_print_info_outputs_to_stdout(caplog):
    """Deve imprimir mensagem informativa."""
    from clean_telegram.ui import print_info
    print_info("Processando...")
    assert "ℹ" in caplog.text or "Processando" in caplog.text
```

**Função:** `print_stats_table(stats, title)`
```python
def test_print_stats_table_displays_table(capsys):
    """Deve imprimir tabela formatada com estatísticas."""
    from clean_telegram.ui import print_stats_table
    stats = {
        "Mensagens": 1500,
        "Participantes": 45,
        "Mídia": 320
    }
    print_stats_table(stats, "Backup Completo")
    captured = capsys.readouterr()
    assert "Backup Completo" in captured.out
    assert "1500" in captured.out

def test_print_stats_table_handles_large_numbers(capsys):
    """Deve formatar números grandes corretamente."""
    from clean_telegram.ui import print_stats_table
    stats = {"Mensagens": 1500000}
    print_stats_table(stats, "Grandes Números")
    captured = capsys.readouterr()
    # Pode formatar como 1.5M ou 1500000
    assert "1500" in captured.out or "1.5" in captured.out
```

**Função:** `create_spinner(text)`
```python
def test_spinner_context_manager():
    """Deve criar e gerenciar spinner como context manager."""
    from clean_telegram.ui import create_spinner
    with create_spinner("Carregando...") as spinner:
        assert spinner is not None
        # Simula trabalho
        import time
        time.sleep(0.01)
    # Context manager deve limpar o spinner

def test_spinner_with_success():
    """Deve permitir marcar spinner como sucesso."""
    from clean_telegram.ui import create_spinner
    with create_spinner("Processando") as spinner:
        spinner.succeed()
```

**Função:** `confirm(message)`
```python
def test_confirm_user_accepts(monkeypatch):
    """Deve retornar True quando usuário confirma."""
    from clean_telegram.ui import confirm
    monkeypatch.setattr('builtins.input', lambda _: 'y')
    result = confirm("Continuar?")
    assert result is True

def test_confirm_user_declines(monkeypatch):
    """Deve retornar False quando usuário recusa."""
    from clean_telegram.ui import confirm
    monkeypatch.setattr('builtins.input', lambda _: 'n')
    result = confirm("Continuar?")
    assert result is False

def test_confirm_user_uses_default(monkeypatch):
    """Deve usar padrão quando usuário aperta Enter."""
    from clean_telegram.ui import confirm
    monkeypatch.setattr('builtins.input', lambda _: '')
    result = confirm("Continuar?", default=True)
    assert result is True
```

**Função:** `suppress_telethon_logs()`
```python
def test_suppress_telethon_logs_restores_level():
    """Deve restaurar nível de log após contexto."""
    import logging
    from clean_telegram.ui import suppress_telethon_logs

    original_level = logging.getLogger("telethon").level
    with suppress_telethon_logs():
        # Nível deve estar elevado
        pass
    # Nível deve ser restaurado
    final_level = logging.getLogger("telethon").level
    assert final_level == original_level
```

**Função:** `clear_screen()`
```python
def test_clear_screen_calls_system(monkeypatch):
    """Deve chamar comando de limpar tela."""
    from clean_telegram.ui import clear_screen
    mock_system = Mock()
    monkeypatch.setattr('os.system', mock_system)
    clear_screen()
    mock_system.assert_called_once()
```

**Aceitação:**
- [ ] Todas as 9 funções testadas
- [ ] Cobertura de ui.py ≥ 80%
- [ ] Todos os testes passando

---

### 3. Testar cli.py - Funções Críticas (2 horas)

**Status Atual:** ~30% cobertura
**Prioridade:** ALTA (ponto de entrada da CLI)

#### 3.1 Criar arquivo de teste
**Arquivo:** `tests/test_cli_critical.py` (NOVO)

#### 3.2 Testar confirm_action()

**Problema:** Função que impede ações acidentais - CRÍTICA para segurança

```python
import pytest
from clean_telegram.cli import confirm_action

def test_confirm_action_accepts_only_exact_string(monkeypatch, capsys):
    """Deve aceitar APENAS 'APAGAR TUDO' como confirmação."""
    # Input correto
    monkeypatch.setattr('sys.stdin.readline', lambda: 'APAGAR TUDO\n')
    assert confirm_action() is True

def test_confirm_action_rejects_partial_match(monkeypatch, capsys):
    """Deve rejeitar variações parciais."""
    test_cases = ['apagar tudo', 'APAGAR', 'TUDO', 'Apagar Tudo', '']
    for input_text in test_cases:
        monkeypatch.setattr('sys.stdin.readline', lambda: input_text + '\n')
        assert confirm_action() is False, f"Deve rejeitar: {input_text}"

def test_confirm_action_handles_empty_input(monkeypatch, capsys):
    """Deve rejeitar input vazio."""
    monkeypatch.setattr('sys.stdin.readline', lambda: '\n')
    assert confirm_action() is False

def test_confirm_action_strips_whitespace(monkeypatch, capsys):
    """Deve remover espaços em branco extras."""
    monkeypatch.setattr('sys.stdin.readline', lambda: '  APAGAR TUDO  \n')
    assert confirm_action() is True
```

#### 3.3 Testar env_int()

```python
import pytest
from clean_telegram.cli import env_int

def test_env_int_with_valid_value(monkeypatch):
    """Deve converter string válida para int."""
    monkeypatch.setenv('TEST_VAR', '12345')
    result = env_int('TEST_VAR')
    assert result == 12345

def test_env_int_with_missing_value(monkeypatch):
    """Deve raise SystemExit se variável não existe."""
    monkeypatch.delenv('TEST_VAR', raising=False)
    with pytest.raises(SystemExit):
        env_int('TEST_VAR')

def test_env_int_with_invalid_value(monkeypatch):
    """Deve raise SystemExit se valor não é int."""
    monkeypatch.setenv('TEST_VAR', 'not_a_number')
    with pytest.raises(SystemExit) as exc_info:
        env_int('TEST_VAR')
    assert "não é um inteiro válido" in str(exc_info.value)
```

#### 3.4 Testar run_clean()

```python
import pytest
from unittest.mock import AsyncMock, Mock
from clean_telegram.cli import run_clean

@pytest.mark.asyncio
async def test_run_clean_logs_user_info(mock_client):
    """Deve logar informações do usuário antes de limpar."""
    mock_me = Mock()
    mock_me.username = "testuser"
    mock_me.first_name = "Test"
    mock_me.id = 12345
    mock_client.get_me = AsyncMock(return_value=mock_me)
    mock_client.clean_all_dialogs = AsyncMock(return_value=5)

    args = Mock(dry_run=True, limit=0)
    await run_clean(args, mock_client)

    mock_client.get_me.assert_called_once()
    mock_client.clean_all_dialogs.assert_called_once_with(dry_run=True, limit=0)

@pytest.mark.asyncio
async def test_run_clean_handles_errors_gracefully(mock_client):
    """Deve lidar com erros sem crashar."""
    mock_client.get_me = AsyncMock(side_effect=Exception("API Error"))
    args = Mock(dry_run=True, limit=0)

    # Não deve raise exceção
    await run_clean(args, mock_client)
```

#### 3.5 Testar run_report()

```python
import pytest
from unittest.mock import AsyncMock, Mock
from clean_telegram.cli import run_report

@pytest.mark.asyncio
async def test_run_report_generates_groups_report(mock_client):
    """Deve gerar relatório de grupos quando solicitado."""
    mock_me = Mock(username="testuser", first_name="Test", id=12345)
    mock_client.get_me = AsyncMock(return_value=mock_me)

    args = Mock(report="groups", report_format="csv", report_output=None)

    await run_report(args, mock_client)
    mock_client.get_me.assert_called_once()

@pytest.mark.asyncio
async def test_run_report_generates_all_reports(mock_client):
    """Deve gerar todos os relatórios quando report='all'."""
    mock_me = Mock(username="testuser", first_name="Test", id=12345)
    mock_client.get_me = AsyncMock(return_value=mock_me)

    args = Mock(report="all", report_format="json", report_output=None)

    await run_report(args, mock_client)
    mock_client.get_me.assert_called_once()
```

**Aceitação:**
- [ ] confirm_action() completamente testada
- [ ] env_int() testada
- [ ] run_clean() e run_report() testadas
- [ ] Cobertura de cli.py ≥ 50%

---

## 📊 Cronograma Semanal

### Semana 1 (8-10 horas)

| Dia | Tarefas | Horas | Entregáveis |
|-----|---------|-------|-------------|
| **Seg** | Infraestrutura (pytest.ini, .coveragerc, conftest.py) | 2h | Config base funcionando |
| **Ter** | ui.py - Parte 1 (funções de print simples) | 2h | 4 funções testadas |
| **Qua** | ui.py - Parte 2 (spinner, confirm, suppress_logs) | 2h | 5 funções testadas |
| **Qui** | cli.py - confirm_action() e env_int() | 1.5h | Funções críticas testadas |
| **Sex** | cli.py - run_clean() e run_report() | 1.5h | CLI básico coberto |

### Semana 2 (Buffer e Refinamento)

| Dia | Tarefas | Horas | Entregáveis |
|-----|---------|-------|-------------|
| **Seg** | Executar testes completos, verificar cobertura | 1h | Relatório de cobertura |
| **Ter** | Ajustar testes falhando, edge cases | 2h | Todos testes passando |
| **Qua** | Documentar testes em CLAUDE.md | 1h | Docs atualizados |
| **Qui** | Buffer para imprevistos | 2h | - |
| **Sex** | Validação final + commit | 1h | Fase 1 completa |

---

## ✅ Critérios de Aceitação da Fase 1

### Mínimo (MVP)
- [ ] pytest.ini configurado com marcadores
- [ ] .coveragerc configurado com fail_under=70
- [ ] AsyncIteratorMock extraído para conftest.py
- [ ] ui.py testado (cobertura ≥ 70%)
- [ ] confirm_action() completamente testada
- [ ] env_int() testada
- [ ] Cobertura geral ≥ 65%

### Ideal (Stretch Goals)
- [ ] run_clean() e run_report() testadas
- [ ] Cobertura geral ≥ 70%
- [ ] Todos os testes marcados adequadamente
- [ ] CI/CD local funcionando (pytest + coverage)

---

## 🚀 Como Executar os Testes

```bash
# Todos os testes
pytest

# Apenas testes unitários rápidos
pytest -m unit

# Apenas testes de segurança
pytest -m security

# Com cobertura
pytest --cov=src/clean_telegram --cov-report=html

# Apenas ui.py
pytest tests/test_ui.py -v

# Ver cobertura específica
pytest --cov=src/clean_telegram/ui --cov-report=term-missing
```

---

## 📝 Deferido para Fase 2

- Testes de integração com Telegram real (~20h)
- interactive.py fluxos completos (~8h)
- backup.py download_media_from_chat (~4h)
- Performance e load testing (~4h)
- CI/CD automatizado (GitHub Actions) (~4h)

---

## 🔗 Arquivos a Criar/Modificar

### Novos Arquivos
1. `pytest.ini` - Configuração do pytest
2. `.coveragerc` - Configuração do coverage
3. `tests/test_ui.py` - Testes do módulo UI (NOVO)
4. `tests/test_cli_critical.py` - Testes críticos do CLI (NOVO)

### Arquivos a Modificar
1. `tests/conftest.py` - Adicionar AsyncIteratorMock
2. `tests/test_cli_auth.py` - Usar AsyncIteratorMock do conftest
3. `tests/test_backup_cloud.py` - Usar AsyncIteratorMock do conftest
4. `tests/test_cleaner.py` - Usar AsyncIteratorMock do conftest
5. `CLAUDE.md` - Atualizar com comandos de teste

---

## ⚠️ Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Testes de UI dependem de Rich | Média | Baixo | Mock de console output |
| confirm_action() requer stdin | Alta | Baixo | Mock de sys.stdin.readline |
| Cobertura não atingir 70% | Média | Médio | Priorizar componentes críticos |
| Duplicação de código em testes | Baixa | Baixo | Fix já planejado (conftest) |

---

**Próximo Passo:** Após aprovação, iniciar com Semana 1 - Dia 1 (Infraestrutura)
