import os
from pathlib import Path

import boto3
from botocore.client import Config

from app.core.config import settings


class LocalStorageService:
    def __init__(self, root: str):
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)
        print(f"Storage: using local filesystem at {self._root.resolve()}")

    def upload_bytes(self, key: str, data: bytes, content_type: str) -> str:
        path = self._root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key

    def download_bytes(self, key: str) -> bytes:
        return (self._root / key).read_bytes()

    def delete_object(self, key: str) -> None:
        path = self._root / key
        if path.exists():
            path.unlink()


class S3StorageService:
    def __init__(self):
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
            use_ssl=settings.s3_use_ssl,
            config=Config(
                signature_version="s3v4",
                connect_timeout=3,
                read_timeout=5,
                retries={"max_attempts": 1},
            ),
        )
        self._bucket = settings.s3_bucket
        self._ensure_bucket()
        print(f"Storage: using S3/MinIO at {settings.s3_endpoint_url}")

    def _ensure_bucket(self) -> None:
        try:
            self._client.head_bucket(Bucket=self._bucket)
        except Exception:
            self._client.create_bucket(Bucket=self._bucket)

    def upload_bytes(self, key: str, data: bytes, content_type: str) -> str:
        self._client.put_object(Bucket=self._bucket, Key=key, Body=data, ContentType=content_type)
        return key

    def download_bytes(self, key: str) -> bytes:
        response = self._client.get_object(Bucket=self._bucket, Key=key)
        return response["Body"].read()

    def delete_object(self, key: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=key)


_storage_service = None


def get_storage_service():
    global _storage_service
    if _storage_service is None:
        _storage_service = _create_storage_service()
    return _storage_service


def _create_storage_service():
    mode = settings.storage_backend.lower()
    if mode == "local":
        return LocalStorageService(settings.local_storage_dir)

    if mode == "s3":
        return S3StorageService()

    # auto: try S3, fall back to local disk for dev without Docker/MinIO
    try:
        return S3StorageService()
    except Exception as exc:
        print(f"Storage: MinIO/S3 unavailable ({exc}). Falling back to local disk.")
        return LocalStorageService(settings.local_storage_dir)


# Backwards-compatible alias — lazy, does not connect at import time
class _StorageProxy:
    def upload_bytes(self, key: str, data: bytes, content_type: str) -> str:
        return get_storage_service().upload_bytes(key, data, content_type)

    def download_bytes(self, key: str) -> bytes:
        return get_storage_service().download_bytes(key)

    def delete_object(self, key: str) -> None:
        return get_storage_service().delete_object(key)


storage_service = _StorageProxy()
