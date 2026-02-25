"""Email delivery service using SendGrid.

Ported from gor-marketing's email_sender.py and adapted for multi-tenant
SaaS operation. Supports:
- Per-tenant sender identity (from brand profile or settings)
- BCC-style personalizations (recipients don't see each other)
- Batch sending (1000 recipients per SendGrid request)
- DB-backed campaign tracking via EmailCampaign model
- Agent notification emails
"""

from uuid import UUID

import httpx
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.email_campaign import EmailCampaign

logger = structlog.get_logger()

SENDGRID_API_URL = "https://api.sendgrid.com/v3/mail/send"


def _canspam_footer(
    physical_address: str,
    unsubscribe_url: str | None = None,
    brokerage_name: str | None = None,
) -> str:
    """Build a CAN-SPAM compliant footer with physical address and unsubscribe link.

    CAN-SPAM requires: (1) physical postal address and (2) opt-out mechanism
    in every commercial email.
    """
    name_line = f"{brokerage_name} &bull; " if brokerage_name else ""
    unsub = (
        f'<a href="{unsubscribe_url}" style="color:#999999;text-decoration:underline;">Unsubscribe</a>'
        if unsubscribe_url
        else '<a href="mailto:{from_email}?subject=Unsubscribe" style="color:#999999;text-decoration:underline;">Unsubscribe</a>'
    )
    return f"""\
<div style="margin-top:24px;padding:16px 0;border-top:1px solid #eeeeee;text-align:center;font-size:10px;color:#777777;font-family:Arial,Helvetica,sans-serif;">
  <div>{name_line}{physical_address}</div>
  <div style="margin-top:4px;">{unsub} from future emails.</div>
</div>"""


