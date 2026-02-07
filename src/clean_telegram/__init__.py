"""CleanTelegram: script para limpar conta Telegram via Telethon.

Este pacote fornece funcionalidades para:
- Apagar históricos de conversa (usuários/bots)
- Sair de grupos/canais
- Gerenciar diálogos do Telegram de forma programática
"""

__version__ = "0.1.0"

from .client import process_dialog
from .utils import env_int, safe_sleep

__all__ = ["process_dialog", "env_int", "safe_sleep"]
