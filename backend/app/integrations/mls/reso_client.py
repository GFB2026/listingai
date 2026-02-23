import re
from datetime import datetime, timedelta, timezone

import httpx

from app.core.encryption import decrypt_value, encrypt_value


class RESOClient:
    """RESO Web API HTTP client with OAuth2 client credentials flow."""

    def __init__(self, base_url: str, client_id: str, client_secret: str):
        self.base_url = base_url.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token: str | None = None
        self.token_expires_at: datetime | None = None
        self._client = httpx.AsyncClient(timeout=30.0)

    async def authenticate(self) -> str:
        """Obtain OAuth2 access token via client credentials grant."""
        response = await self._client.post(
            f"{self.base_url}/trestle/oidc/connect/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": "api",
            },
        )
        response.raise_for_status()
        data = response.json()

        self.access_token = data["access_token"]
        expires_in = data.get("expires_in", 3600)
        self.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        return self.access_token

    async def _ensure_authenticated(self):
        if not self.access_token or (
            self.token_expires_at
            and datetime.now(timezone.utc) >= self.token_expires_at
        ):
            await self.authenticate()

    async def get_properties(
        self,
        filter_query: str | None = None,
        select_fields: str | None = None,
        top: int = 200,
        skip: int = 0,
    ) -> dict:
        """Query the Property resource with OData parameters."""
        await self._ensure_authenticated()

        params = {"$top": top, "$skip": skip}
        if filter_query:
            params["$filter"] = filter_query
        if select_fields:
            params["$select"] = select_fields

        response = await self._client.get(
            f"{self.base_url}/trestle/odata/Property",
            params=params,
            headers={"Authorization": f"Bearer {self.access_token}"},
        )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _escape_odata_string(value: str) -> str:
        """Escape single quotes for OData string literals."""
        return value.replace("'", "''")

    async def get_media(self, resource_key: str) -> dict:
        """Get media (photos) for a listing."""
        await self._ensure_authenticated()

        # Validate resource_key format (alphanumeric + hyphens only)
        if not re.match(r"^[A-Za-z0-9\-_]+$", resource_key):
            raise ValueError(f"Invalid resource key format: {resource_key}")

        safe_key = self._escape_odata_string(resource_key)
        response = await self._client.get(
            f"{self.base_url}/trestle/odata/Media",
            params={
                "$filter": f"ResourceRecordKey eq '{safe_key}'",
                "$orderby": "Order",
            },
            headers={"Authorization": f"Bearer {self.access_token}"},
        )
        response.raise_for_status()
        return response.json()

    async def close(self):
        await self._client.aclose()

    @classmethod
    def from_connection(cls, connection) -> "RESOClient":
        """Create a client from an MLSConnection model instance."""
        return cls(
            base_url=connection.base_url,
            client_id=decrypt_value(connection.client_id_encrypted),
            client_secret=decrypt_value(connection.client_secret_encrypted),
        )
