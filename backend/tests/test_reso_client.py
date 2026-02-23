"""Tests for RESO Web API client."""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.integrations.mls.reso_client import RESOClient


class TestAuthenticate:
    @pytest.mark.asyncio
    async def test_authenticate_success(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "tok_abc",
            "expires_in": 3600,
        }
        mock_response.raise_for_status = MagicMock()

        client = RESOClient("https://api.example.com", "id", "secret")
        client._client = AsyncMock()
        client._client.post = AsyncMock(return_value=mock_response)

        token = await client.authenticate()

        assert token == "tok_abc"
        assert client.access_token == "tok_abc"
        assert client.token_expires_at is not None
        await client.close()

    @pytest.mark.asyncio
    async def test_token_expiry_triggers_reauthentication(self):
        client = RESOClient("https://api.example.com", "id", "secret")
        client._client = AsyncMock()

        # Set expired token
        client.access_token = "old_token"
        client.token_expires_at = datetime.now(timezone.utc) - timedelta(seconds=10)

        auth_response = MagicMock()
        auth_response.json.return_value = {"access_token": "new_tok", "expires_in": 3600}
        auth_response.raise_for_status = MagicMock()
        client._client.post = AsyncMock(return_value=auth_response)

        get_response = MagicMock()
        get_response.json.return_value = {"value": []}
        get_response.raise_for_status = MagicMock()
        client._client.get = AsyncMock(return_value=get_response)

        result = await client.get_properties()

        assert client.access_token == "new_tok"
        assert result == {"value": []}
        await client.close()


class TestGetProperties:
    @pytest.mark.asyncio
    async def test_get_properties(self):
        client = RESOClient("https://api.example.com", "id", "secret")
        client._client = AsyncMock()
        client.access_token = "tok"
        client.token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        mock_response = MagicMock()
        mock_response.json.return_value = {"value": [{"ListingKey": "A1"}]}
        mock_response.raise_for_status = MagicMock()
        client._client.get = AsyncMock(return_value=mock_response)

        result = await client.get_properties(filter_query="ListPrice gt 100000", top=10)

        assert len(result["value"]) == 1
        call_kwargs = client._client.get.call_args
        assert call_kwargs.kwargs["params"]["$filter"] == "ListPrice gt 100000"
        assert call_kwargs.kwargs["params"]["$top"] == 10
        await client.close()

    @pytest.mark.asyncio
    async def test_get_properties_with_select(self):
        client = RESOClient("https://api.example.com", "id", "secret")
        client._client = AsyncMock()
        client.access_token = "tok"
        client.token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        mock_response = MagicMock()
        mock_response.json.return_value = {"value": []}
        mock_response.raise_for_status = MagicMock()
        client._client.get = AsyncMock(return_value=mock_response)

        await client.get_properties(select_fields="ListingKey,ListPrice")

        call_kwargs = client._client.get.call_args
        assert call_kwargs.kwargs["params"]["$select"] == "ListingKey,ListPrice"
        await client.close()


class TestGetMedia:
    @pytest.mark.asyncio
    async def test_get_media(self):
        client = RESOClient("https://api.example.com", "id", "secret")
        client._client = AsyncMock()
        client.access_token = "tok"
        client.token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "value": [{"MediaURL": "https://photos.example.com/1.jpg"}]
        }
        mock_response.raise_for_status = MagicMock()
        client._client.get = AsyncMock(return_value=mock_response)

        result = await client.get_media("ABC-123")

        assert len(result["value"]) == 1
        await client.close()

    @pytest.mark.asyncio
    async def test_get_media_invalid_key(self):
        client = RESOClient("https://api.example.com", "id", "secret")
        client._client = AsyncMock()
        client.access_token = "tok"
        client.token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        with pytest.raises(ValueError, match="Invalid resource key"):
            await client.get_media("invalid key with spaces!")

        await client.close()


class TestODataEscape:
    def test_escape_single_quotes(self):
        assert RESOClient._escape_odata_string("O'Brien") == "O''Brien"

    def test_no_quotes(self):
        assert RESOClient._escape_odata_string("normal") == "normal"


class TestFromConnection:
    def test_from_connection(self):
        mock_conn = MagicMock()
        mock_conn.base_url = "https://api.example.com"
        mock_conn.client_id_encrypted = b"enc_id"
        mock_conn.client_secret_encrypted = b"enc_secret"

        with patch(
            "app.integrations.mls.reso_client.decrypt_value",
            side_effect=["my_id", "my_secret"],
        ):
            client = RESOClient.from_connection(mock_conn)

        assert client.client_id == "my_id"
        assert client.client_secret == "my_secret"
        assert client.base_url == "https://api.example.com"
