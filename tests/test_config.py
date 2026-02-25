"""Testes para o módulo config.py (configuração persistente)."""

import json
from pathlib import Path

import pytest

from clean_telegram.config import (
    CleanTelegramConfig,
    load_config,
    save_config,
)


class TestCleanTelegramConfig:
    """Testes para o dataclass CleanTelegramConfig."""

    def test_default_values(self):
        """Deve ter valores padrão corretos."""
        cfg = CleanTelegramConfig()
        assert cfg.default_dry_run is True
        assert cfg.default_dialog_limit == 0
        assert cfg.clean_whitelist == []
        assert cfg.default_backup_dir == "backups"
        assert cfg.default_backup_format == "json"
        assert cfg.default_max_concurrent == 5
        assert cfg.default_report_dir == "relatorios"
        assert cfg.default_report_format == "csv"

    def test_custom_values(self):
        """Deve aceitar valores customizados."""
        cfg = CleanTelegramConfig(
            default_dry_run=False,
            clean_whitelist=["@grupo1", "12345"],
            default_backup_dir="meus_backups",
        )
        assert cfg.default_dry_run is False
        assert cfg.clean_whitelist == ["@grupo1", "12345"]
        assert cfg.default_backup_dir == "meus_backups"


class TestLoadConfig:
    """Testes para load_config()."""

    def test_returns_default_when_file_not_exists(self, tmp_path):
        """Deve retornar configuração padrão se arquivo não existir."""
        path = tmp_path / "nonexistent.json"
        cfg = load_config(path)
        assert isinstance(cfg, CleanTelegramConfig)
        assert cfg.default_dry_run is True
        assert cfg.clean_whitelist == []

    def test_loads_valid_config_file(self, tmp_path):
        """Deve carregar configuração de arquivo JSON válido."""
        path = tmp_path / "config.json"
        data = {
            "default_dry_run": False,
            "default_dialog_limit": 100,
            "clean_whitelist": ["@chat1", "@chat2"],
            "default_backup_dir": "custom_backups",
            "default_backup_format": "csv",
            "default_max_concurrent": 10,
            "default_report_dir": "custom_reports",
            "default_report_format": "json",
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        cfg = load_config(path)
        assert cfg.default_dry_run is False
        assert cfg.default_dialog_limit == 100
        assert cfg.clean_whitelist == ["@chat1", "@chat2"]
        assert cfg.default_backup_dir == "custom_backups"
        assert cfg.default_backup_format == "csv"

    def test_ignores_unknown_fields(self, tmp_path):
        """Deve ignorar campos desconhecidos no JSON."""
        path = tmp_path / "config.json"
        data = {
            "default_dry_run": False,
            "unknown_field": "should_be_ignored",
            "another_unknown": 999,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        cfg = load_config(path)
        assert cfg.default_dry_run is False
        assert not hasattr(cfg, "unknown_field")

    def test_returns_default_on_invalid_json(self, tmp_path):
        """Deve retornar configuração padrão se JSON for inválido."""
        path = tmp_path / "config.json"
        path.write_text("not valid json {{{", encoding="utf-8")

        cfg = load_config(path)
        assert isinstance(cfg, CleanTelegramConfig)
        assert cfg.default_dry_run is True  # valor padrão

    def test_returns_default_on_type_error(self, tmp_path):
        """Deve retornar configuração padrão se JSON tiver tipos incompatíveis."""
        path = tmp_path / "config.json"
        # Forçar TypeError passando lista no lugar de dict-like
        path.write_text("[1, 2, 3]", encoding="utf-8")

        cfg = load_config(path)
        assert isinstance(cfg, CleanTelegramConfig)
        assert cfg.default_dry_run is True


class TestSaveConfig:
    """Testes para save_config()."""

    def test_saves_config_to_json(self, tmp_path):
        """Deve salvar configuração como JSON válido."""
        path = tmp_path / "config.json"
        cfg = CleanTelegramConfig(
            default_dry_run=False,
            clean_whitelist=["@grupo_teste"],
            default_backup_dir="meus_backups",
        )

        save_config(cfg, path)

        assert path.exists()
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        assert data["default_dry_run"] is False
        assert data["clean_whitelist"] == ["@grupo_teste"]
        assert data["default_backup_dir"] == "meus_backups"

    def test_creates_parent_directories(self, tmp_path):
        """Deve criar diretórios pai se não existirem."""
        path = tmp_path / "nested" / "dir" / "config.json"
        cfg = CleanTelegramConfig()

        save_config(cfg, path)

        assert path.exists()

    def test_round_trip(self, tmp_path):
        """Deve manter dados após save + load."""
        path = tmp_path / "config.json"
        original = CleanTelegramConfig(
            default_dry_run=False,
            default_dialog_limit=50,
            clean_whitelist=["@a", "@b", "123456"],
            default_backup_dir="backup_dir",
            default_backup_format="csv",
            default_max_concurrent=3,
            default_report_dir="reports_dir",
            default_report_format="txt",
        )

        save_config(original, path)
        loaded = load_config(path)

        assert loaded.default_dry_run == original.default_dry_run
        assert loaded.default_dialog_limit == original.default_dialog_limit
        assert loaded.clean_whitelist == original.clean_whitelist
        assert loaded.default_backup_dir == original.default_backup_dir
        assert loaded.default_backup_format == original.default_backup_format
        assert loaded.default_max_concurrent == original.default_max_concurrent
        assert loaded.default_report_dir == original.default_report_dir
        assert loaded.default_report_format == original.default_report_format

    def test_saves_with_utf8_content(self, tmp_path):
        """Deve salvar conteúdo UTF-8 corretamente (acentos, emojis)."""
        path = tmp_path / "config.json"
        cfg = CleanTelegramConfig(
            clean_whitelist=["Grupo Família 👨‍👩‍👧", "ação_teste"],
        )

        save_config(cfg, path)
        loaded = load_config(path)

        assert "Grupo Família 👨‍👩‍👧" in loaded.clean_whitelist
        assert "ação_teste" in loaded.clean_whitelist
