"""Testes para o entry point __main__.py."""

from unittest import mock

import pytest


class TestMainModule:
    """Testes para o módulo __main__."""

    def test_main_should_run_async_main(self, mocker):
        """Deve executar main() assíncrono do cli."""
        mock_asyncio_run = mocker.patch("asyncio.run")
        mock_main_async = mocker.patch("clean_telegram.__main__._main_async")

        # Import and execute
        from clean_telegram.__main__ import main

        main()

        mock_asyncio_run.assert_called_once()
        mock_main_async.assert_called_once()


class TestCliMain:
    """Testes para cli.main() e cli.main_sync()."""

    def test_should_run_main_async(self, mocker):
        """Deve executar main() de forma assíncrona via main_sync()."""
        from clean_telegram import cli

        mock_run = mocker.patch("asyncio.run")
        mock_main = mocker.patch.object(cli, "main", return_value=mocker.AsyncMock())

        cli.main_sync()

        mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_main_should_load_dotenv(self, mocker):
        """Deve carregar variáveis de ambiente em main()."""
        from clean_telegram import cli

        mock_load = mocker.patch("clean_telegram.cli.load_dotenv")
        mocker.patch("clean_telegram.cli.parse_args", return_value=mock.Mock(
            interactive=True,
            dry_run=False,
            yes=True,
            report=None,
            backup_group=None,
            export_members=None,
            export_messages=None,
            limit=0
        ))
        mock_client = mocker.AsyncMock()
        mock_client.__aenter__ = mocker.AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = mocker.AsyncMock()
        mocker.patch("clean_telegram.cli.create_client", return_value=(mock_client, mock.Mock(mode="user", session_name="session")))
        mocker.patch("clean_telegram.cli.start_client", return_value=mocker.AsyncMock())
        mocker.patch("clean_telegram.cli.interactive_main", return_value=mocker.AsyncMock())

        await cli.main()

        mock_load.assert_called_once()

    @pytest.mark.asyncio
    async def test_main_should_parse_args(self, mocker):
        """Deve fazer parse dos argumentos."""
        from clean_telegram import cli

        mocker.patch("clean_telegram.cli.load_dotenv")

        mock_parse = mocker.patch("clean_telegram.cli.parse_args")
        mock_parse.return_value = mock.Mock(
            interactive=False,
            dry_run=True,
            yes=True,
            report=None,
            backup_group=None,
            export_members=None,
            export_messages=None,
            limit=10
        )

        mock_client = mocker.AsyncMock()
        mock_client.__aenter__ = mocker.AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = mocker.AsyncMock()

        mocker.patch("clean_telegram.cli.create_client", return_value=(mock_client, mock.Mock(mode="user", session_name="session")))
        mocker.patch("clean_telegram.cli.start_client", return_value=mocker.AsyncMock())
        mocker.patch("clean_telegram.cli.clean_all_dialogs", return_value=0)

        await cli.main()

        mock_parse.assert_called_once()

    @pytest.mark.asyncio
    async def test_main_should_create_client(self, mocker):
        """Deve criar cliente Telegram."""
        from clean_telegram import cli

        mocker.patch("clean_telegram.cli.load_dotenv")
        mocker.patch("clean_telegram.cli.parse_args", return_value=mock.Mock(
            interactive=False,
            dry_run=True,
            yes=True,
            report=None,
            backup_group=None,
            export_members=None,
            export_messages=None,
            limit=0
        ))

        mock_client = mocker.AsyncMock()
        mock_client.__aenter__ = mocker.AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = mocker.AsyncMock()

        mock_auth_config = mock.Mock(mode="user", session_name="session")

        mock_create = mocker.patch("clean_telegram.cli.create_client", return_value=(mock_client, mock_auth_config))
        mocker.patch("clean_telegram.cli.start_client", return_value=mocker.AsyncMock())
        mocker.patch("clean_telegram.cli.clean_all_dialogs", return_value=0)

        await cli.main()

        mock_create.assert_called_once()
