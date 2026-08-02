"""BSE API client — fetches corporate announcements via the `bse` library."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from bse import BSE

from config import config, lookup_scrip_code

logger = logging.getLogger(__name__)

# Subcategories that indicate concall transcripts or investor presentations
TARGET_SUBCATEGORIES = frozenset({
    "Earnings Call Transcript",
    "Analyst / Investor Meet",
    "Investor Presentation",
})

# Types of announcements that are NOT transcripts (skip these)
SKIP_CATEGORIES = frozenset({
    "General",
    "Press Release / Media Release",
    "Newspaper Publication",
    "Change in Management",
    "Date of payment of Dividend",
    "Dividend",
    "Outcome of Board Meeting",
    "Financial Results",
})


class BSEClient:
    """Wraps the `bse` library to fetch corporate announcements."""

    def __init__(self) -> None:
        self._bse: BSE | None = None

    @property
    def client(self) -> BSE:
        if self._bse is None:
            self._bse = BSE(download_folder="/tmp/bse-downloads")
        return self._bse

    def get_scrip_code(self, ticker: str) -> int:
        """Get BSE scrip code for a ticker symbol.

        Checks the hardcoded portfolio dict first, then falls back to
        the ``bse`` library's live lookup.
        """
        return lookup_scrip_code(ticker)

    def fetch_announcements(
        self,
        ticker: str,
        days_back: int = 7,
        subcategory_filter: bool = True,
    ) -> list[dict[str, Any]]:
        """Fetch recent BSE announcements for a ticker.

        Returns a list of announcement dicts, optionally filtered to
        transcript/investor-meet subcategories.
        """
        scrip_code = self.get_scrip_code(ticker)
        to_date = datetime.now()
        from_date = to_date - timedelta(days=days_back)

        try:
            raw = self.client.announcements(
                scripcode=str(scrip_code),
                from_date=from_date,
                to_date=to_date,
            )
        except Exception:
            logger.exception("BSE API error for %s (scrip=%s)", ticker, scrip_code)
            return []

        table = raw.get("Table") or []
        if not table:
            return []

        announcements = []
        for row in table:
            subcat = (row.get("SUBCATNAME") or "").strip()
            category = (row.get("CATEGORYNAME") or "").strip()

            # Skip non-relevant categories
            if category in SKIP_CATEGORIES:
                continue

            # Optionally filter to target subcategories
            if subcategory_filter and subcat not in TARGET_SUBCATEGORIES:
                continue

            attachment = (row.get("ATTACHMENTNAME") or "").strip()
            if not attachment:
                continue

            announcements.append({
                "news_id": row.get("NEWSID", ""),
                "scrip_code": int(scrip_code),
                "ticker": ticker,
                "company_name": (row.get("SLONGNAME") or "").strip(),
                "title": (row.get("NEWSSUB") or "").strip(),
                "headline": (row.get("HEADLINE") or "").strip(),
                "subcategory": subcat,
                "category": category,
                "attachment_name": attachment,
                "announcement_date": (row.get("NEWS_DT") or "").strip(),
                "pdf_url_bse": (
                    f"https://www.bseindia.com/xml-data/corpfiling/"
                    f"AttachLive/{attachment}"
                ),
            })

        return announcements

    def fetch_all_portfolio_announcements(
        self,
        days_back: int = 7,
        subcategory_filter: bool = True,
    ) -> dict[str, list[dict[str, Any]]]:
        """Fetch announcements for all portfolio stocks.

        Returns a dict mapping ticker -> list of announcements.
        """
        results: dict[str, list[dict[str, Any]]] = {}
        for ticker in config.portfolio_stocks:
            anns = self.fetch_announcements(ticker, days_back, subcategory_filter)
            if anns:
                results[ticker] = anns
                logger.info(
                    "Fetched %d announcements for %s", len(anns), ticker
                )
            else:
                logger.debug("No new announcements for %s", ticker)
        return results

    def check_for_new_transcripts(
        self, processed_ids: set[str], days_back: int = 15
    ) -> list[dict[str, Any]]:
        """Fetch all portfolio announcements and return only unprocessed ones.

        ``processed_ids`` is a set of ``news_id`` strings that have already
        been handled.
        """
        all_new: list[dict[str, Any]] = []
        for ticker in config.portfolio_stocks:
            anns = self.fetch_announcements(ticker, days_back)
            for ann in anns:
                if ann["news_id"] not in processed_ids:
                    all_new.append(ann)
        return all_new