class EmailService:
    """SendGrid email delivery for listing marketing campaigns."""

    def __init__(
        self,
        api_key: str | None = None,
        from_email: str | None = None,
        from_name: str | None = None,
    ):
        settings = get_settings()
        self.api_key = api_key or settings.sendgrid_api_key
        self.from_email = from_email or settings.sendgrid_default_from_email
        self.from_name = from_name or settings.sendgrid_default_from_name

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def send(
        self,
        to_emails: list[str],
        subject: str,
        html_content: str,
        reply_to: str | None = None,
        physical_address: str | None = None,
        unsubscribe_url: str | None = None,
    ) -> dict:
        """Send an HTML email to one or more recipients.

        Uses per-recipient personalizations so recipients don't see each other.
        When physical_address is provided, a CAN-SPAM compliant footer is
        automatically appended to the HTML content.

        Returns:
            {"sent": int, "failed": int, "errors": list[str]}
        """
        if not self.api_key:
            return {"sent": 0, "failed": 0, "errors": ["SendGrid API key not configured"]}

        if not to_emails:
            return {"sent": 0, "failed": 0, "errors": ["No recipients"]}

        # Auto-append CAN-SPAM footer when physical address is provided
        if physical_address:
            footer = _canspam_footer(
                physical_address=physical_address,
                unsubscribe_url=unsubscribe_url,
                brokerage_name=self.from_name,
            )
            # Insert before closing </body> or </div>, or just append
            if "</body>" in html_content.lower():
                idx = html_content.lower().rfind("</body>")
                html_content = html_content[:idx] + footer + html_content[idx:]
            else:
                html_content += footer

        personalizations = [
            {"to": [{"email": addr.strip()}]}
            for addr in to_emails
            if addr.strip()
        ]

        if not personalizations:
            return {"sent": 0, "failed": 0, "errors": ["No valid recipients"]}

        results = {"sent": 0, "failed": 0, "errors": []}
        batch_size = 1000

        for i in range(0, len(personalizations), batch_size):
            batch = personalizations[i:i + batch_size]
            payload = {
                "personalizations": batch,
                "from": {"email": self.from_email, "name": self.from_name},
                "subject": subject,
                "content": [{"type": "text/html", "value": html_content}],
            }

            if reply_to:
                payload["reply_to"] = {"email": reply_to}

            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        SENDGRID_API_URL,
                        json=payload,
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json",
                        },
                        timeout=30.0,
                    )

                if resp.status_code in (200, 201, 202):
                    results["sent"] += len(batch)
                else:
                    results["failed"] += len(batch)
                    try:
                        error_body = resp.json()
                        for err in error_body.get("errors", []):
                            results["errors"].append(err.get("message", str(err)))
                    except Exception:
                        results["errors"].append(f"HTTP {resp.status_code}: {resp.text[:200]}")
            except httpx.TimeoutException:
                results["failed"] += len(batch)
                results["errors"].append("SendGrid request timed out")
                logger.warning("sendgrid_timeout", batch_index=i, batch_size=len(batch))
            except httpx.ConnectError as e:
                results["failed"] += len(batch)
                results["errors"].append(f"SendGrid connection error: {e}")
                logger.warning("sendgrid_connect_error", error=str(e))

        return results

    async def send_and_track(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        to_emails: list[str],
        subject: str,
        html_content: str,
        campaign_type: str,
        reply_to: str | None = None,
        content_id: UUID | None = None,
        listing_id: UUID | None = None,
        user_id: UUID | None = None,
        physical_address: str | None = None,
        unsubscribe_url: str | None = None,
    ) -> EmailCampaign:
        """Send email and persist a campaign record for audit/analytics.

        Returns:
            The created EmailCampaign record.
        """
        results = await self.send(
            to_emails=to_emails,
            subject=subject,
            html_content=html_content,
            reply_to=reply_to,
            physical_address=physical_address,
            unsubscribe_url=unsubscribe_url,
        )

        campaign = EmailCampaign(
            tenant_id=tenant_id,
            content_id=content_id,
            listing_id=listing_id,
            user_id=user_id,
            subject=subject,
            from_email=self.from_email,
            from_name=self.from_name,
            reply_to=reply_to,
            recipient_count=len(to_emails),
            sent=results["sent"],
            failed=results["failed"],
            errors=results["errors"],
            campaign_type=campaign_type,
        )
        db.add(campaign)

        log = logger.bind(campaign_type=campaign_type, recipients=len(to_emails))
        if results["failed"]:
            log.warning("email_send_partial", sent=results["sent"], failed=results["failed"])
        else:
            log.info("email_sent", sent=results["sent"])

        return campaign

    async def send_agent_notification(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        agent_email: str,
        agent_name: str,
        address: str,
        content_types: list[str],
        brokerage_name: str | None = None,
        user_id: UUID | None = None,
        listing_id: UUID | None = None,
    ) -> EmailCampaign:
        """Notify a listing agent that their marketing materials are ready.

        Returns:
            The created EmailCampaign record.
        """
        brokerage = brokerage_name or self.from_name

        type_labels = {
            "listing_description": "Listing Description",
            "social_instagram": "Instagram Post",
            "social_facebook": "Facebook Post",
            "social_linkedin": "LinkedIn Post",
            "social_x": "X (Twitter) Post",
            "email_just_listed": "Just Listed Email",
            "email_open_house": "Open House Email",
            "email_drip": "Drip Campaign Email",
            "flyer": "Print Flyer",
            "video_script": "Video Script",
            "open_house_invite": "Open House Invitation",
            "price_reduction": "Price Reduction Announcement",
            "just_sold": "Just Sold Announcement",
        }

        items_html = "".join(
            f"<li>{type_labels.get(ct, ct)}</li>" for ct in content_types
        )
        greeting = f"Hi {agent_name}," if agent_name else "Hi,"
        subject = f"Your listing materials are ready — {address}"

        html_content = f"""\
<div style="font-family: Arial, Helvetica, sans-serif; color: #333; max-width: 600px;">
  <p>{greeting}</p>
  <p>Great news — your marketing materials for <strong>{address}</strong> are ready!</p>
  <p>Here's what was generated:</p>
  <ul>{items_html}</ul>
  <p>Please log in to review and access your materials.</p>
  <br>
  <p style="color: #555;">— {brokerage} Marketing</p>
</div>
"""

        return await self.send_and_track(
            db=db,
            tenant_id=tenant_id,
            to_emails=[agent_email],
            subject=subject,
            html_content=html_content,
            campaign_type="agent_notify",
            user_id=user_id,
            listing_id=listing_id,
        )


def parse_subject_from_email(email_text: str) -> str:
    """Extract subject line from AI-generated email text.

    Looks for a "Subject: ..." line in the generated content.
    Falls back to a generic subject if none found.
    """
    for line in email_text.split("\n"):
        stripped = line.strip()
        if stripped.lower().startswith("subject:"):
            return stripped[len("subject:"):].strip()
    return "New Listing Available"
