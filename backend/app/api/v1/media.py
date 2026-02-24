import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.config import get_settings
from app.models.user import User
from app.services.media_service import MediaService

router = APIRouter()


class MediaUploadResponse(BaseModel):
    media_id: str
    key: str
    content_type: str
    size: int


class MediaPresignedResponse(BaseModel):
    url: str | None = None
    media_id: str
    key: str | None = None
    error: str | None = None

ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "application/pdf",
}

# Magic byte signatures
MAGIC_BYTES = {
    "image/jpeg": [b"\xff\xd8"],
    "image/png": [b"\x89\x50\x4e\x47"],
    "image/webp": [b"RIFF"],  # Full check includes WEBP at offset 8
}


def _validate_magic_bytes(content_type: str, data: bytes) -> bool:
    """Validate file content matches its declared MIME type via magic bytes."""
    signatures = MAGIC_BYTES.get(content_type)
    if signatures is None:
        # No magic byte check for this type (e.g. PDF)
        return True
    for sig in signatures:
        if data[:len(sig)] == sig:
            # Extra check for WebP: bytes 8-12 must be "WEBP"
            return not (content_type == "image/webp" and data[8:12] != b"WEBP")
    return False


@router.post("/upload", response_model=MediaUploadResponse)
async def upload_media(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    # Read file contents
    contents = await file.read()

    # Check file size
    max_size = get_settings().max_upload_file_size
    if len(contents) > max_size:
        max_mb = max_size // (1024 * 1024)
        raise HTTPException(
            status_code=400, detail=f"File too large. Maximum size is {max_mb}MB."
        )

    # Check MIME type
    content_type = file.content_type or "application/octet-stream"
    if content_type not in ALLOWED_MIME_TYPES:
        allowed = ", ".join(sorted(ALLOWED_MIME_TYPES))
        raise HTTPException(
            status_code=400,
            detail=f"File type '{content_type}' not allowed. Allowed types: {allowed}",
        )

    # Validate magic bytes
    if not _validate_magic_bytes(content_type, contents):
        raise HTTPException(status_code=400, detail="File content does not match declared type.")

    # Generate safe filename (no user input in path)
    safe_filename = f"{uuid.uuid4()}"

    media_service = MediaService()
    result = await media_service.upload_validated(
        contents=contents,
        filename=safe_filename,
        content_type=content_type,
        tenant_id=str(user.tenant_id),
    )
    return result


@router.get("/{media_id}", response_model=MediaPresignedResponse)
async def get_media(
    media_id: str,
    user: User = Depends(get_current_user),
):
    media_service = MediaService()
    return await media_service.get_presigned_url(media_id, str(user.tenant_id))
