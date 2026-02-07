"""Testes para o módulo utils.py."""

import os

import pytest

from clean_telegram.utils import env_int, resolve_session_name, safe_sleep


class TestEnvInt:
    """Testes para env_int."""

    def test_env_int_valid(self, temp_env_vars):
        """Testa env_int com valor válido."""
        os.environ["TEST_VAR"] = "12345"
        result = env_int("TEST_VAR")
        assert result == 12345

    def test_env_int_missing(self, temp_env_vars):
        """Testa env_int com variável não definida."""
        with pytest.raises(SystemExit):
            env_int("NONEXISTENT_VAR")

    def test_env_int_invalid_value(self, temp_env_vars):
        """Testa env_int com valor não numérico."""
        os.environ["TEST_VAR"] = "not_a_number"
        with pytest.raises(SystemExit):
            env_int("TEST_VAR")

    def test_env_int_zero(self, temp_env_vars):
        """Testa env_int com valor zero."""
        os.environ["TEST_VAR"] = "0"
        result = env_int("TEST_VAR")
        assert result == 0

    def test_env_int_negative(self, temp_env_vars):
        """Testa env_int com valor negativo."""
        os.environ["TEST_VAR"] = "-100"
        result = env_int("TEST_VAR")
        assert result == -100

    def test_env_int_empty_string(self, temp_env_vars):
        """Testa env_int com string vazia."""
        os.environ["TEST_VAR"] = ""
        with pytest.raises(SystemExit):
            env_int("TEST_VAR")

    def test_env_int_spaces(self, temp_env_vars):
        """Testa env_int com espaços que devem ser removidos."""
        os.environ["TEST_VAR"] = "  123  "
        result = env_int("TEST_VAR")
        assert result == 123

    def test_env_int_float_string(self, temp_env_vars):
        """Testa env_int com string de float (deve falhar)."""
        os.environ["TEST_VAR"] = "12.5"
        with pytest.raises(SystemExit):
            env_int("TEST_VAR")


class TestSafeSleep:
    """Testes para safe_sleep."""

    @pytest.mark.asyncio
    async def test_safe_sleep_zero(self):
        """Testa safe_sleep com zero segundos."""
        await safe_sleep(0)
        # Não deve levantar exceção

    @pytest.mark.asyncio
    async def test_safe_sleep_positive(self):
        """Testa safe_sleep com valor positivo."""
        import time

        start = time.monotonic()
        await safe_sleep(0.1)
        elapsed = time.monotonic() - start
        assert elapsed >= 0.1

    @pytest.mark.asyncio
    async def test_safe_sleep_negative(self):
        """Testa safe_sleep com valor negativo (deve falhar)."""
        with pytest.raises(ValueError, match="não negativo"):
            await safe_sleep(-1)

    @pytest.mark.asyncio
    async def test_safe_sleep_invalid_type(self):
        """Testa safe_sleep com tipo inválido (deve falhar)."""
        with pytest.raises(ValueError, match="número"):
            await safe_sleep("invalid")

    @pytest.mark.asyncio
    async def test_safe_sleep_float(self):
        """Testa safe_sleep com valor float."""
        import time

        start = time.monotonic()
        await safe_sleep(0.05)
        elapsed = time.monotonic() - start
        assert elapsed >= 0.05


class TestResolveSessionName:
    """Testes para resolução do caminho de sessão."""

    def test_resolve_session_name_defaults_to_user_dir(self, tmp_path):
        """Nome simples deve usar ~/.clean_telegram."""
        cwd = tmp_path / "cwd"
        home = tmp_path / "home"
        cwd.mkdir()
        home.mkdir()

        result = resolve_session_name("session", cwd=cwd, home=home)

        assert result == str(home / ".clean_telegram" / "session")
        assert (home / ".clean_telegram").exists()

    def test_resolve_session_name_uses_absolute_path(self, tmp_path):
        """Caminho absoluto deve ser preservado."""
        cwd = tmp_path / "cwd"
        home = tmp_path / "home"
        cwd.mkdir()
        home.mkdir()
        absolute = tmp_path / "sessions" / "my_session"

        result = resolve_session_name(str(absolute), cwd=cwd, home=home)

        assert result == str(absolute)
        assert absolute.parent.exists()

    def test_resolve_session_name_uses_relative_directory(self, tmp_path):
        """Caminho relativo com diretório deve ser resolvido pelo cwd."""
        cwd = tmp_path / "cwd"
        home = tmp_path / "home"
        cwd.mkdir()
        home.mkdir()

        result = resolve_session_name("data/my_session", cwd=cwd, home=home)

        assert result == str(cwd / "data" / "my_session")
        assert (cwd / "data").exists()

    def test_resolve_session_name_supports_dot_relative_path(self, tmp_path):
        """Caminho relativo com ./ deve ser tratado como caminho explícito."""
        cwd = tmp_path / "cwd"
        home = tmp_path / "home"
        cwd.mkdir()
        home.mkdir()

        result = resolve_session_name("./session", cwd=cwd, home=home)

        assert result == str(cwd / "session")

    def test_resolve_session_name_migrates_legacy_file(self, tmp_path):
        """Sessão legada local deve ser migrada para ~/.clean_telegram."""
        cwd = tmp_path / "cwd"
        home = tmp_path / "home"
        cwd.mkdir()
        home.mkdir()
        legacy = cwd / "session.session"
        legacy.write_text("legacy-data", encoding="utf-8")

        result = resolve_session_name("session", cwd=cwd, home=home)

        modern = home / ".clean_telegram" / "session.session"
        assert result == str(home / ".clean_telegram" / "session")
        assert modern.exists()
        assert modern.read_text(encoding="utf-8") == "legacy-data"

    def test_resolve_session_name_defaults_when_empty(self, tmp_path):
        """Valor vazio deve cair no nome padrão 'session'."""
        cwd = tmp_path / "cwd"
        home = tmp_path / "home"
        cwd.mkdir()
        home.mkdir()

        result = resolve_session_name("   ", cwd=cwd, home=home)

        assert result == str(home / ".clean_telegram" / "session")
