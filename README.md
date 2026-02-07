# CleanTelegram

**Atenção:** este projeto automatiza ações destrutivas na sua conta Telegram (apagar conversas e sair de grupos/canais). Use **por sua conta e risco**. Recomendo testar primeiro com `--dry-run`.

## O que faz

- Apaga diálogos (conversas) com usuários/bots.
- Sai de **grupos** e **canais**.
- (Opcional) arquiva e silencia o que não dá para “bloquear”.

> Observação: Telegram não tem um “bloquear grupo” de verdade (bloqueio é para **usuários**). Para grupos/canais, o equivalente prático é **sair**; e/ou **arquivar + silenciar**.

## Requisitos

- Python 3.10+
- Credenciais do Telegram API: `API_ID` e `API_HASH`
  - Pegue em: https://my.telegram.org

## Instalação

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edite `.env` com `API_ID` e `API_HASH`.

## Uso

Dry-run (recomendado):

```bash
python clean_telegram.py --dry-run
```

Executar de verdade:

```bash
python clean_telegram.py
```

Opções úteis:

```bash
python clean_telegram.py --help
```

## Notas

- Na primeira execução, o Telethon vai pedir o **número** e o **código** (e 2FA, se houver) e salvará uma sessão local em `session.session`.
- Pode haver limitações/erros por rate limit do Telegram; o script tenta ser cuidadoso.
