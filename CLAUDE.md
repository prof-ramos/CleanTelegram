# CLAUDE.md

Guia para assistentes de IA que trabalham neste repositório.

## Visão geral do projeto

**CleanTelegram** é um script Python de propósito único que automatiza a limpeza de uma conta Telegram via [Telethon](https://github.com/LonamiWebs/Telethon). Ele apaga históricos de conversa (usuários/bots) e sai de grupos/canais.

Este é um projeto **destrutivo por design** — qualquer alteração deve preservar os mecanismos de segurança existentes (`--dry-run`, confirmação interativa `"APAGAR TUDO"`).

## Estrutura do repositório

```text
CleanTelegram/
├── clean_telegram.py      # Script principal (ponto de entrada único)
├── requirements.txt       # Dependências Python (telethon, python-dotenv)
├── .env.example           # Template de variáveis de ambiente
├── .gitignore             # Ignora .venv, .env, *.session, __pycache__
└── README.md              # Documentação do projeto (pt-BR)
```

Não há subdiretórios de código, testes, CI/CD ou configuração de linting.

## Stack tecnológica

| Componente        | Tecnologia                          |
| ----------------- | ----------------------------------- |
| Linguagem         | Python 3.10+                        |
| Cliente Telegram  | Telethon 1.42.0                     |
| Variáveis de amb. | python-dotenv 1.2.1                 |
| Runtime assíncrono| asyncio (stdlib)                    |
| Gerenciador deps  | pip + requirements.txt              |

## Comandos essenciais

```bash
# Criar e ativar virtualenv
python -m venv .venv
source .venv/bin/activate

# Instalar dependências
pip install -r requirements.txt

# Copiar e configurar variáveis de ambiente
cp .env.example .env
# Editar .env com API_ID e API_HASH (https://my.telegram.org)

# Execução em modo seguro (dry-run — não altera nada)
python clean_telegram.py --dry-run

# Execução real (pede confirmação "APAGAR TUDO")
python clean_telegram.py

# Pular confirmação interativa
python clean_telegram.py --yes

# Limitar quantidade de diálogos processados
python clean_telegram.py --limit 10

# Ver todas as opções
python clean_telegram.py --help
```

## Arquitetura do código (`clean_telegram.py`)

O script segue um fluxo linear assíncrono:

1. **`main()`** — Entry-point: configura logging, carrega `.env`, parseia argumentos, pede confirmação e itera sobre os diálogos.
2. **`_process_dialog()`** — Roteador que escolhe a ação correta conforme o tipo da entidade:
   - `Channel` → `leave_channel()` (canais e megagrupos)
   - `Chat` → `leave_legacy_chat()` (grupos legados), com fallback via `client.delete_dialog()`
   - `User` / bots → `delete_dialog()` (apaga histórico)
   - Tipo desconhecido → `client.delete_dialog()` (fallback genérico)
3. **Funções auxiliares:**
   - `env_int()` — Lê variável de ambiente obrigatória como int
   - `safe_sleep()` — Delay entre operações (0.35s) para evitar rate limit
   - `delete_dialog()` — Apaga histórico via `DeleteHistoryRequest`
   - `leave_channel()` — Sai de canal/megagrupo via `LeaveChannelRequest`
   - `leave_legacy_chat()` — Sai de grupo legado via `DeleteChatUserRequest`

### Tratamento de erros

- **`FloodWaitError`**: Retry com backoff exponencial (até 5 tentativas). Aguarda o tempo indicado pela API antes de tentar novamente.
- **`RPCError`**: Loga o erro e pula o diálogo.
- **`Exception` genérica**: Catch-all com log completo do traceback.

## Convenções do projeto

### Idioma

- **Documentação, comentários, docstrings e mensagens de log**: português brasileiro (pt-BR).
- **Nomes de variáveis, funções e parâmetros**: inglês (padrão Python).
- **Mensagens de commit**: português é aceitável, mas o prefixo segue Conventional Commits em inglês (`feat:`, `fix:`, `docs:`, `chore:`).

### Estilo de código

- Sem linter ou formatter configurado — manter consistência com o código existente.
- Type hints nas assinaturas de funções.
- Docstrings em português para todas as funções.
- Keyword-only arguments para flags booleanas (ex.: `*, dry_run: bool`).
- Logging via `logger` (módulo `logging`), não `print()` (exceto para interação direta com o usuário).

### Segurança — regras invioláveis

1. **Nunca remover ou enfraquecer** o mecanismo de confirmação `"APAGAR TUDO"`.
2. **Nunca remover** a flag `--dry-run` — ela é a principal proteção do usuário.
3. **Nunca fazer commit de arquivos `.env`** ou `*.session` — contêm credenciais sensíveis.
4. **Manter rate-limit handling** — sem ele, a conta do usuário pode ser temporariamente bloqueada pela API do Telegram.
5. **Preservar delays entre operações** (`safe_sleep`) para reduzir risco de flood.

## Variáveis de ambiente

| Variável       | Obrigatória | Descrição                                    |
| -------------- | ----------- | -------------------------------------------- |
| `API_ID`       | Sim         | ID da aplicação Telegram (inteiro)           |
| `API_HASH`     | Sim         | Hash da aplicação Telegram (string hex)      |
| `SESSION_NAME` | Não         | Nome do arquivo de sessão (padrão: `session`)|

## Testes

Não há framework de testes configurado. O modo `--dry-run` é o mecanismo atual de verificação segura. Se testes forem adicionados no futuro:
- Usar `pytest` como framework.
- Mockar chamadas ao Telethon/Telegram API (nunca fazer chamadas reais em testes).
- Colocar testes em um diretório `tests/`.

## Dependências

Fixadas por versão exata em `requirements.txt`:
- **telethon==1.42.0** — Cliente Telegram (MTProto)
- **python-dotenv==1.2.1** — Carregamento de `.env`

Para adicionar dependências, atualizar `requirements.txt` com versão exata (ex.: `pacote==X.Y.Z`).
