# CleanTelegram

**Tags:** telegram, telethon, python, automation, privacy, cleanup

> [!WARNING]
> **Atenção:** Este projeto automatiza ações **destrutivas** (apagar conversas, sair de grupos). Use com cautela e sempre teste com `--dry-run` primeiro.

## 🚀 O que faz

O **CleanTelegram** é uma ferramenta de linha de comando (CLI) para gerenciar e limpar sua conta do Telegram de forma automatizada.

- 🗑️ **Limpeza:** Apaga conversas (DMs) e sai de grupos/canais em massa.
- 📦 **Backup:** Salva histórico completo de chats (mensagens + participantes + mídia).
- 📊 **Relatórios:** Gera inventários de seus grupos, canais e contatos.
- ☁️ **Cloud Upload:** Envia backups diretamente para seu "Saved Messages" no Telegram.

## 📋 Requisitos

- **Python 3.10+**
- Credenciais do Telegram (`API_ID` e `API_HASH`):
  - Obtenha em [my.telegram.org](https://my.telegram.org).
- (Opcional) `BOT_TOKEN` se for usar em modo Bot.

## 🛠️ Instalação

Clone o repositório e instale em modo editável (recomendado):

### Com uv (Recomendado)

```bash
# 1. Instalar dependências e o pacote
uv sync
uv pip install -e .

# 2. Configurar variáveis de ambiente
cp .env.example .env
# Edite .env com suas credenciais
```

### Com pip

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
```

## ⚙️ Configuração

O projeto suporta dois modos de operação, detectados automaticamente pelo `.env`:

1.  **Modo Usuário** (Padrão): Requer login interativo (número + código). Acesso total à sua conta pessoal.
    - Deixe `BOT_TOKEN` em branco no `.env`.
2.  **Modo Bot**: Usa `BOT_TOKEN`. Ações limitadas às permissões do bot nos chats.
    - Preencha `BOT_TOKEN` no `.env`.

## 🎮 Uso

Após instalar, o comando `cleantelegram` (ou `clean-telegram`) estará disponível.

### 🌟 Modo Interativo (Recomendado)

A maneira mais fácil de usar. Navegue por menus visuais para backup, limpeza e relatórios.

```bash
cleantelegram --interactive
# ou
cleantelegram -i
```

### 🖥️ Linha de Comando (CLI)

#### 1. Backup e Exportação

```bash
# Backup completo (JSON)
cleantelegram --backup-group -1001234567890

# Backup com MÍDIA (fotos, vídeos)
cleantelegram --backup-group -1001234567890 --download-media --media-types photo,video

# Backup e upload para Nuvem (Saved Messages)
cleantelegram --backup-group -1001234567890 --backup-to-cloud
```

#### 2. Relatórios

Gera arquivos CSV/JSON/TXT com lista de chats.

```bash
# Listar todos os grupos e canais
cleantelegram --report groups

# Listar contatos (tabela no terminal)
cleantelegram --report contacts --report-format json
```

#### 3. Limpeza (Cuidado!)

```bash
# Simulação (Dry-Run) - Segura, apenas lista o que seria feito
cleantelegram --clean --dry-run

# Executar limpeza real (apaga DMs, sai de canais)
cleantelegram --clean
```

> **Nota:** Por segurança, a limpeza real pode pedir confirmação extra ou ter limites de segurança.

## 🧪 Desenvolvimento

Para rodar os testes:

```bash
# Instalar dependências de dev
uv sync --all-extras

# Rodar testes
uv run pytest
```

## 📜 Licença

MIT
