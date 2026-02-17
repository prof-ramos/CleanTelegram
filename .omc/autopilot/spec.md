# ESPECIFICAÇÃO - Fase 1: Melhoria de Testes CleanTelegram

**Data:** 2025-02-13
**Timeline:** 1-2 semanas
**Cobertura Atual:** 59% → **Meta:** 70%+

---

## 1. REQUISITOS FUNCIONAIS

### 1.1 Infraestrutura de Testes (2 horas)

| Arquivo | Conteúdo |
|---------|----------|
| `pytest.ini` | Marcadores: unit, integration, slow, network, telegram |
| `.coveragerc` | fail_under=70, branch coverage, HTML/JSON reports |
| `tests/conftest.py` | AsyncIteratorMock centralizado, fixtures Rich Console |

### 1.2 ui.py - Testar 9 Funções (0% → 70%+)

| # | Função | Linhas | Casos de Teste |
|---|--------|--------|----------------|
| 1 | `suppress_telethon_logs()` | 20-31 | Context manager, restore level |
| 2 | `spinner()` | 34-44 | Retorna status context manager |
| 3 | `print_header()` | 47-57 | Panel com título/subtítulo |
| 4 | `print_stats_table()` | 60-85 | Formatação de números, tabela Rich |
| 5 | `print_success()` | 88-90 | Emoji + cor verde |
| 6 | `print_error()` | 93-95 | Emoji + cor vermelha |
| 7 | `print_warning()` | 98-100 | Emoji + cor amarela |
| 8 | `print_info()` | 103-105 | Emoji + cor azul |
| 9 | `print_tip()` | 108-110 | Emoji dim |

### 1.3 cli.py - Funções Críticas

| Função | Casos de Teste | Prioridade |
|--------|----------------|------------|
| `confirm_action()` | "APAGAR TUDO"=True, outro=False, trim whitespace | URGENTE |
| `env_int()` | válido, vazio, não-numérico, negativo, zero | URGENTE |
| `run_clean()` | Mock client, dry_run, limit | ALTA |
| `run_report()` | groups, contacts, all formats | ALTA |

---

## 2. REQUISITOS NÃO-FUNCIONAIS

| Categoria | Especificação |
|-----------|---------------|
| **Performance** | Suite completa < 30 segundos |
| **Segurança** | confirm_action() requer match exato |
| **Manutenibilidade** | DRY - AsyncIteratorMock centralizado |
| **Compatibilidade** | Python 3.10+, pytest 8.0+ |

---

## 3. STACK TECNOLÓGICO

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",           # Já existe
    "pytest-asyncio>=0.23.0",  # Já existe
    "pytest-cov>=7.0.0",       # Já existe
    "pytest-mock>=3.12.0",     # NOVO - mocker fixture
]
```

---

## 4. ESTRATÉGIA DE MOCK

### 4.1 Rich Console Global
```python
from unittest.mock import patch
import pytest

@pytest.fixture
def mock_console():
    with patch("clean_telegram.ui.console") as m:
        yield m
```

### 4.2 sys.stdin para confirm_action()
```python
from io import StringIO
import sys
import pytest

@pytest.fixture
def mock_stdin(monkeypatch):
    def _make_input(text: str):
        monkeypatch.setattr(sys, "stdin", StringIO(text + "\n"))
    return _make_input
```

---

## 5. ARQUITETURA DE TESTES

```
tests/
├── conftest.py                      # EXPANDIR (18 → 150 linhas)
│   ├── AsyncIteratorMock            # Centralizado
│   ├── mock_console()               # Rich fixture
│   ├── mock_stdin()                 # I/O fixture
│   ├── mock_telethon_client()       # Client padrão
│   └── mock_chat_entity()           # Chat padrão
│
├── test_ui.py                       # NOVO - ui.py completo
├── test_cli_core.py                 # NOVO - cli.py crítico
├── test_cli_auth.py                 # ✓ Existe
├── test_cleaner.py                  # ✓ Existe
├── test_backup_cloud.py             # ✓ Existe
├── test_interactive_backup.py       # ✓ Existe
├── test_performance.py              # ✓ Existe
└── test_reports.py                  # ✓ Existe
```

---

## 6. ARQUIVOS DE CONFIGURAÇÃO

### pytest.ini
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

### .coveragerc
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

---

## 7. CRITÉRIOS DE ACEITAÇÃO

### Infraestrutura
- [ ] `pytest.ini` criado com 5 marcadores
- [ ] `.coveragerc` criado com fail_under=70
- [ ] `AsyncIteratorMock` em conftest.py
- [ ] 3 arquivos atualizados para usar fixture

### ui.py
- [ ] Todas 9 funções testadas
- [ ] Cobertura ≥ 70%
- [ ] Mock do Rich Console funcionando

### cli.py
- [ ] confirm_action() completamente testada
- [ ] env_int() com edge cases
- [ ] run_clean() e run_report() básicos

### Global
- [ ] Cobertura total 59% → 70%+
- [ ] Zero regressões (66 testes atuais passando)

---

## 8. OUT OF SCOPE

- ❌ Testes de integração com Telegram real (Fase 2)
- ❌ interactive.py fluxos completos (Fase 2)
- ❌ backup.py download_media (Fase 2)
- ❌ CI/CD automatizado (Fase 6)

---

## 9. RISCOS E MITIGAÇÃO

| Risco | Probabilidade | Mitigação |
|-------|---------------|-----------|
| Rich Console mock frágil | Média | Usar patch padrão + fixture |
| sys.stdin mock falhar | Baixa | StringIO + monkeypatch |
| Cobertura não atingir 70% | Média | Focar em críticos primeiro |

---

**ESPECIFICAÇÃO APROVADA PARA EXECUÇÃO**
