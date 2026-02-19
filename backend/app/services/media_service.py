import uuid

import boto3
from fastapi import UploadFile

from app.config import get_settings


class MediaService:
    def __init__(self):
        settings = get_settings()
        self.s3 = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
        )
        self.bucket = settings.s3_bucket_name

    async def upload(self, file: UploadFile, tenant_id: str) -> dict:
        file_id = str(uuid.uuid4())
        ext = file.filename.split(".")[-1] if file.filename else "bin"
        key = f"{tenant_id}/{file_id}.{ext}"

        contents = await file.read()
        self.s3.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=contents,
            ContentType=file.content_type or "application/octet-stream",
        )

        return {
            "media_id": file_id,
            "key": key,
            "filename": file.filename,
            "content_type": file.content_type,
            "size": len(contents),
        }

    async def get_presigned_url(self, media_id: str, tenant_id: str) -> dict:
        # List objects with prefix to find the file
        prefix = f"{tenant_id}/{media_id}"
        response = self.s3.list_objects_v2(Bucket=self.bucket, Prefix=prefix, MaxKeys=1)

        if not response.get("Contents"):
            return {"error": "File not found"}

        key = response["Contents"][0]["Key"]
        url = self.s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=3600,
        )

        return {"url": url, "media_id": media_id, "key": key}

    async def download_from_url(self, url: str, tenant_id: str, filename: str) -> dict:
        """Download a file from URL and store in S3 (used for MLS photo sync)."""
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()

        file_id = str(uuid.uuid4())
        ext = filename.split(".")[-1] if filename else "jpg"
        key = f"{tenant_id}/mls/{file_id}.{ext}"

        self.s3.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=response.content,
            ContentType=response.headers.get("content-type", "image/jpeg"),
        )

        return {"media_id": file_id, "key": key}
