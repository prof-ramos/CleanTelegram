# CleanTelegram

> Automação para limpar sua conta Telegram: apaga conversas, sai de grupos e canais.

**Tags:** `telegram` `telethon` `python` `cleanup` `automation` `privacy`

---

> **ATENÇÃO — AÇÃO DESTRUTIVA**
>
> Este script **apaga conversas** e **sai de grupos/canais** da sua conta Telegram.
> As ações são **irreversíveis**. Teste sempre com `--dry-run` antes de executar de verdade.

---

## Funcionalidades

- Apaga histórico de conversas com **usuários** e **bots** (com revogação quando possível)
- Sai de **canais** e **megagrupos** (`LeaveChannelRequest`)
- Sai de **grupos legados** (`DeleteChatUserRequest`) com fallback automático
- Modo **`--dry-run`** — simula a execução sem alterar nada
- Confirmação obrigatória **`"APAGAR TUDO"`** para evitar execução acidental
- **Rate-limit handling** — retry automático com backoff em caso de `FloodWaitError`
- Delay entre operações (`0.35s`) para proteger contra bloqueio temporário da API

> **Nota:** O Telegram não oferece "bloqueio" de grupos/canais — apenas de usuários.
> Para grupos e canais, o equivalente prático é **sair**.

## Requisitos

