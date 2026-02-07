# Fluxo UX — CleanTelegram

Documento que mapeia a jornada completa do usuário ao interagir com o **CleanTelegram**, um projeto Python moderno para limpeza de contas Telegram via Telethon.

---

## 1. Visão geral dos fluxos

```text
┌─────────────────────────────────────────────────────┐
│                  JORNADA DO USUÁRIO                  │
│                                                     │
│  ┌──────────┐   ┌──────────┐   ┌────────────────┐  │
│  │  Setup   │──▶│Execução  │──▶│ Processamento  │  │
│  │ Inicial  │   │  & Auth   │   │  de Diálogos   │  │
│  └──────────┘   └──────────┘   └────────────────┘  │
│                                                     │
│  3 modos de execução:                               │
│   --dry-run    Simulação segura (nenhuma alteração)  │
│   --yes        Execução sem confirmação interativa   │
│   (padrão)     Execução com confirmação "APAGAR TUDO"│
└─────────────────────────────────────────────────────┘
```

---

## 2. Fluxo de Setup Inicial (primeira vez)

### 2.1. Setup com UV (recomendado)

```text
 USUÁRIO                          SISTEMA
 ───────                          ──────
    │
    │  uv venv
    │  source .venv/bin/activate
    │  uv pip install -e ".[dev]"
    ├──────────────────────────────────▶ Instala telethon + python-dotenv
    │                                    + ferramentas de dev
    │
    │  cp .env.example .env
    │  (edita .env com API_ID e API_HASH)
    ├──────────────────────────────────▶ Configura credenciais
    │
    │  python -m clean_telegram --dry-run
    ├──────────────────────────────────▶ Primeira execução
    │                                    │
    │  ◀── Telethon pede telefone ───────┤
    │  Digita +55 11 9xxxx-xxxx          │
    ├──────────────────────────────────▶ │
    │                                    │
    │  ◀── Telethon pede código ─────────┤
    │  Digita código recebido no Telegram│
    ├──────────────────────────────────▶ │
    │                                    │
    │  ◀── (se 2FA) pede senha ──────────┤
    │  Digita senha 2FA                  │
    ├──────────────────────────────────▶ │
    │                                    │
    │                                    ├──▶ Salva ~/.clean_telegram/session.session
    │                                    │
    │  ◀── Dry-run: lista diálogos ──────┤
    │      (nenhuma alteração feita)      │
    ▼                                    ▼
```

### 2.2. Setup com pip tradicional

```bash
# Criar e ativar virtualenv
python -m venv .venv
source .venv/bin/activate

# Instalar dependências
pip install -e ".[dev]"

# Configurar ambiente
cp .env.example .env
# Editar .env com API_ID e API_HASH (https://my.telegram.org)

# Executar
python -m clean_telegram --dry-run
```

> **Nota:** Após o primeiro login, o arquivo de sessão (por padrão `~/.clean_telegram/session.session`) é reutilizado automaticamente. O fluxo de autenticação não se repete.

---

## 3. Estrutura do Projeto

```text
CleanTelegram/
├── src/
│   └── clean_telegram/
│       ├── __init__.py      # Pacote principal
│       ├── __main__.py      # Entry-point do CLI
│       ├── client.py        # Funções de interação com Telegram
│       └── utils.py         # Funções utilitárias
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Fixtures pytest
│   ├── test_client.py       # Testes do módulo client
│   └── test_utils.py        # Testes do módulo utils
├── docs/
│   └── UX_FLOW.md           # Este documento
├── .env.example             # Template de variáveis de ambiente
├── pyproject.toml           # Configuração do projeto
├── requirements.txt         # Dependências de produção
├── requirements-dev.txt     # Dependências de desenvolvimento
└── README.md                # Documentação do projeto
```

---

## 4. Fluxo Principal de Execução

