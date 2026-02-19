from fastapi import APIRouter

from app.api.v1 import (
    admin,
    auth,
    billing,
    brand_profiles,
    content,
    listings,
    media,
    tenants,
    users,
    webhooks,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(tenants.router, prefix="/tenants", tags=["Tenants"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(listings.router, prefix="/listings", tags=["Listings"])
api_router.include_router(content.router, prefix="/content", tags=["Content"])
api_router.include_router(brand_profiles.router, prefix="/brand-profiles", tags=["Brand Profiles"])
api_router.include_router(billing.router, prefix="/billing", tags=["Billing"])
api_router.include_router(media.router, prefix="/media", tags=["Media"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])
api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])
