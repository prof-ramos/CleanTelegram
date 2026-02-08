"""Testes estendidos para o módulo reports.py.

Cobre: generate_all_reports, generate_contacts_report com caminho padrão,
_safe_getattr com fallback, e contacts com formato inválido.
"""

from datetime import datetime
from pathlib import Path
from unittest import mock

import pytest

from clean_telegram.reports import (
    _safe_getattr,
    generate_all_reports,
    generate_contacts_report,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_client_with_users():
    """Cria um mock de TelegramClient com diálogos de usuários."""
    client = mock.AsyncMock()

    class MockUser:
        id = 111222
        first_name = "Maria"
        last_name = "Santos"
        username = "mariasantos"
        bot = False
        verified = True
        premium = False
        phone = "+5511999999999"

        class status:
            was_online = datetime(2024, 2, 7, 14, 30)

    class MockChannel:
        id = 555666
        megagroup = True

    async def mock_iter_dialogs():
        dialog1 = mock.Mock()
        dialog1.name = "Maria Santos"
        dialog1.entity = MockUser()

        dialog2 = mock.Mock()
        dialog2.name = "Canal"
        dialog2.entity = MockChannel()

        yield dialog1
        yield dialog2

    client.iter_dialogs = mock_iter_dialogs
    return client


@pytest.fixture
def mock_client_mixed():
    """Client com ambos tipos para generate_all_reports."""
    client = mock.AsyncMock()

    class MockChannel:
        id = 123456
        username = "grupoteste"
        participants_count = 150
        megagroup = True
        broadcast = False
        creator = False
        admin_rights = None
        date = datetime(2024, 1, 15, 10, 30)

    class MockUser:
        id = 111222
        first_name = "Maria"
        last_name = "Santos"
        username = "mariasantos"
        bot = False
        verified = True
        premium = False
        phone = ""

        class status:
            was_online = datetime(2024, 2, 7, 14, 30)

    async def mock_iter_dialogs():
        d1 = mock.Mock()
        d1.name = "Grupo"
        d1.entity = MockChannel()

        d2 = mock.Mock()
        d2.name = "Maria"
        d2.entity = MockUser()

        yield d1
        yield d2

    client.iter_dialogs = mock_iter_dialogs
    return client


# =============================================================================
# Testes: _safe_getattr
# =============================================================================


class TestSafeGetattr:
    """Testes para _safe_getattr."""

    def test_returns_attribute_value(self):
        obj = mock.Mock()
        obj.name = "test"
        assert _safe_getattr(obj, "name") == "test"

    def test_returns_default_for_missing_attribute(self):
        obj = mock.Mock(spec=[])
        assert _safe_getattr(obj, "nonexistent", "default") == "default"

    def test_returns_none_by_default(self):
        obj = mock.Mock(spec=[])
        assert _safe_getattr(obj, "nonexistent") is None

    def test_handles_none_object(self):
        assert _safe_getattr(None, "attr", "fallback") == "fallback"


# =============================================================================
# Testes: generate_contacts_report com caminho padrão
# =============================================================================


class TestGenerateContactsReportDefaultPath:
    """Testa generate_contacts_report com output_path=None."""

    @pytest.mark.asyncio
    async def test_default_path_uses_timestamp(self, mock_client_with_users, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        result = await generate_contacts_report(
            mock_client_with_users,
            output_path=None,
            output_format="csv",
        )

        assert result.startswith("relatorios/contacts_")
        assert result.endswith(".csv")
        assert Path(result).exists()

    @pytest.mark.asyncio
    async def test_contacts_invalid_format(self, mock_client_with_users, tmp_path):
        output_path = tmp_path / "test.invalid"

        with pytest.raises(ValueError, match="Formato não suportado"):
            await generate_contacts_report(
                mock_client_with_users,
                output_path=str(output_path),
                output_format="invalid",
            )


# =============================================================================
# Testes: generate_all_reports
# =============================================================================


class TestGenerateAllReports:
    """Testa generate_all_reports()."""

    @pytest.mark.asyncio
    async def test_generates_both_report_types(self, mock_client_mixed, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        results = await generate_all_reports(mock_client_mixed, output_format="csv")

        assert "groups_channels" in results
        assert "contacts" in results
        assert Path(results["groups_channels"]).exists()
        assert Path(results["contacts"]).exists()

    @pytest.mark.asyncio
    async def test_generate_all_reports_json(self, mock_client_mixed, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        results = await generate_all_reports(mock_client_mixed, output_format="json")

        assert results["groups_channels"].endswith(".json")
        assert results["contacts"].endswith(".json")

    @pytest.mark.asyncio
    async def test_generate_all_reports_txt(self, mock_client_mixed, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        results = await generate_all_reports(mock_client_mixed, output_format="txt")

        assert results["groups_channels"].endswith(".txt")
        assert results["contacts"].endswith(".txt")
