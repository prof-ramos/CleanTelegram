"""Módulo de configuração persistente do CleanTelegram."""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

DEFAULT_CONFIG_PATH = Path.home() / ".cleantelegram" / "config.json"


@dataclass
class CleanTelegramConfig:
    """Configurações persistentes do CleanTelegram."""

    # Configurações de limpeza
    default_dry_run: bool = True
    default_dialog_limit: int = 0
    clean_whitelist: list[str] = field(default_factory=list)

    # Configurações de backup
    default_backup_dir: str = "backups"
    default_backup_format: str = "json"
    default_max_concurrent: int = 5

    # Configurações de relatório
    default_report_dir: str = "relatorios"
    default_report_format: str = "csv"


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> CleanTelegramConfig:
    """Carrega configuração do arquivo JSON, criando defaults se não existir.

    Args:
        path: Caminho do arquivo de configuração.

    Returns:
        Configuração carregada ou padrão se arquivo não existir.
    """
    if not path.exists():
        return CleanTelegramConfig()
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        valid_fields = CleanTelegramConfig.__dataclass_fields__
        return CleanTelegramConfig(**{k: v for k, v in data.items() if k in valid_fields})
    except (json.JSONDecodeError, TypeError, AttributeError):
        return CleanTelegramConfig()


def save_config(config: CleanTelegramConfig, path: Path = DEFAULT_CONFIG_PATH) -> None:
    """Salva configuração no arquivo JSON.

    Args:
        config: Configuração a salvar.
        path: Caminho do arquivo de configuração.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(asdict(config), f, ensure_ascii=False, indent=2)
