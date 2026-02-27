"""Social media posting via Meta Graph API (Facebook + Instagram).

Ported from gor-marketing's social_poster.py and adapted for multi-tenant
SaaS operation. Per-tenant credentials are stored in tenant.settings JSONB:

    tenant.settings = {
        "social": {
            "page_access_token": "...",
            "facebook_page_id": "...",
            "instagram_user_id": "..."   // optional
        }
    }

Supports:
- Facebook Page posts (text, link, or photo)
- Instagram Business posts (photo + caption, two-step container flow)
- DB-backed post tracking via SocialPost model
- Structured logging for observability
"""

from uuid import UUID

import httpx
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.social_post import SocialPost

logger = structlog.get_logger()

GRAPH_API_BASE = "https://graph.facebook.com/v21.0"

_IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}


async def validate_photo_url(url: str) -> dict:
    """Validate that a photo URL is reachable and returns an image.

    Performs a lightweight HEAD request to check accessibility and content type
    before sending to the Meta Graph API, which gives opaque errors on bad URLs.

    Returns:
        {"valid": bool, "error": str | None}
    """
    if not url:
        return {"valid": False, "error": "Photo URL is empty"}
    if not url.startswith(("http://", "https://")):
        return {
            "valid": False,
            "error": (
                "Photo URL must start with http:// or"
                f" https://, got '{url[:50]}'"
            ),
        }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.head(url, follow_redirects=True, timeout=10.0)
        if resp.status_code >= 400:
            return {"valid": False, "error": f"Photo URL returned HTTP {resp.status_code}"}
        content_type = resp.headers.get("content-type", "").split(";")[0].strip().lower()
        if content_type and content_type not in _IMAGE_CONTENT_TYPES:
            return {
                "valid": False,
                "error": (
                    f"Photo URL content-type is"
                    f" '{content_type}', expected an image"
                ),
            }
        return {"valid": True, "error": None}
    except httpx.TimeoutException:
        return {"valid": False, "error": "Photo URL validation timed out"}
    except httpx.ConnectError as e:
        return {"valid": False, "error": f"Photo URL not reachable: {e}"}
    except httpx.HTTPError as e:
        return {"valid": False, "error": f"Photo URL validation failed: {e}"}


