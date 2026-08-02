"""NSE API client — fetches corporate announcements via the public NSE API.

NSE has a MUCH richer archive than BSE — PDFs going back to 2024 still downloadable.
No authentication needed. Direct PDF links on nsearchives.nseindia.com.

Endpoint: https://www.nseindia.com/api/corporate-announcements
PDF CDN:  https://nsearchives.nseindia.com/corporate/
"""

import json
import logging
import time
import urllib.request
from datetime import datetime, timedelta
from typing import Dict, List
from dataclasses import dataclass, field, asdict

log = logging.getLogger("nse_client")

NSE_API_BASE = "https://www.nseindia.com/api/corporate-announcements"
NSE_ARCHIVE = "https://nsearchives.nseindia.com/corporate"

# Special NSE symbol mappings (Zomato rebranded to Eternal Ltd)
SYMBOL_MAP = {
    "ZOMATO": "ETERNAL",
    "MCDOWELL-N": "MCDOWELLN",  # May not work - try raw
}

# Keywords to identify transcripts and presentations
TRANSCRIPT_KEYWORDS = ["transcript", "earnings call"]
PRESENTATION_KEYWORDS = ["presentation", "ppt", "investor meet", "analyst meet", "analysts/institutional"]
MEETING_KEYWORDS = ["schedule of meet", "prior intimation", "conference call"]

# API will be rate-limited — use a throttle
REQUEST_INTERVAL = 1.5  # sec between requests
_last_request = 0.0


def _rate_limit():
    global _last_request
    elapsed = time.time() - _last_request
    if elapsed < REQUEST_INTERVAL:
        time.sleep(REQUEST_INTERVAL - elapsed)
    _last_request = time.time()


@dataclass
class NSEAnnouncement:
    news_id: str
    symbol: str
    company_name: str
    announcement_date: str
    desc: str  # filing category
    attchmnt_text: str  # detailed filing description
    pdf_url: str
    doc_type: str  # "transcript", "presentation", "meeting", "other"
    source: str = "NSE"

    def to_index_doc(self, ticker: str) -> dict:
        """Convert to Typesense document format."""
        quarter, fiscal_year = estimate_quarter(self.announcement_date)
        return {
            "news_id": self.news_id,
            "company_name": self.company_name,
            "ticker": ticker,
            "bse_scrip_code": 0,
            "quarter": quarter,
            "fiscal_year": fiscal_year,
            "announcement_date": self.announcement_date,
            "subcategory": self.desc,
            "doc_type": self.doc_type,
            "pdf_url_r2": "",
            "pdf_url_bse": self.pdf_url,
            "full_text": "",
            "prepared_remarks": "",
            "qa_section": "",
            "created_at": int(time.time()),
        }


def detect_doc_type(desc: str, attchmnt_text: str) -> str:
    """Classify the announcement type."""
    combined = (desc + " " + attchmnt_text).lower()
    if any(k in combined for k in TRANSCRIPT_KEYWORDS):
        return "transcript"
    if any(k in combined for k in PRESENTATION_KEYWORDS):
        return "presentation"
    if any(k in combined for k in MEETING_KEYWORDS):
        return "meeting"
    return "other"


def estimate_quarter(date_str: str) -> tuple:
    """Estimate quarter & fiscal year from the announcement date string.
    
    NSE format: "28-Jul-2026 20:24:53"
    """
    try:
        parts = date_str.split()
        dt = datetime.strptime(parts[0], "%d-%b-%Y")
    except (ValueError, IndexError):
        return "Q?", "FY??"
    m, y = dt.month, dt.year
    if 4 <= m <= 6:
        return "Q1", f"FY{y-2000}-{y-1999}"
    elif 7 <= m <= 9:
        return "Q2", f"FY{y-2000}-{y-1999}"
    elif 10 <= m <= 12:
        return "Q3", f"FY{y-2000}-{y-1999}"
    else:
        return "Q4", f"FY{y-1-2000}-{y-2000}"


def resolve_symbol(ticker: str) -> str:
    """Map ticker to NSE API symbol (handles Zomato→Eternal)."""
    return SYMBOL_MAP.get(ticker, ticker)


def fetch_announcements(
    symbol: str,
    from_date: str = "01-01-2024",
    to_date: str = None,
) -> List[NSEAnnouncement]:
    """Fetch ALL corporate announcements for an NSE symbol.

    NSE API returns all results in one page (no pagination needed).
    """
    if to_date is None:
        to_date = datetime.now().strftime("%d-%m-%Y")

    api_symbol = resolve_symbol(symbol)
    url = (f"{NSE_API_BASE}?index=equities&symbol={api_symbol}"
           f"&from_date={from_date}&to_date={to_date}")

    log.info("  Fetching NSE announcements for %s (api_symbol=%s)...", symbol, api_symbol)

    _rate_limit()
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    })

    try:
        resp = urllib.request.urlopen(req, timeout=20)
        raw = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        log.warning("  NSE HTTP error for %s: %s", symbol, e)
        return []
    except Exception as e:
        log.warning("  NSE error for %s: %s", symbol, e)
        return []

    if not isinstance(raw, list):
        log.warning("  Unexpected NSE response for %s (not a list)", symbol)
        return []

    results = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        attchmnt_file = (item.get("attchmntFile") or "").strip()
        if not attchmnt_file:
            continue

        desc = (item.get("desc") or "").strip()
        attchment_text = (item.get("attchmntText") or "").strip()
        news_id = str(item.get("seq_id", ""))
        an_dt = (item.get("an_dt") or "").strip()
        sm_name = (item.get("sm_name") or "").strip()

        doc_type = detect_doc_type(desc, attchment_text)
        if doc_type == "other":
            continue

        results.append(NSEAnnouncement(
            news_id=news_id,
            symbol=symbol,
            company_name=sm_name,
            announcement_date=an_dt,
            desc=desc,
            attchmnt_text=attchment_text,
            pdf_url=attchmnt_file,
            doc_type=doc_type,
        ))

    return results


def is_pdf_available(pdf_url: str) -> bool:
    """Quick HEAD check if PDF is downloadable."""
    try:
        req = urllib.request.Request(pdf_url, method="HEAD", headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        resp = urllib.request.urlopen(req, timeout=5)
        return resp.status == 200
    except Exception:
        return False