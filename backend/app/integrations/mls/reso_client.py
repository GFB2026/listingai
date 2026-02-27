import re
from datetime import UTC, datetime, timedelta

import httpx

from app.core.encryption import decrypt_value

# Provider-specific path templates
_PROVIDER_PATHS = {
    "trestle": {
        "token": "/trestle/oidc/connect/token",
        "property": "/trestle/odata/Property",
        "media": "/trestle/odata/Media",
        "auth_type": "client_credentials",
    },
    "bridge": {
        "token": None,  # Bridge uses server token (no OAuth flow)
        "property": "/api/v2/OData/Property",
        "media": "/api/v2/OData/Media",
        "auth_type": "server_token",
    },
}


class RESOClient:
    """RESO Web API HTTP client supporting Trestle and Bridge Interactive providers."""

    def __init__(self, base_url: str, client_id: str, client_secret: str,
                 provider: str = "trestle", dataset: str = ""):
        self.base_url = base_url.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self.provider = provider.lower()
        self.access_token: str | None = None
        self.token_expires_at: datetime | None = None
        self._client = httpx.AsyncClient(timeout=30.0)

        if self.provider not in _PROVIDER_PATHS:
            raise ValueError(
                f"Unknown MLS provider: {self.provider}."
                " Use 'trestle' or 'bridge'."
            )

        paths = _PROVIDER_PATHS[self.provider]
        self._token_path = paths["token"]
        self._auth_type = paths["auth_type"]

        # Bridge paths include dataset ID (e.g., /api/v2/OData/test/Property)
        if self.provider == "bridge" and dataset:
            self._property_path = f"/api/v2/OData/{dataset}/Property"
            self._media_path = f"/api/v2/OData/{dataset}/Media"
        else:
            self._property_path = paths["property"]
            self._media_path = paths["media"]

    async def authenticate(self) -> str:
        """Obtain access token. Trestle uses OAuth2 client credentials; Bridge uses server token."""
        if self._auth_type == "server_token":
            # Bridge: the client_secret IS the server token
            self.access_token = self.client_secret
            self.token_expires_at = datetime.now(UTC) + timedelta(hours=24)
            return self.access_token

        # Trestle: OAuth2 client credentials grant
        response = await self._client.post(
            f"{self.base_url}{self._token_path}",
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
        self.token_expires_at = datetime.now(UTC) + timedelta(seconds=expires_in)

        return self.access_token

    async def _ensure_authenticated(self):
        if not self.access_token or (
            self.token_expires_at
            and datetime.now(UTC) >= self.token_expires_at
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
            f"{self.base_url}{self._property_path}",
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
            f"{self.base_url}{self._media_path}",
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
        settings = connection.settings or {}
        return cls(
            base_url=connection.base_url,
            client_id=decrypt_value(connection.client_id_encrypted),
            client_secret=decrypt_value(connection.client_secret_encrypted),
            provider=getattr(connection, "provider", "trestle") or "trestle",
            dataset=settings.get("dataset", ""),
        )
