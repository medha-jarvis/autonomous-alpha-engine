"""
Autonomous Alpha Engine — Bulk Historical Seeder
=================================================
Paginates through ALL BSE announcements for all 31 portfolio stocks
over the last 2 years, downloads transcripts & presentations,
extracts text, indexes to Typesense.

Skips PDFs that have been removed from BSE servers (404).
Checks availability with a quick HEAD request first.

Run:  uv run python3 backend/scripts/bulk_seed.py
"""

import sys, os, json, time, logging, urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from bse import BSE
from config import config, lookup_scrip_code
from pdf_processor import download_pdf, extract_text
from typesense_client import TypesenseClient, ensure_collections
from r2_storage import configure as configure_r2

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("bulk_seed")


def is_pdf_available(pdf_url: str) -> bool:
    """Quick HEAD check if PDF is still available on BSE servers."""
    try:
        req = urllib.request.Request(pdf_url, method="HEAD")
        req.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.bseindia.com/",
        })
        resp = urllib.request.urlopen(req, timeout=5)
        ct = resp.headers.get("Content-Type", "")
        return resp.status == 200 and "pdf" in ct.lower()
    except:
        return False


def detect_doc_type(subcat: str, title: str, headline: str) -> str:
    lower = (title + " " + headline).lower()
    if subcat == "Earnings Call Transcript":
        return "transcript"
    if subcat in ("Analyst / Investor Meet", "Investor Presentation"):
        return "presentation"
    if "transcript" in lower:
        return "transcript"
    if any(k in lower for k in ["presentation", "ppt"]):
        return "presentation"
    return "other"


def estimate_quarter(date_str: str) -> tuple[str, str]:
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", ""))
    except:
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


def fetch_stock_announcements(bse: BSE, scrip: str, days_back: int = 730):
    """Fetch ALL announcements for a stock by paginating."""
    to_date = datetime.now()
    from_date = to_date - timedelta(days=days_back)
    all_items = []
    for page in range(1, 100):
        try:
            resp = bse.announcements(page_no=page, scripcode=scrip, from_date=from_date, to_date=to_date)
            table = resp.get("Table", [])
            if not table:
                break
            all_items.extend(table)
            if len(table) < 50:
                break
        except Exception as e:
            log.warning("  Page %d error: %s", page, e)
            break
    return all_items


def filter_relevant(items: list[dict]) -> list[dict]:
    relevant = []
    for r in items:
        subcat = (r.get("SUBCATNAME") or "").strip()
        title = (r.get("NEWSSUB") or "").strip()
        headline = (r.get("HEADLINE") or "").strip()
        attachment = (r.get("ATTACHMENTNAME") or "").strip()
        news_id = str(r.get("NEWSID", ""))
        if not attachment or not news_id:
            continue
        doc_type = detect_doc_type(subcat, title, headline)
        if doc_type == "other":
            continue
        pdf_url = f"https://www.bseindia.com/xml-data/corpfiling/AttachLive/{attachment}"
        relevant.append({
            "news_id": news_id,
            "company_name": (r.get("SLONGNAME") or "").strip(),
            "subcategory": subcat,
            "doc_type": doc_type,
            "announcement_date": (r.get("NEWS_DT") or "").strip(),
            "pdf_url_bse": pdf_url,
        })
    return relevant


