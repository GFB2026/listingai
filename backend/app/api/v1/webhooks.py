import stripe
from fastapi import APIRouter, HTTPException, Request

from app.config import get_settings

router = APIRouter()


@router.post("/stripe")
async def stripe_webhook(request: Request):
    settings = get_settings()
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Handle events
    if event["type"] == "customer.subscription.created":
        pass  # TODO: Update tenant plan
    elif event["type"] == "customer.subscription.updated":
        pass  # TODO: Update tenant plan/limits
    elif event["type"] == "customer.subscription.deleted":
        pass  # TODO: Downgrade tenant to free
    elif event["type"] == "invoice.payment_succeeded":
        pass  # TODO: Record payment
    elif event["type"] == "invoice.payment_failed":
        pass  # TODO: Notify tenant

    return {"status": "ok"}