class SocialService:
    """Meta Graph API client for Facebook Pages and Instagram Business."""

    def __init__(
        self,
        page_access_token: str,
        page_id: str,
        ig_user_id: str | None = None,
    ):
        self.token = page_access_token
        self.page_id = page_id
        self.ig_user_id = ig_user_id

    @classmethod
    def from_tenant_settings(cls, settings: dict) -> "SocialService | None":
        """Create a SocialService from tenant.settings JSONB.

        Returns None if social credentials are not configured.
        """
        social = settings.get("social", {})
        token = social.get("page_access_token", "")
        page_id = social.get("facebook_page_id", "")
        if not token or not page_id:
            return None
        return cls(
            page_access_token=token,
            page_id=page_id,
            ig_user_id=social.get("instagram_user_id") or None,
        )

    @property
    def has_instagram(self) -> bool:
        return bool(self.ig_user_id)

    # ── Facebook Page ─────────────────────────────────────────────

    async def post_to_facebook(
        self,
        message: str,
        link: str | None = None,
        photo_url: str | None = None,
    ) -> dict:
        """Publish a post to the Facebook Page.

        Returns:
            {"success": bool, "post_id": str | None, "error": str | None}
        """
        try:
            async with httpx.AsyncClient() as client:
                if photo_url:
                    resp = await client.post(
                        f"{GRAPH_API_BASE}/{self.page_id}/photos",
                        data={
                            "caption": message,
                            "url": photo_url,
                            "access_token": self.token,
                        },
                        timeout=60.0,
                    )
                else:
                    data = {
                        "message": message,
                        "access_token": self.token,
                    }
                    if link:
                        data["link"] = link
                    resp = await client.post(
                        f"{GRAPH_API_BASE}/{self.page_id}/feed",
                        data=data,
                        timeout=30.0,
                    )

                body = resp.json()
                if "id" in body:
                    return {"success": True, "post_id": body["id"], "error": None}
                error = body.get("error", {}).get("message", str(body))
                return {"success": False, "post_id": None, "error": error}
        except httpx.TimeoutException:
            return {"success": False, "post_id": None, "error": "Facebook API request timed out"}
        except httpx.ConnectError as e:
            return {
                "success": False,
                "post_id": None,
                "error": f"Facebook API connection error: {e}",
            }

    # ── Instagram Business ────────────────────────────────────────

    async def post_to_instagram(
        self,
        caption: str,
        image_url: str,
    ) -> dict:
        """Publish a photo post to Instagram Business (two-step container flow).

        Returns:
            {"success": bool, "post_id": str | None, "error": str | None}
        """
        if not self.ig_user_id:
            return {"success": False, "post_id": None,
                    "error": "Instagram user ID not configured"}

        try:
            async with httpx.AsyncClient() as client:
                # Step 1: Create media container
                resp = await client.post(
                    f"{GRAPH_API_BASE}/{self.ig_user_id}/media",
                    data={
                        "image_url": image_url,
                        "caption": caption,
                        "access_token": self.token,
                    },
                    timeout=30.0,
                )
                body = resp.json()

                if "id" not in body:
                    error = body.get("error", {}).get("message", str(body))
                    return {"success": False, "post_id": None, "error": error}

                container_id = body["id"]

                # Step 2: Publish the container
                resp = await client.post(
                    f"{GRAPH_API_BASE}/{self.ig_user_id}/media_publish",
                    data={
                        "creation_id": container_id,
                        "access_token": self.token,
                    },
                    timeout=30.0,
                )
                body = resp.json()

                if "id" in body:
                    return {"success": True, "post_id": body["id"], "error": None}
                error = body.get("error", {}).get("message", str(body))
                return {"success": False, "post_id": None, "error": error}
        except httpx.TimeoutException:
            return {"success": False, "post_id": None, "error": "Instagram API request timed out"}
        except httpx.ConnectError as e:
            return {
                "success": False,
                "post_id": None,
                "error": f"Instagram API connection error: {e}",
            }

    # ── Convenience ───────────────────────────────────────────────

    async def post_listing(
        self,
        fb_text: str | None = None,
        ig_text: str | None = None,
        photo_url: str | None = None,
        listing_link: str | None = None,
    ) -> dict:
        """Post a listing to all configured platforms.

        Validates the photo URL before attempting any platform posts.

        Returns:
            {"facebook": result_dict, "instagram": result_dict}
        """
        # Validate photo URL upfront to give clear errors instead of opaque API failures
        validated_photo = photo_url
        if photo_url:
            check = await validate_photo_url(photo_url)
            if not check["valid"]:
                logger.warning("photo_url_invalid", url=photo_url[:100], error=check["error"])
                validated_photo = None

        results = {}

        if fb_text:
            results["facebook"] = await self.post_to_facebook(
                message=fb_text,
                link=listing_link,
                photo_url=validated_photo,
            )
            if photo_url and not validated_photo and results["facebook"]["success"]:
                results["facebook"]["warning"] = f"Photo skipped: {check['error']}"
        else:
            results["facebook"] = {"success": False, "post_id": None,
                                   "error": "No Facebook content"}

        if ig_text and validated_photo and self.ig_user_id:
            results["instagram"] = await self.post_to_instagram(
                caption=ig_text,
                image_url=validated_photo,
            )
        elif ig_text and photo_url and not validated_photo:
            results["instagram"] = {"success": False, "post_id": None,
                                    "error": f"Photo validation failed: {check['error']}"}
        elif ig_text and not photo_url:
            results["instagram"] = {"success": False, "post_id": None,
                                    "error": "Instagram requires a photo URL"}
        elif not self.ig_user_id:
            results["instagram"] = {"success": False, "post_id": None,
                                    "error": "Instagram user ID not configured"}
        else:
            results["instagram"] = {"success": False, "post_id": None,
                                    "error": "No Instagram content"}

        return results

    async def post_and_track(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        fb_text: str | None = None,
        ig_text: str | None = None,
        photo_url: str | None = None,
        listing_link: str | None = None,
        content_id: UUID | None = None,
        listing_id: UUID | None = None,
        user_id: UUID | None = None,
    ) -> list[SocialPost]:
        """Post to all platforms and persist SocialPost records.

        Returns:
            List of created SocialPost records.
        """
        results = await self.post_listing(
            fb_text=fb_text,
            ig_text=ig_text,
            photo_url=photo_url,
            listing_link=listing_link,
        )

        posts = []
        for platform, result in results.items():
            post = SocialPost(
                tenant_id=tenant_id,
                content_id=content_id,
                listing_id=listing_id,
                user_id=user_id,
                platform=platform,
                body=fb_text if platform == "facebook" else ig_text,
                photo_url=photo_url,
                link_url=listing_link,
                status="success" if result["success"] else "failed",
                platform_post_id=result.get("post_id"),
                error=result.get("error"),
            )
            db.add(post)
            posts.append(post)

            log = logger.bind(platform=platform, tenant_id=str(tenant_id))
            if result["success"]:
                log.info("social_posted", post_id=result["post_id"])
            elif result["error"]:
                log.warning("social_post_failed", error=result["error"])

        return posts