def process_single(ann: dict, ts: TypesenseClient, ticker: str, scrip_code: int) -> dict:
    """Download, extract, index. Returns result dict."""
    quarter, fiscal_year = estimate_quarter(ann["announcement_date"])
    news_id = ann["news_id"]
    doc_type = ann["doc_type"]

    result = {
        "news_id": news_id, "ticker": ticker,
        "subcategory": ann["subcategory"], "doc_type": doc_type,
        "quarter": quarter, "fiscal_year": fiscal_year, "status": "processing",
    }

    try:
        # Quick availability check first
        if not is_pdf_available(ann["pdf_url_bse"]):
            result["status"] = "skipped_404"
            return result

        pdf_bytes = download_pdf(ann)
        transcript = extract_text(pdf_bytes)

        ts_doc = {
            "news_id": news_id, "company_name": ann["company_name"],
            "ticker": ticker, "bse_scrip_code": scrip_code,
            "quarter": quarter, "fiscal_year": fiscal_year,
            "announcement_date": ann["announcement_date"],
            "subcategory": ann["subcategory"], "doc_type": doc_type,
            "pdf_url_r2": "", "pdf_url_bse": ann["pdf_url_bse"],
            "full_text": transcript.full_text[:50000],
            "prepared_remarks": transcript.prepared_remarks[:20000],
            "qa_section": transcript.qa_section[:20000] if doc_type == "transcript" else "",
            "created_at": int(time.time()),
        }
        ts.index_document("concall_transcripts", ts_doc)

        result["status"] = "completed"
        result["page_count"] = transcript.page_count
        log.info("  ✓ %s %s %s (%d pages)", ticker, quarter, fiscal_year, transcript.page_count)

    except Exception as e:
        log.info("  - %s %s: %s", ticker, news_id[:8], e)
        result["status"] = "failed"
        result["error"] = str(e)

    return result


def main():
    bse = BSE(download_folder="/tmp/bse-downloads")
    configure_r2(account_id=config.r2_account_id, access_key=config.r2_access_key_id,
                 secret_key=config.r2_secret_access_key, bucket=config.r2_bucket_name,
                 token=config.r2_token_value)

    ts = TypesenseClient(host=config.typesense_host, port=config.typesense_port,
                         api_key=config.typesense_api_key, protocol=config.typesense_protocol)
    ensure_collections(ts)

    total_fetched = 0
    total_relevant = 0
    total_indexed = 0
    total_skipped = 0
    all_results = []
    start_time = time.time()

    for ticker, scrip in config.portfolio_stocks.items():
        scrip_code = int(lookup_scrip_code(ticker) or scrip)
        log.info("")
        log.info("=" * 60)
        log.info("%s (scrip: %s)...", ticker, scrip)
        log.info("=" * 60)

        items = fetch_stock_announcements(bse, scrip)
        total_fetched += len(items)

        relevant = filter_relevant(items)
        total_relevant += len(relevant)
        log.info("  %d total, %d relevant", len(items), len(relevant))
        if not relevant:
            continue

        # Pre-check PDF availability (parallel HEAD requests)
        pdf_checks = {}
        with ThreadPoolExecutor(max_workers=10) as ex:
            fut = {ex.submit(is_pdf_available, r["pdf_url_bse"]): r for r in relevant}
            for f in as_completed(fut):
                r = fut[f]
                try:
                    pdf_checks[r["news_id"]] = f.result()
                except:
                    pdf_checks[r["news_id"]] = False

        available = [r for r in relevant if pdf_checks.get(r["news_id"])]
        skipped = [r for r in relevant if not pdf_checks.get(r["news_id"])]
        total_skipped += len(skipped)
        log.info("  %d available, %d skipped (404)", len(available), len(skipped))

        if not available:
            continue

        # Download & index (parallel)
        with ThreadPoolExecutor(max_workers=5) as ex:
            futures = {ex.submit(process_single, r, ts, ticker, scrip_code): r for r in available}
            for f in as_completed(futures):
                result = f.result()
                all_results.append(result)
                if result["status"] == "completed":
                    total_indexed += 1

    elapsed = time.time() - start_time
    log.info("")
    log.info("=" * 60)
    log.info("BULK SEED COMPLETE")
    log.info("=" * 60)
    log.info("Time: %d min %d sec", elapsed // 60, elapsed % 60)
    log.info("Fetched: %d total announcements", total_fetched)
    log.info("Relevant: %d docs", total_relevant)
    log.info("Available (not 404): %d", total_relevant - total_skipped)
    log.info("Indexed: %d", total_indexed)

    summary = {
        "elapsed_seconds": elapsed,
        "total_fetched": total_fetched,
        "total_relevant": total_relevant,
        "total_available": total_relevant - total_skipped,
        "total_indexed": total_indexed,
        "skipped_404": total_skipped,
    }
    print(json.dumps(summary, indent=2))

    # Save detailed results
    with open("/opt/data/alpha-engine/db/bulk_seed_results.json", "w") as f:
        json.dump({"summary": summary, "results": all_results}, f, indent=2)


if __name__ == "__main__":
    main()