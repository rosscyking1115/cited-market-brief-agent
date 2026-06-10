"""Raw source storage abstraction (plan §7 step 3: raw documents stored separately
from normalized chunks).

Keys are per-tenant prefixed: {org_id}/{sha256}/{filename} — mirrors the production
S3 layout (per-tenant prefix + IAM conditions, plan §9) so dev and prod paths match.
"""

import hashlib
from pathlib import Path
from typing import Protocol

from app.core.config import settings


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class RawStore(Protocol):
    def put(self, org_id: str, filename: str, data: bytes) -> tuple[str, str]:
        """Store raw bytes. Returns (object_key, sha256 checksum)."""
        ...

    def get(self, object_key: str) -> bytes: ...


class LocalRawStore:
    """Filesystem store for local development."""

    def __init__(self, root: str | None = None) -> None:
        self._root = Path(root or settings.raw_store_path)

    def put(self, org_id: str, filename: str, data: bytes) -> tuple[str, str]:
        checksum = sha256_hex(data)
        key = f"{org_id}/{checksum}/{filename}"
        path = self._root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key, checksum

    def get(self, object_key: str) -> bytes:
        return (self._root / object_key).read_bytes()


class S3RawStore:
    """S3/MinIO store (requires the 's3' extra). Lazy import keeps boto3 optional in dev."""

    def __init__(self) -> None:
        import boto3  # noqa: PLC0415

        self._bucket = settings.s3_bucket_raw
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url or None,
            aws_access_key_id=settings.s3_access_key or None,
            aws_secret_access_key=settings.s3_secret_key or None,
        )

    def put(self, org_id: str, filename: str, data: bytes) -> tuple[str, str]:
        checksum = sha256_hex(data)
        key = f"{org_id}/{checksum}/{filename}"
        self._client.put_object(Bucket=self._bucket, Key=key, Body=data)
        return key, checksum

    def get(self, object_key: str) -> bytes:
        resp = self._client.get_object(Bucket=self._bucket, Key=object_key)
        return resp["Body"].read()


def get_raw_store() -> RawStore:
    if settings.raw_store_backend == "s3":
        return S3RawStore()
    return LocalRawStore()
