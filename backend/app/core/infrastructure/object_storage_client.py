"""
Object storage client for MinIO/S3 uploads and pre-signed URLs.
"""
from __future__ import annotations

import importlib
from pathlib import Path
from typing import Optional
from urllib.parse import quote

from app.core.config.settings import get_settings

settings = get_settings()


def _local_root() -> Path:
    root = Path(settings.upload_dir)
    return root.resolve()


def _safe_local_path(bucket: str, key: str) -> Path:
    root = _local_root()
    candidate = (root / bucket / key).resolve()
    root_str = str(root)
    if not str(candidate).startswith(root_str):
        raise RuntimeError("Invalid object key path")
    return candidate


def is_configured() -> bool:
    return bool(settings.s3_access_key and settings.s3_secret_key)


def _client():
    if not is_configured():
        raise RuntimeError("S3_ACCESS_KEY/S3_SECRET_KEY are not configured")

    boto3 = importlib.import_module("boto3")
    kwargs = {
        "service_name": "s3",
        "aws_access_key_id": settings.s3_access_key,
        "aws_secret_access_key": settings.s3_secret_key,
        "region_name": settings.s3_region,
    }
    if settings.s3_endpoint_url:
        kwargs["endpoint_url"] = settings.s3_endpoint_url
    return boto3.client(**kwargs)


def upload_bytes(content: bytes, bucket: str, key: str, content_type: Optional[str] = None) -> str:
    if not is_configured():
        target = _safe_local_path(bucket, key)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return key

    client = _client()
    extra = {}
    if content_type:
        extra["ContentType"] = content_type
    client.put_object(Bucket=bucket, Key=key, Body=content, **extra)
    return key


def presigned_get_url(bucket: str, key: str, expires_in: Optional[int] = None) -> str:
    if not is_configured():
        return f"/api/v1/files/local/{quote(bucket, safe='')}/{quote(key, safe='/')}"

    client = _client()
    ttl = expires_in or settings.s3_presign_expiry_seconds
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=ttl,
    )


def get_local_file_path(bucket: str, key: str) -> Optional[str]:
    if is_configured():
        return None

    candidate = _safe_local_path(bucket, key)
    if not candidate.exists() or not candidate.is_file():
        return None
    return str(candidate)
