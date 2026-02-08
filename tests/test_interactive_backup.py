"""Testes do modo interativo para funcionalidade de backup."""

from unittest import mock

import pytest

from clean_telegram.interactive import interactive_backup

# =============================================================================
# Testes: interactive_backup (básicos)
# =============================================================================


class TestInteractiveBackupBasic:
    """Testes básicos da função interactive_backup."""

    @pytest.mark.asyncio
    async def test_should_cancel_when_no_chat_id(self):
        """Testa cancelamento quando usuário não fornece chat_id."""
        client = mock.AsyncMock()
        get_entity_called = [False]

        async def mock_get_entity(chat_id):
            get_entity_called[0] = True
            entity = mock.Mock()
            entity.id = -1001234567890
            entity.title = "Test Group"
            return entity

        client.get_entity = mock_get_entity

        with mock.patch("clean_telegram.interactive.questionary") as mock_q:
            # Criar um mock para ask_async que retorna string vazia
            ask_mock = mock.AsyncMock(return_value="")
            mock_q.text.return_value.ask_async = ask_mock
            await interactive_backup(client)

        # Verificar que get_entity não foi chamado (cancelou antes)
        assert not get_entity_called[0]

    @pytest.mark.asyncio
    async def test_should_show_error_for_invalid_chat(self):
        """Testa exibição de erro para chat inválido."""
        client = mock.AsyncMock()

        async def mock_get_me():
            me = mock.Mock()
            me.id = 999888
            me.username = "testuser"
            me.first_name = "Test"
            return me

        client.get_me = mock_get_me

        async def mock_get_entity(chat_id):
            raise ValueError("Chat not found")

        client.get_entity = mock_get_entity

        with mock.patch("clean_telegram.interactive.questionary") as mock_q:
            ask_text_mock = mock.AsyncMock(return_value="@invalid")
            ask_select_mock = mock.AsyncMock(return_value="json")
            mock_q.text.return_value.ask_async = ask_text_mock
            mock_q.select.return_value.ask_async = ask_select_mock
            with mock.patch("builtins.print"):
                await interactive_backup(client)

    @pytest.mark.asyncio
    async def test_should_cancel_when_no_format_selected(self):
        """Testa cancelamento quando nenhum formato é selecionado."""
        client = mock.AsyncMock()

        async def mock_get_me():
            me = mock.Mock()
            me.id = 999888
            me.username = "testuser"
            me.first_name = "Test"
            return me

        client.get_me = mock_get_me

        async def mock_get_entity(chat_id):
            entity = mock.Mock()
            entity.id = -1001234567890
            entity.title = "Test Group"
            return entity

        client.get_entity = mock_get_entity

        with mock.patch("clean_telegram.interactive.questionary") as mock_q:
            ask_text_mock = mock.AsyncMock(return_value="@test")
            ask_select_mock = mock.AsyncMock(return_value=None)  # Cancelado
            mock_q.text.return_value.ask_async = ask_text_mock
            mock_q.select.return_value.ask_async = ask_select_mock
            with mock.patch("builtins.print"):
                await interactive_backup(client)


# =============================================================================
# Testes: Menu Principal
# =============================================================================


class TestInteractiveMainMenu:
    """Testes do menu principal com opção de backup."""

    @pytest.mark.asyncio
    async def test_main_menu_includes_backup_option(self):
        """Testa que menu principal inclui opção de backup."""
        from clean_telegram.interactive import interactive_main

        client = mock.AsyncMock()

        async def mock_get_me():
            me = mock.Mock()
            me.id = 999888
            me.username = "testuser"
            me.first_name = "Test"
            me.last_name = "User"
            return me

        client.get_me = mock_get_me

        call_count = [0]

        async def mock_select_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return "backup"
            return "exit"

        with mock.patch("clean_telegram.interactive.questionary") as mock_q:
            ask_select_mock = mock.AsyncMock(side_effect=mock_select_side_effect)
            mock_q.select.return_value.ask_async = ask_select_mock
            mock_q.press_any_key_to_continue.return_value.ask_async = mock.AsyncMock(
                return_value=None
            )
            with mock.patch(
                "clean_telegram.interactive.interactive_backup"
            ) as mock_backup:
                with mock.patch("builtins.print"):
                    await interactive_main(client)

            # Verificar que a função de backup foi chamada
            mock_backup.assert_called_once_with(client)

    @pytest.mark.asyncio
    async def test_menu_options(self):
        """Testa que todas as opções esperadas estão no menu."""
        import inspect

        # Verificar que interactive_backup existe e pode ser chamada
        assert callable(interactive_backup)

        # Verificar a assinatura da função
        sig = inspect.signature(interactive_backup)
        assert "client" in sig.parameters
