# CLAUDE.md

Este arquivo fornece orientação para o Claude Code (claude.ai/code) ao trabalhar com código neste repositório.

## Project Overview

CleanTelegram é um projeto Python que automatiza a limpeza de contas Telegram usando a biblioteca Telethon. O projeto segue práticas modernas de desenvolvimento Python com estrutura baseada em `src/` e ferramentas de qualidade configuradas.

## Development Commands

### Environment Management (UV)
Recomendamos usar **UV** como gerenciador de pacotes para este projeto:

```bash
# Instalar UV (se ainda não tiver)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Criar ambiente virtual com UV
uv venv

# Ativar ambiente
source .venv/bin/activate  # Linux/Mac
# ou
.venv\Scripts\activate     # Windows

# Instalar dependências
uv pip install -e ".[dev]"

# Ou sem UV:
pip install -e ".[dev]"
```

### Running the Application

```bash
# Executar com módulo Python
python -m clean_telegram --help

# Dry-run (testar sem alterações)
python -m clean_telegram --dry-run

# Executar com limitação de diálogos
python -m clean_telegram --limit 10

# Execução completa (requer confirmação)
python -m clean_telegram

# Execução sem confirmação
python -m clean_telegram --yes
```

### Testing Commands

```bash
# pytest - Run all tests
pytest

# Run with coverage
pytest --cov=src/clean_telegram --cov-report=html

# Run specific test file
pytest tests/test_client.py

# Run with verbose output
pytest -v

# Run tests matching pattern
pytest -k "test_delete"
```

### Code Quality Commands

```bash
# Format code with Black
black src/ tests/

# Check formatting without changes
black --check src/ tests/

# Sort imports
isort src/ tests/

# Check import sorting
isort --check-only src/ tests/

# Run linting with Flake8
flake8 src/ tests/

# Type checking with MyPy
mypy src/

# Run all quality checks at once
black --check src/ tests/ && isort --check-only src/ tests/ && flake8 src/ tests/ && mypy src/
```

## Technology Stack

### Core Technologies
- **Python 3.10+** - Linguagem primária
- **Telethon** - Biblioteca para interagir com Telegram MTProto API
- **python-dotenv** - Gerenciamento de variáveis de ambiente

### Development Tools
- **UV** - Gerenciador de pacotes (recomendado)
- **pytest** - Framework de testes
- **pytest-asyncio** - Suporte para testes assíncronos
- **pytest-cov** - Relatório de cobertura de testes

### Code Quality Tools
- **Black** - Formatador de código
- **isort** - Ordenador de imports
- **Flake8** - Linter (guia de estilo PEP 8)
- **MyPy** - Verificador de tipos estáticos

## Project Structure

```
CleanTelegram/
├── src/
│   └── clean_telegram/
│       ├── __init__.py      # Pacote principal com exports
│       ├── __main__.py      # Entry-point do CLI
│       ├── client.py        # Funções de interação com Telegram
│       └── utils.py         # Funções utilitárias
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Configuração pytest
│   ├── test_client.py       # Testes do módulo client
│   └── test_utils.py        # Testes do módulo utils
├── .env.example             # Exemplo de variáveis de ambiente
├── .flake8                  # Configuração do Flake8
├── pyproject.toml           # Configuração do projeto (moderno)
├── requirements.txt         # Dependências de produção
├── requirements-dev.txt     # Dependências de desenvolvimento
├── README.md                # Documentação do projeto
└── CLAUDE.md                # Este arquivo
```

## Naming Conventions
- **Files/Modules**: `snake_case` (ex: `client.py`, `test_utils.py`)
- **Classes**: `PascalCase` (ex: `TelegramClient`)
- **Functions/Variables**: `snake_case` (ex: `process_dialog`, `env_int`)
- **Constants**: `UPPER_SNAKE_CASE` (ex: `API_ID`)
- **Private methods**: Prefixo `_` (ex: `_private_method`)

## Python Guidelines

### Type Hints
Use type hints para parâmetros de função e valores de retorno:
```python
async def process_dialog(
    client: TelegramClient,
    entity: Union[Channel, Chat, User],
    title: str,
    index: int,
    *,
    dry_run: bool,
) -> bool:
    """Processa um diálogo do Telegram."""
```

### Code Style
- Siga PEP 8
- Limite de linha: 100 caracteres
- Use docstrings para módulos, classes e funções
- Funções devem ter propósito único
- Use `logging` em vez de `print`

### Best Practices
- Use `pathlib` para operações com arquivos
- Use context managers (`with`) para gerenciamento de recursos
- Trate exceções apropriadamente com try/except
- Use `asyncio` para operações I/O pesadas (Telethon é assíncrono)

## Testing Standards

### Test Structure
- Organize testes espelhando a estrutura do código fonte
- Use nomes descritivos para testes
- Siga padrão AAA (Arrange, Act, Assert)
- Use fixtures para dados comuns de teste

### Coverage Goals
- Objetivo: 70%+ de cobertura
- Testes unitários para lógica de negócio
- Testes assíncronos para funções Telethon

### pytest Configuration
Configuração está em `pyproject.toml`:
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

## Environment Setup

### Installation with UV
```bash
# Clonar repositório
git clone https://github.com/gabrielramos/CleanTelegram
cd CleanTelegram

# Criar venv com UV
uv venv
source .venv/bin/activate

# Instalar dependências
uv pip install -e ".[dev]"

# Configurar ambiente
cp .env.example .env
# Editar .env com API_ID e API_HASH
```

### Environment Variables
- `API_ID`: ID da API do Telegram (obrigatório)
- `API_HASH`: Hash da API do Telegram (obrigatório)
- `SESSION_NAME`: Nome da sessão Telethon (opcional, padrão: "session")

## Security Guidelines

- Nunca commite `.env` com credenciais reais
- Nunca commite arquivos `*.session` - contêm credenciais de autenticação do Telegram
- Use `.env.example` como template
- Valide input do usuário
- Trate exceções de API apropriadamente (FloodWaitError, RPCError)
- Use logs em vez de print para debug

## Development Workflow

### Before Starting
1. Ative o ambiente virtual
2. Instale dependências: `uv pip install -e ".[dev]"`
3. Configure `.env` com credenciais

### During Development
1. Use type hints para melhor documentação
2. Execute testes frequentemente
3. Use mensagens de commit significativas
4. Formate código com Black antes de commitar

### Before Committing
1. `pytest` - Execute testes
2. `black --check src/ tests/` - Verifique formatação
3. `isort --check-only src/ tests/` - Verifique imports
4. `flake8 src/ tests/` - Verifique lint
5. `mypy src/` - Verifique tipos

## CLI Reference

```bash
python -m clean_telegram --help
```

Opções disponíveis:
- `--dry-run`: Não faz alterações, só mostra o que faria
- `--yes`: Não pede confirmação interativa
- `--limit N`: Limita a N diálogos processados (0 = todos)
