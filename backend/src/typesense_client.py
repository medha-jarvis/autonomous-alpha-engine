"""Typesense client — index and search transcripts and evaluations."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)


class TypesenseClient:
    """Thin HTTP client for Typesense (no official SDK dependency)."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8108,
        api_key: str = "",
        protocol: str = "http",
    ) -> None:
        self.base_url = f"{protocol}://{host}:{port}"
        self.api_key = api_key
        self.headers = {
            "X-TYPESENSE-API-KEY": api_key,
            "Content-Type": "application/json",
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    # ── Collection Management ──────────────────────────────────────

    def create_collection(self, schema: dict) -> dict:
        """Create a Typesense collection from a schema dict."""
        url = f"{self.base_url}/collections"
        resp = self.session.post(url, json=schema, timeout=10)
        if resp.status_code == 409:
            logger.info("Collection already exists: %s", schema.get("name"))
            return {"already_exists": True}
        resp.raise_for_status()
        logger.info("Created collection: %s", schema.get("name"))
        return resp.json()

    def delete_collection(self, name: str) -> dict:
        """Drop a collection entirely."""
        url = f"{self.base_url}/collections/{name}"
        resp = self.session.delete(url, timeout=10)
        resp.raise_for_status()
        logger.info("Deleted collection: %s", name)
        return resp.json()

    def get_collection(self, name: str) -> dict | None:
        """Return collection info, or None if it doesn't exist."""
        url = f"{self.base_url}/collections/{name}"
        resp = self.session.get(url, timeout=10)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    def list_collections(self) -> list[dict]:
        """List all collections."""
        url = f"{self.base_url}/collections"
        resp = self.session.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json()

    # ── Document Indexing ──────────────────────────────────────────

    def index_document(self, collection: str, document: dict) -> dict:
        """Index a single document (auto-generated id if none provided)."""
        url = f"{self.base_url}/collections/{collection}/documents"
        resp = self.session.post(url, json=document, timeout=10)
        if resp.status_code != 201:
            logger.warning(
                "Index doc failed [%d]: %s", resp.status_code, resp.text[:200]
            )
        resp.raise_for_status()
        return resp.json()

    def index_documents(
        self, collection: str, documents: list[dict]
    ) -> list[dict]:
        """Import multiple documents in a single bulk call."""
        url = f"{self.base_url}/collections/{collection}/documents/import"
        body = "\n".join(json.dumps(d) for d in documents) + "\n"
        resp = self.session.post(
            url, data=body, timeout=30,
            headers={**self.headers, "Content-Type": "text/plain"},
        )
        results = []
        for line in resp.text.strip().split("\n"):
            if line:
                results.append(json.loads(line))
        failures = [r for r in results if not r.get("success")]
        if failures:
            logger.warning(
                "%d/%d index failures in %s",
                len(failures), len(documents), collection,
            )
        return results

    # ── Search ─────────────────────────────────────────────────────

    def search(
        self,
        collection: str,
        query: str,
        query_by: str = "full_text,prepared_remarks,qa_section",
        limit: int = 10,
        filters: str | None = None,
        sort_by: str | None = "_text_match:desc",
    ) -> dict:
        """Full-text search across a collection."""
        params: dict[str, Any] = {
            "q": query,
            "query_by": query_by,
            "per_page": limit,
        }
        if filters:
            params["filter_by"] = filters
        if sort_by:
            params["sort_by"] = sort_by

        url = f"{self.base_url}/collections/{collection}/documents/search"
        resp = self.session.get(url, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def get_document(self, collection: str, doc_id: str) -> dict | None:
        """Fetch a single document by ID."""
        url = f"{self.base_url}/collections/{collection}/documents/{doc_id}"
        resp = self.session.get(url, timeout=10)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    def delete_document(self, collection: str, doc_id: str) -> dict:
        """Delete a document by ID."""
        url = f"{self.base_url}/collections/{collection}/documents/{doc_id}"
        resp = self.session.delete(url, timeout=10)
        return resp.json()

    # ── Health ─────────────────────────────────────────────────────

    def health(self) -> bool:
        """Check if Typesense is reachable."""
        try:
            resp = self.session.get(f"{self.base_url}/health", timeout=5)
            return resp.json().get("ok", False)
        except Exception:
            return False


# ── Default Collection Schemas ─────────────────────────────────────

CONCALL_TRANSCRIPTS_SCHEMA = {
    "name": "concall_transcripts",
    "fields": [
        {"name": "news_id", "type": "string"},
        {"name": "company_name", "type": "string"},
        {"name": "ticker", "type": "string", "facet": True},
        {"name": "bse_scrip_code", "type": "int32"},
        {"name": "quarter", "type": "string", "facet": True},
        {"name": "fiscal_year", "type": "string", "facet": True},
        {"name": "announcement_date", "type": "string"},
        {"name": "subcategory", "type": "string", "facet": True},
        {"name": "pdf_url_r2", "type": "string"},
        {"name": "pdf_url_bse", "type": "string"},
        {"name": "full_text", "type": "string"},
        {"name": "prepared_remarks", "type": "string"},
        {"name": "qa_section", "type": "string"},
        {"name": "created_at", "type": "int64"},
    ],
    "default_sorting_field": "created_at",
}

EVALUATIONS_SCHEMA = {
    "name": "evaluations",
    "fields": [
        {"name": "transcript_id", "type": "string"},
        {"name": "ticker", "type": "string", "facet": True},
        {"name": "company_name", "type": "string"},
        {"name": "quarter", "type": "string", "facet": True},
        {"name": "fiscal_year", "type": "string", "facet": True},
        {"name": "uc_number", "type": "int32"},
        {"name": "uc_name", "type": "string"},
        {"name": "result_json", "type": "string"},
        {"name": "alert_triggered", "type": "bool"},
        {"name": "created_at", "type": "int64"},
    ],
    "default_sorting_field": "created_at",
}


def ensure_collections(client: TypesenseClient) -> None:
    """Create default collections if they don't exist."""
    for schema in (CONCALL_TRANSCRIPTS_SCHEMA, EVALUATIONS_SCHEMA):
        existing = client.get_collection(schema["name"])
        if existing is None:
            client.create_collection(schema)
            logger.info("Created collection: %s", schema["name"])
        else:
            logger.debug("Collection exists: %s", schema["name"])