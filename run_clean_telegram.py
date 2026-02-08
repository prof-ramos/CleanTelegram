"""CleanTelegram: script para limpar conta Telegram via Telethon.

Funcionalidades:
- Apagar históricos de conversa (usuários/bots)
- Sair de grupos/canais
- Gerar relatórios de grupos, canais e contatos

Use com cuidado e teste primeiro com --dry-run.
"""

import asyncio
import sys
from pathlib import Path

# Adicionar src/ ao path para importar o módulo
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from clean_telegram.cli import main

if __name__ == "__main__":
    asyncio.run(main())
