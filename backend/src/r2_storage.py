"""Cloudflare R2 storage client."""

from __future__ import annotations

import io
import logging
from typing import BinaryIO

import boto3
from botocore.config import Config as BotoConfig

logger = logging.getLogger(__name__)

# ── Injected via config.py, not hardcoded here ──────────────────────
_ACCOUNT_ID: str = ""
_ACCESS_KEY: str = ""
_SECRET_KEY: str = ""
_BUCKET: str = ""
_TOKEN: str = ""
_ENDPOINT: str = ""


def configure(
    account_id: str,
    access_key: str,
    secret_key: str,
    bucket: str,
    token: str = "",
    endpoint: str = "",
) -> None:
    """Set R2 credentials (called once from orchestrator/config)."""
    global _ACCOUNT_ID, _ACCESS_KEY, _SECRET_KEY, _BUCKET, _TOKEN, _ENDPOINT  # noqa: PLW0603
    _ACCOUNT_ID = account_id
    _ACCESS_KEY = access_key
    _SECRET_KEY = secret_key
    _BUCKET = bucket
    _TOKEN = token
    _ENDPOINT = endpoint or f"https://{account_id}.r2.cloudflarestorage.com"


def _get_client():
    session = boto3.Session(
        aws_access_key_id=_ACCESS_KEY,
        aws_secret_access_key=_SECRET_KEY,
    )
    return session.client(
        "s3",
        endpoint_url=_ENDPOINT,
        region_name="auto",
        config=BotoConfig(
            retries={"max_attempts": 3, "mode": "adaptive"},
            connect_timeout=10,
            read_timeout=30,
        ),
    )


def upload_pdf(
    pdf_bytes: bytes,
    object_key: str,
    content_type: str = "application/pdf",
) -> str:
    """Upload a PDF to R2 and return its public URL.

    ``object_key`` should be something like
    ``transcripts/TCS/2026/Q1/27523cab-.....pdf``.
    """
    client = _get_client()
    client.put_object(
        Bucket=_BUCKET,
        Key=object_key,
        Body=io.BytesIO(pdf_bytes),
        ContentType=content_type,
    )
    public_url = f"{_ENDPOINT}/{_BUCKET}/{object_key}"
    logger.info("Uploaded to R2: %s (%d bytes)", object_key, len(pdf_bytes))
    return public_url


def download_pdf(object_key: str) -> bytes:
    """Download a PDF from R2 by its object key."""
    client = _get_client()
    resp = client.get_object(Bucket=_BUCKET, Key=object_key)
    data = resp["Body"].read()
    logger.info("Downloaded from R2: %s (%d bytes)", object_key, len(data))
    return data


def delete_pdf(object_key: str) -> None:
    """Remove a PDF from R2."""
    client = _get_client()
    client.delete_object(Bucket=_BUCKET, Key=object_key)
    logger.info("Deleted from R2: %s", object_key)


def list_transcripts(prefix: str = "transcripts/") -> list[dict]:
    """List transcript objects under a prefix."""
    client = _get_client()
    objects = []
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=_BUCKET, Prefix=prefix):
        for obj in page.get("Contents", []):
            objects.append({
                "key": obj["Key"],
                "size": obj["Size"],
                "last_modified": obj["LastModified"].isoformat(),
            })
    return objects


def build_object_key(
    ticker: str,
    news_id: str,
    attachment_name: str,
    quarter: str = "",
    fiscal_year: str = "",
) -> str:
    """Build a hierarchical object key for R2 storage.

    Pattern: ``transcripts/{TICKER}/{FY}/{Q}/{news_id}_{attachment_name}``
    """
    if quarter and fiscal_year:
        return (
            f"transcripts/{ticker.upper()}/{fiscal_year}/"
            f"{quarter}/{news_id}_{attachment_name}"
        )
    return f"transcripts/{ticker.upper()}/{news_id}_{attachment_name}"