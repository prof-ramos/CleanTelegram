"""Entry point para execução como módulo Python.

Usage:
    python -m clean_telegram --help
    python -m clean_telegram --report all
"""

import asyncio

from .cli import main as _main_async


def main() -> None:
    """Entry point síncrono para entry points de console."""
    asyncio.run(_main_async())


if __name__ == "__main__":
    main()