```mermaid
flowchart TD
    A[python -m clean_telegram] --> B{Variáveis .env ok?}
    B -- "API_ID ou API_HASH faltando" --> C[/"SystemExit: Faltou ... no .env"/]
    B -- "OK" --> D{Qual modo?}

    D -- "--dry-run" --> G[Conecta ao Telegram]
    D -- "--yes" --> G
    D -- "padrão" --> E["Exibe: Digite 'APAGAR TUDO' para confirmar"]

    E --> F{Usuário digitou\n'APAGAR TUDO'?}
    F -- "Não" --> F1[/"Cancelado."/]
    F -- "Sim" --> G

    G --> H[Login via TelegramClient]
    H --> I["Log: Logado como @username"]
    I --> J[Itera sobre diálogos]

    J --> K{Limite atingido?\n--limit N}
    K -- "Sim" --> L["Log: Concluído. Diálogos processados: N"]
    K -- "Não / sem limite" --> M[Próximo diálogo]

    M --> N[process_dialog]
    N --> O{Tipo da entidade}

    O -- "Channel" --> P["SAIR de canal/megagrupo\nLeaveChannelRequest"]
    O -- "Chat" --> Q["SAIR de grupo legado\nDeleteChatUserRequest"]
    O -- "User / Bot" --> R["APAGAR conversa\nDeleteHistoryRequest"]
    O -- "Desconhecido" --> S["APAGAR diálogo\nclient.delete_dialog()"]

    Q -- "RPCError" --> Q1["Fallback:\nclient.delete_dialog()"]

    P --> T["safe_sleep(0.35s)"]
    Q --> T
    Q1 --> T
    R --> T
    S --> T

    T --> J

    style C fill:#d32f2f,color:#fff
    style F1 fill:#f57c00,color:#fff
    style L fill:#388e3c,color:#fff
```

---

## 5. Fluxo de Tratamento de Erros (por diálogo)

```mermaid
flowchart TD
    A[process_dialog] --> B{Resultado}

    B -- "Sucesso" --> C["safe_sleep(0.35s)\n→ próximo diálogo"]

    B -- "FloodWaitError" --> D{Tentativa < 5?}
    D -- "Sim" --> E["Log: Rate limit. Aguardando Xs...\nawait asyncio.sleep(wait_s)"]
    E --> A
    D -- "Não (5 tentativas)" --> F["Log: Max retries atingido\n→ pula diálogo"]

    B -- "RPCError" --> G["Log: RPCError + traceback\n→ pula diálogo"]

    B -- "Exception genérica" --> H["Log: Erro inesperado + traceback\n→ pula diálogo"]

    F --> I[Próximo diálogo]
    G --> I
    H --> I
    C --> I

    style C fill:#388e3c,color:#fff
    style F fill:#d32f2f,color:#fff
    style G fill:#f57c00,color:#fff
    style H fill:#f57c00,color:#fff
```

---

## 6. Fluxo do modo `--dry-run`

```text
┌─────────────────────────────────────────────────────────┐
│                    MODO DRY-RUN                         │
│                                                         │
│  Tudo funciona igual ao modo real, EXCETO:              │
│                                                         │
│  ✓ Confirmação "APAGAR TUDO" é IGNORADA (não pede)     │
│  ✓ Diálogos são iterados normalmente                    │
│  ✓ Tipo de cada entidade é identificado                 │
│  ✓ Logs são emitidos (SAIR / APAGAR)                    │
│  ✗ Nenhuma request destrutiva é enviada ao Telegram     │
│  ✗ LeaveChannelRequest → NÃO executado                  │
│  ✗ DeleteChatUserRequest → NÃO executado                │
│  ✗ DeleteHistoryRequest → NÃO executado                 │
│  ✗ client.delete_dialog() → NÃO executado               │
│                                                         │
│  O usuário vê exatamente o que SERIA feito.             │
└─────────────────────────────────────────────────────────┘
```

---

## 7. Mapa de decisões do roteador `process_dialog`

```text
  entity recebida
        │
        ▼
  ┌─────────────┐     Sim     ┌───────────────────────┐
  │ é Channel?  │────────────▶│ leave_channel()       │
  └──────┬──────┘             │ LeaveChannelRequest   │
         │ Não                └───────────────────────┘
         ▼
  ┌─────────────┐     Sim     ┌───────────────────────┐
  │ é Chat?     │────────────▶│ leave_legacy_chat()   │
  └──────┬──────┘             │ DeleteChatUserRequest │
         │ Não                │          │            │
         │                    │    RPCError?          │
         │                    │     ▼ Sim             │
         │                    │ client.delete_dialog()│
         │                    └───────────────────────┘
         ▼
  ┌─────────────┐     Sim     ┌───────────────────────┐
  │ é User/Bot? │────────────▶│ delete_dialog()       │
  └──────┬──────┘             │ DeleteHistoryRequest  │
         │ Não                └───────────────────────┘
         ▼
  ┌─────────────────┐         ┌───────────────────────┐
  │ Tipo            │────────▶│ client.delete_dialog() │
  │ desconhecido    │         │ (fallback genérico)   │
  └─────────────────┘         └───────────────────────┘
```

