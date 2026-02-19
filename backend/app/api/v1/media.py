from fastapi import APIRouter, Depends, UploadFile, File

from app.api.deps import get_current_user
from app.models.user import User
from app.services.media_service import MediaService

router = APIRouter()


@router.post("/upload")
async def upload_media(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    media_service = MediaService()
    result = await media_service.upload(
        file=file,
        tenant_id=str(user.tenant_id),
    )
    return result


@router.get("/{media_id}")
async def get_media(
    media_id: str,
    user: User = Depends(get_current_user),
):
    media_service = MediaService()
    return await media_service.get_presigned_url(media_id, str(user.tenant_id))
