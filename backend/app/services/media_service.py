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

    async def upload_validated(
        self, contents: bytes, filename: str,
        content_type: str, tenant_id: str,
    ) -> dict:
        """Upload pre-validated file contents to S3."""
        ext_map = {
            "image/jpeg": "jpg",
            "image/png": "png",
            "image/webp": "webp",
            "application/pdf": "pdf",
        }
        ext = ext_map.get(content_type, "bin")
        key = f"{tenant_id}/{filename}.{ext}"

        self.s3.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=contents,
            ContentType=content_type,
        )

        return {
            "media_id": filename,
            "key": key,
            "content_type": content_type,
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

    _MAX_DOWNLOAD_SIZE = 20 * 1024 * 1024  # 20 MB

    async def download_from_url(self, url: str, tenant_id: str, filename: str) -> dict:
        """Download a file from URL and store in S3 (used for MLS photo sync)."""
        import httpx

        timeout = httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=10.0)
        async with (
            httpx.AsyncClient(timeout=timeout) as client,
            client.stream("GET", url) as response,
        ):
                response.raise_for_status()

                content_length = response.headers.get("content-length")
                if content_length and int(content_length) > self._MAX_DOWNLOAD_SIZE:
                    raise ValueError(f"File too large: {content_length} bytes")

                chunks = []
                total = 0
                async for chunk in response.aiter_bytes(8192):
                    total += len(chunk)
                    if total > self._MAX_DOWNLOAD_SIZE:
                        raise ValueError(f"File exceeds {self._MAX_DOWNLOAD_SIZE} byte limit")
                    chunks.append(chunk)

                content = b"".join(chunks)
                content_type = response.headers.get("content-type", "image/jpeg")

        file_id = str(uuid.uuid4())
        ext = filename.split(".")[-1] if filename else "jpg"
        key = f"{tenant_id}/mls/{file_id}.{ext}"

        self.s3.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=content,
            ContentType=content_type,
        )

        return {"media_id": file_id, "key": key}
