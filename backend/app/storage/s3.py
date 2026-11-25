"""Object storage on Cloudflare R2 through its S3-compatible API.

What this is for
----------------
The production document store can be Cloudflare R2 instead of Oracle Object
Storage: ``STORAGE_BACKEND=s3`` plus the ``R2_*`` settings in
:mod:`app.core.config` selects this backend. R2 speaks the S3 API, so the
implementation uses ``boto3`` pointed at the R2 endpoint URL rather than a
vendor SDK.

The verification contract
-------------------------
The checksum contract from :mod:`app.storage.backends` holds here too: the
SHA-256 of the payload is stored as S3 object metadata
(``sha256``, shared as :data:`CHECKSUM_METADATA_KEY`) and
:meth:`S3CompatibleStorage.checksum` reads it back without downloading the
object. :meth:`StorageBackend.save_verified` (inherited unchanged) compares
the two and raises :class:`ChecksumMismatch` when they differ.

The R2 bucket is assumed private. :meth:`url_for` therefore returns a
presigned ``GET`` URL (default expiry one hour), never a public URL.
"""
from __future__ import annotations

from app.core.observability import get_logger
from app.storage.backends import (
    CHECKSUM_METADATA_KEY,
    StorageBackend,
    StorageError,
    checksum,
)

log = get_logger("librepeople.storage.s3")

#: How long a presigned download URL stays valid, in seconds (one hour).
DEFAULT_URL_EXPIRY_SECONDS = 3600

#: An upload larger than this is refused before it reaches the network.
#: 25 MB covers CSV imports, generated PDFs and scanned onboarding documents.
MAX_OBJECT_BYTES = 25 * 1024 * 1024


class S3CompatibleStorage(StorageBackend):
    """An S3-API object store (Cloudflare R2) holding private documents."""

    def __init__(
        self,
        endpoint_url: str | None,
        bucket: str,
        access_key_id: str,
        secret_access_key: str,
        region: str = "auto",
        url_expiry_seconds: int = DEFAULT_URL_EXPIRY_SECONDS,
    ):
        import boto3  # lazy import: only the s3 backend needs boto3

        if not bucket:
            raise StorageError("The S3 backend needs a bucket name.")
        self.bucket = bucket
        self.url_expiry_seconds = url_expiry_seconds
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name=region,
        )

    def _validate(
        self, key: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> None:
        if not key or key.startswith("/"):
            raise StorageError("The storage key must be a non-empty relative path.")
        if len(data) > MAX_OBJECT_BYTES:
            raise StorageError(
                f"The object is {len(data)} bytes; "
                f"the limit is {MAX_OBJECT_BYTES} bytes."
            )
        if not content_type or "/" not in content_type:
            raise StorageError(
                f"Refusing to store {key} without a valid content type."
            )

    def save(
        self, key: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> str:
        self._validate(key, data, content_type)
        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
                Metadata={CHECKSUM_METADATA_KEY: checksum(data)},
            )
        except Exception as exc:  # noqa: BLE001
            raise StorageError(
                f"Could not store the object under {key}."
            ) from exc
        return self.url_for(key)

    def read(self, key: str) -> bytes:
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
            return response["Body"].read()
        except Exception as exc:  # noqa: BLE001
            raise StorageError(
                f"Could not read the object stored under {key}."
            ) from exc

    def url_for(self, key: str) -> str:
        # The bucket is private, so downloads go through a presigned URL
        # that stops working after ``url_expiry_seconds``.
        try:
            return self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=self.url_expiry_seconds,
            )
        except Exception:  # noqa: BLE001
            return f"s3://{self.bucket}/{key}"

    def delete(self, key: str) -> bool:
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:  # noqa: BLE001
            return False

    def exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:  # noqa: BLE001
            return False

    def checksum(self, key: str) -> str | None:
        try:
            response = self.client.head_object(Bucket=self.bucket, Key=key)
            metadata = response.get("Metadata") or {}
            # S3 normalises user metadata keys to lowercase.
            return metadata.get(CHECKSUM_METADATA_KEY.lower()) or metadata.get(
                CHECKSUM_METADATA_KEY
            )
        except Exception:  # noqa: BLE001
            return None
