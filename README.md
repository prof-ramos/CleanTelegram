# CleanTelegram

**Tags:** telegram, telethon, python, cleanup, automation, privacy, destructive

**Atenção:** este projeto automatiza ações destrutivas na sua conta Telegram (apagar conversas e sair de grupos/canais). Use **por sua conta e risco**. Recomendo testar primeiro com `--dry-run`.

## O que faz

- Apaga diálogos (conversas) com usuários/bots.
- Sai de **grupos** e **canais**.
- **Gera relatórios** de grupos, canais e contatos em CSV, JSON ou TXT.
- **Backup completo** de grupos (mensagens + participantes).
- **Exporta participantes** e mensagens de grupos específicos.

> Observação: Telegram não tem um "bloquear grupo" de verdade (bloqueio é para **usuários**). Para grupos/canais, o equivalente prático é **sair**; e/ou **arquivar + silenciar**.

## Requisitos

- Python 3.10+
- Credenciais do Telegram API: `API_ID` e `API_HASH`
  - Pegue em: https://my.telegram.org
- Opcional para modo bot: `BOT_TOKEN`
  - Pegue com o BotFather no Telegram

## Instalação

### Com UV (recomendado)

```bash
# Instalar dependências
uv sync

# Criar arquivo .env
cp .env.example .env
```

### Com pip/venv

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edite `.env` com `API_ID` e `API_HASH`.

## Autenticação (usuário x bot)

O projeto detecta automaticamente o modo de autenticação:

- Se `BOT_TOKEN` estiver definido no `.env`, usa **modo bot**.
- Se `BOT_TOKEN` não estiver definido, usa **modo usuário** (sessão tradicional do Telethon).

Variáveis relacionadas:

- `SESSION_NAME` (modo usuário, padrão: `session`)
- `BOT_SESSION_NAME` (modo bot, padrão: `bot_session`)

## Uso

### Com UV

```bash
# Sincronizar dependências
uv sync

# Modo interativo
uv run python -m clean_telegram --interactive

# Modo bot (autodetectado por BOT_TOKEN no .env)
uv run python -m clean_telegram --report groups

# Limpeza (dry-run)
uv run python -m clean_telegram --dry-run

# Relatórios
uv run python -m clean_telegram --report groups
uv run python -m clean_telegram --report contacts
uv run python -m clean_telegram --report all

# Backup de grupo
uv run python -m clean_telegram --backup-group -1001234567890

# Exportar participantes
uv run python -m clean_telegram --export-members @nome_do_grupo

# Exportar mensagens
uv run python -m clean_telegram --export-messages @nome_do_grupo

# Help
uv run python -m clean_telegram --help
```

### Sem UV (módulo Python)

### Modo Interativo

Para uma experiência mais amigável, use o modo interativo com menus visuais:

```bash
python -m clean_telegram --interactive
# ou
python -m clean_telegram -i
# ou
python run_clean_telegram.py -i
```

O modo interativo oferece:
- 📋 Menus visuais para selecionar ações
- ⚠️ Confirmações guiadas para ações destrutivas
- 📊 Seleção de tipo e formato de relatórios
- 📈 Visualização de estatísticas da conta

### Limpeza de diálogos

Dry-run (recomendado):

```bash
python run_clean_telegram.py --dry-run
# ou
python -m clean_telegram --dry-run
```

Executar de verdade:

```bash
python run_clean_telegram.py
# ou
python -m clean_telegram
```

### Geração de relatórios

Gerar relatório de grupos e canais (CSV):

```bash
python -m clean_telegram --report groups
```

Gerar relatório de contatos (JSON):

```bash
python -m clean_telegram --report contacts --report-format json
```

Gerar todos os relatórios (TXT):

```bash
python -m clean_telegram --report all --report-format txt
```

Especificar caminho de saída:

```bash
python -m clean_telegram --report groups --report-output meu_relatorio.csv
```

### Backup e Exportação de Dados

**Backup completo de um grupo:**

```bash
# Backup em JSON (padrão)
uv run python -m clean_telegram --backup-group <chat_id>

# Backup em CSV
uv run python -m clean_telegram --backup-group <chat_id> --backup-format csv

# Backup em ambos os formatos
uv run python -m clean_telegram --backup-group <chat_id> --backup-format both
```

**Backup com MÍDIA:**

```bash
# Backup completo BAIXANDO ARQUIVOS DE MÍDIA
uv run python -m clean_telegram --backup-group <chat_id> --download-media

# Backup apenas de fotos e vídeos
uv run python -m clean_telegram --backup-group <chat_id> --download-media --media-types photo,video

# Backup com tipos específicos de mídia
uv run python -m clean_telegram --backup-group <chat_id> --download-media --media-types photo,video,document
```

**Backup para Cloud Chat (Saved Messages):**

```bash
# Envia arquivos de backup para o Cloud Chat (Mensagens Salvas)
uv run python -m clean_telegram --backup-group <chat_id> --backup-to-cloud

# Backup com mídia + envio para cloud
uv run python -m clean_telegram --backup-group <chat_id> --download-media --backup-to-cloud
```

> **☁️ O que é Cloud Chat?**
>
> O Cloud Chat do Telegram (Saved Messages / Mensagens Salvas) funciona como armazenamento pessoal na nuvem:
> - Armazenamento generoso (até 4GB para usuários Premium, 2GB para grátis)
> - Acessível de qualquer dispositivo com Telegram
> - Arquivos persistem mesmo se apagados localmente
> - Facilidade de acesso via app do Telegram
> - Organização com captions descritivos usando emojis

**Exportar apenas participantes ou mensagens:**

```bash
# Apenas participantes
uv run python -m clean_telegram --export-members <chat_id>

# Apenas mensagens (sem mídia)
uv run python -m clean_telegram --export-messages <chat_id>
```

**Especificar diretório de saída:**

```bash
# Backup em CSV com mídia
uv run python -m clean_telegram --backup-group <chat_id> --download-media --backup-format both --backup-output meu_backup/
```

**Identificadores de chat:**
- ID numérico: `-1001234567890`
- Username: `@nome_do_grupo`
- Link: `https://t.me/nome_do_grupo`

**Estrutura de backup criada:**
```
backups/
├── NomeDoGrupo_messages_20260207.json
├── NomeDoGrupo_participants_20260207.json
└── media/
    ├── photo/
    │   ├── 1701234567_7641443680_12345.jpg
    │   └── ...
    ├── video/
    ├── document/
    ├── audio/
    └── sticker/
```

## Notas

- Em **modo usuário**, na primeira execução o Telethon vai pedir o **número** e o **código** (e 2FA, se houver) e salvar uma sessão local em `session.session`.
- Em **modo bot**, o login usa `BOT_TOKEN` e a sessão local padrão é `bot_session.session`.
- Em modo bot, ações destrutivas e backup dependem das permissões administrativas do bot no chat.
- Pode haver limitações/erros por rate limit do Telegram; o script tenta ser cuidadoso.
- Relatórios são salvos no diretório `relatorios/` com timestamp no nome do arquivo.
- O modo `--report` não faz alterações na conta, apenas gera os arquivos de relatório.