---

## 8. Tabela de estados do terminal (o que o usuário vê)

| Fase | Saída no terminal | Origem |
|------|-------------------|--------|
| Credenciais ausentes | `Faltou API_ID no .env` | `env_int()` / `main()` |
| Confirmação | `ATENÇÃO: isso vai apagar conversas...` | `main()` via `print()` |
| Cancelado | `Cancelado.` | `main()` via `print()` |
| Login | `Logado como: @user (id=123)` | `logger.info` |
| Canal/megagrupo | `[1] SAIR de canal/megagrupo: NomeCanal` | `logger.info` |
| Grupo legado | `[2] SAIR de grupo legado (Chat): NomeGrupo` | `logger.info` |
| Conversa user/bot | `[3] APAGAR conversa: NomeUsuario` | `logger.info` |
| Tipo desconhecido | `[4] APAGAR diálogo (tipo desconhecido): ...` | `logger.info` |
| Rate limit | `Rate limit (FloodWait)... Aguardando Xs` | `logger.warning` |
| Max retries | `Max retries atingido; pulando 'NomeDialogo'` | `logger.error` |
| Erro RPC | `RPCError em 'NomeDialogo'` | `logger.exception` |
| Erro genérico | `Erro inesperado em 'NomeDialogo'` | `logger.exception` |
| Conclusão | `Concluído. Diálogos processados: N` | `logger.info` |

---

## 9. Cenários de uso típicos

### 9.1 Primeiro uso (cauteloso)

```bash
# 1. Setup com UV (recomendado)
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
cp .env.example .env  # editar com API_ID e API_HASH

# 2. Testar com dry-run
python -m clean_telegram --dry-run

# 3. Testar com poucos diálogos
python -m clean_telegram --dry-run --limit 5

# 4. Executar de verdade (poucos diálogos)
python -m clean_telegram --limit 5
# → Digita "APAGAR TUDO"

# 5. Executar em tudo
python -m clean_telegram
# → Digita "APAGAR TUDO"
```

### 9.2 Uso automatizado (script/cron)

```bash
python -m clean_telegram --yes
# Pula confirmação interativa — usar com cuidado!
```

### 9.3 Debugging de rate limit

```bash
python -m clean_telegram --limit 3
# Observar logs de FloodWaitError
# Ajustar --limit conforme necessário
```

### 9.4 Executar testes

```bash
# Executar todos os testes
pytest

# Executar com cobertura
pytest --cov=src/clean_telegram --cov-report=html

# Executar teste específico
pytest tests/test_client.py -v
```

---

## 10. Diagrama de ciclo de vida da sessão

```text
  Primeira execução               Execuções seguintes
  ──────────────────              ───────────────────
        │                               │
        ▼                               ▼
  ┌──────────────┐               ┌──────────────┐
  │ Sem sessão   │               │ session.     │
  │ local        │               │ session      │
  └──────┬───────┘               │ existe       │
         │                       └──────┬───────┘
         ▼                              ▼
  ┌──────────────┐               ┌──────────────┐
  │ Telefone     │               │ Login        │
  │ + Código     │               │ automático   │
  │ + (2FA)      │               │              │
  └──────┬───────┘               └──────┬───────┘
         │                              │
         ▼                              ▼
  ┌──────────────┐               ┌──────────────┐
  │ Cria         │               │ Reutiliza    │
  │ session.     │               │ sessão       │
  │ session      │               │ existente    │
  └──────┬───────┘               └──────┬───────┘
         │                              │
         └──────────┬───────────────────┘
                    ▼
             ┌──────────────┐
             │ Executa      │
             │ limpeza      │
             └──────────────┘
```

> **Importante:** O arquivo `*.session` contém credenciais de autenticação e **nunca** deve ser commitado no repositório. Ele já está configurado no `.gitignore`.

---

## 11. Comandos de Desenvolvimento

```bash
# Verificar ajuda
python -m clean_telegram --help

# Formatar código
black src/ tests/

# Ordenar imports
isort src/ tests/

# Executar linting
flake8 src/ tests/

# Verificar tipos
mypy src/

# Executar todos os checks de uma vez
black --check src/ tests/ && isort --check-only src/ tests/ && flake8 src/ tests/ && mypy src/
```