- **Python 3.10** ou superior
- Credenciais da **Telegram API**: `API_ID` e `API_HASH`
  - Obtenha em: [https://my.telegram.org](https://my.telegram.org)

## Instalação

```bash
# 1. Clonar o repositório
git clone https://github.com/prof-ramos/CleanTelegram.git
cd CleanTelegram

# 2. Criar e ativar virtualenv
python -m venv .venv
source .venv/bin/activate        # Linux / macOS
# .venv\Scripts\activate         # Windows

# 3. Instalar dependências
pip install -r requirements.txt

# 4. Configurar variáveis de ambiente
cp .env.example .env
```

Edite o arquivo `.env` com suas credenciais:

```ini
API_ID=123456
API_HASH=abc123def456...
SESSION_NAME=session          # opcional; padrão persiste em ~/.clean_telegram/
```

## Uso

### Modo seguro (dry-run) — recomendado para começar

Simula a execução e mostra o que **seria** feito, sem alterar nada:

```bash
python clean_telegram.py --dry-run
```

Saída esperada:

```
2025-01-15 10:30:00 INFO: Logado como: @seuuser (id=123456789)
2025-01-15 10:30:01 INFO: [1] SAIR de canal/megagrupo: Canal Exemplo
2025-01-15 10:30:01 INFO: [2] APAGAR conversa: João Silva
2025-01-15 10:30:01 INFO: [3] SAIR de grupo legado (Chat): Grupo Antigo
...
2025-01-15 10:30:02 INFO: Concluído. Diálogos processados: 3
```

### Execução real

Pede confirmação interativa antes de executar:

```bash
python clean_telegram.py
```

```
ATENÇÃO: isso vai apagar conversas e sair de grupos/canais.
Digite 'APAGAR TUDO' para confirmar: APAGAR TUDO
```

### Limitar quantidade de diálogos

Processa apenas os primeiros N diálogos (útil para testar de forma gradual):

```bash
python clean_telegram.py --limit 5
```

### Pular confirmação interativa

Para uso em scripts ou automação (usar com cuidado):

```bash
python clean_telegram.py --yes
```

## Referência de flags

| Flag | Descrição | Padrão |
|------|-----------|--------|
| `--dry-run` | Simula a execução sem alterar nada | Desativado |
| `--yes` | Pula a confirmação interativa `"APAGAR TUDO"` | Desativado |
| `--limit N` | Processa no máximo N diálogos (`0` = todos) | `0` |
| `--help` | Exibe ajuda com todas as opções | — |

## Variáveis de ambiente

| Variável | Obrigatória | Descrição |
|----------|:-----------:|-----------|
| `API_ID` | Sim | ID da aplicação Telegram (inteiro) |
| `API_HASH` | Sim | Hash da aplicação Telegram (string hex) |
| `SESSION_NAME` | Não | Nome/caminho da sessão. Nome simples usa `~/.clean_telegram/`; caminho absoluto/relativo usa o caminho informado |

## Como funciona

O script segue um fluxo linear assíncrono:

```
main()
  │
  ├─ Carrega .env e valida credenciais
  ├─ Pede confirmação "APAGAR TUDO" (se necessário)
  ├─ Conecta ao Telegram via TelegramClient
  │
  └─ Para cada diálogo:
       │
       ├─ Channel (canal/megagrupo) → LeaveChannelRequest
       ├─ Chat (grupo legado)       → DeleteChatUserRequest
       │                               └─ fallback: client.delete_dialog()
       ├─ User / Bot                → DeleteHistoryRequest
       └─ Tipo desconhecido         → client.delete_dialog()
       │
       └─ safe_sleep(0.35s)
```

### Tratamento de erros

| Erro | Comportamento |
|------|---------------|
| `FloodWaitError` | Retry automático (até 5 tentativas), aguardando o tempo indicado pela API |
| `RPCError` | Loga o erro com traceback e pula para o próximo diálogo |
| `Exception` genérica | Loga o erro completo e pula para o próximo diálogo |

## Primeira execução

Na primeira vez que rodar o script, o Telethon solicitará:

1. **Número de telefone** — no formato internacional (ex.: `+5511999999999`)
2. **Código de verificação** — recebido no próprio Telegram
3. **Senha 2FA** — se autenticação em duas etapas estiver ativada

Após o login, um arquivo de sessão (ex.: `~/.clean_telegram/session.session`) é criado e reaproveitado nas próximas execuções, evitando pedir telefone/código novamente.

> **Segurança:** O arquivo `*.session` contém credenciais de autenticação.
> Ele está no `.gitignore` e **nunca** deve ser commitado ou compartilhado.

## Estrutura do projeto

```
CleanTelegram/
├── clean_telegram.py      # Script principal (ponto de entrada único)
├── requirements.txt       # Dependências (telethon, python-dotenv)
├── .env.example           # Template de variáveis de ambiente
├── .gitignore             # Ignora .venv, .env, *.session, __pycache__
├── CLAUDE.md              # Guia para assistentes de IA
├── docs/
│   └── UX_FLOW.md         # Fluxo UX detalhado com diagramas
└── README.md              # Este arquivo
```

## Dependências

| Pacote | Versão | Finalidade |
|--------|--------|------------|
| [Telethon](https://github.com/LonamiWebs/Telethon) | 1.42.0 | Cliente Telegram (MTProto) |
| [python-dotenv](https://github.com/theskumar/python-dotenv) | 1.2.1 | Carregamento de variáveis do `.env` |

## Perguntas frequentes

<details>
<summary><strong>Posso recuperar conversas apagadas?</strong></summary>

Não. A ação é irreversível. O script usa `DeleteHistoryRequest` com `revoke=True`, que apaga o histórico para ambos os lados quando possível. Use sempre `--dry-run` antes.
</details>

<details>
<summary><strong>O script pode bloquear minha conta?</strong></summary>

O script inclui delays entre operações (`0.35s`) e retry automático em caso de `FloodWaitError` para minimizar esse risco. Ainda assim, executar em contas com muitos diálogos pode gerar rate limits temporários do Telegram. Use `--limit` para processar em lotes menores.
</details>

<details>
<summary><strong>E se eu receber "FloodWaitError"?</strong></summary>

O script trata automaticamente: aguarda o tempo exigido pela API e tenta novamente (até 5 vezes). Se persistir, o diálogo é pulado e o script continua. Você pode re-executar depois para processar os diálogos restantes.
</details>

<details>
<summary><strong>Posso escolher quais conversas apagar?</strong></summary>

Atualmente não. O script processa **todos** os diálogos da conta (ou os primeiros N com `--limit`). Filtragem seletiva ainda não foi implementada.
</details>

<details>
<summary><strong>Como deslogar / trocar de conta?</strong></summary>

Delete o arquivo de sessão usado (por padrão `~/.clean_telegram/session.session`, ou o caminho definido em `SESSION_NAME`). Na próxima execução, o Telethon pedirá login novamente.
</details>
