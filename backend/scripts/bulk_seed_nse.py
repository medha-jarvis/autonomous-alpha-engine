"""Autonomous Alpha Engine — NSE Historical Seeder
=================================================
Fetches ALL earnings call transcripts and investor presentations
from NSE's public API for all 31 portfolio stocks, downloads PDFs,
extracts text, indexes to Typesense.

NSE has MUCH better historical retention than BSE — many PDFs from 2024
are still downloadable.

Run:  uv run python3 backend/scripts/bulk_seed_nse.py
"""

import sys, os, json, time, logging, urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from nse_client import fetch_announcements, NSEAnnouncement, is_pdf_available
from config import config
from pdf_processor import download_pdf, extract_text
from typesense_client import TypesenseClient, ensure_collections
from r2_storage import configure as configure_r2

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("nse_bulk")


def process_single(ann: NSEAnnouncement, ts: TypesenseClient, ticker: str):
    """Download, extract text, index to Typesense."""
    quarter, fiscal_year = ann.announcement_date[:13], "??"
    from nse_client import estimate_quarter
    quarter, fiscal_year = estimate_quarter(ann.announcement_date)
    news_id = ann.news_id

    result = {
        "news_id": news_id,
        "ticker": ticker,
        "doc_type": ann.doc_type,
        "quarter": quarter,
        "fiscal_year": fiscal_year,
        "status": "processing",
    }

    try:
        # Quick availability check
        if not is_pdf_available(ann.pdf_url):
            result["status"] = "skipped_404"
            return result

        # Download PDF
        pdf_bytes = download_pdf({
            "pdf_url_bse": ann.pdf_url,
            "announcement_date": ann.announcement_date,
            "ticker": ticker,
            "news_id": news_id,
        })

        # Extract text
        transcript = extract_text(pdf_bytes)

        # Build Typesense doc
        ts_doc = ann.to_index_doc(ticker)
        ts_doc["full_text"] = transcript.full_text[:50000]
        ts_doc["prepared_remarks"] = transcript.prepared_remarks[:20000] if transcript.prepared_remarks else ""
        ts_doc["qa_section"] = transcript.qa_section[:20000] if transcript.qa_section else ""
        ts_doc["created_at"] = int(time.time())

        ts.index_document("concall_transcripts", ts_doc)

        result["status"] = "completed"
        result["page_count"] = transcript.page_count
        log.info("  ✓ %s %s %s (%d pages)", ticker, quarter, fiscal_year, transcript.page_count)

    except Exception as e:
        log.info("  ✗ %s %s: %s", ticker, news_id[:8], e)
        result["status"] = "failed"
        result["error"] = str(e)

    return result


def main():
    # Configure R2 (for potential uploads)
    configure_r2(
        account_id=config.r2_account_id,
        access_key=config.r2_access_key_id,
        secret_key=config.r2_secret_access_key,
        bucket=config.r2_bucket_name,
        token=config.r2_token_value,
    )

    ts = TypesenseClient(
        host=config.typesense_host,
        port=config.typesense_port,
        api_key=config.typesense_api_key,
        protocol=config.typesense_protocol,
    )
    ensure_collections(ts)

    total_fetched = 0
    total_relevant = 0
    total_indexed = 0
    total_skipped = 0
    total_failed = 0
    all_results = []
    start_time = time.time()

    stock_tickers = sorted(config.portfolio_stocks.keys())

    for ticker in stock_tickers:
        log.info("")
        log.info("=" * 60)
        log.info("%s...", ticker)
        log.info("=" * 60)

        anns = fetch_announcements(ticker)
        total_relevant += len(anns)
        log.info("  %d relevant (transcripts/presentations/meetings)", len(anns))

        if not anns:
            continue

        # Pre-check PDF availability
        pdf_checks = {}
        with ThreadPoolExecutor(max_workers=10) as ex:
            fut = {ex.submit(is_pdf_available, a.pdf_url): a for a in anns}
            for f in as_completed(fut):
                a = fut[f]
                try:
                    pdf_checks[a.news_id] = f.result()
                except:
                    pdf_checks[a.news_id] = False

        available = [a for a in anns if pdf_checks.get(a.news_id)]
        skipped = [a for a in anns if not pdf_checks.get(a.news_id)]
        total_skipped += len(skipped)
        log.info("  %d available, %d skipped (404)", len(available), len(skipped))

        if not available:
            continue

        # Filter to only transcripts + presentations (skip mere meeting intimations)
        real_docs = [a for a in available if a.doc_type in ("transcript", "presentation")]
        if len(real_docs) < len(available):
            log.info("  (%d of those are meetings/notices, skipping for indexing)",
                     len(available) - len(real_docs))
        if not real_docs:
            continue

        # Download & index (parallel)
        with ThreadPoolExecutor(max_workers=5) as ex:
            futures = {ex.submit(process_single, a, ts, ticker): a for a in real_docs}
            for f in as_completed(futures):
                result = f.result()
                all_results.append(result)
                if result["status"] == "completed":
                    total_indexed += 1
                elif result["status"] == "failed":
                    total_failed += 1

    elapsed = time.time() - start_time
    log.info("")
    log.info("=" * 60)
    log.info("NSE BULK SEED COMPLETE")
    log.info("=" * 60)
    log.info("Time: %d min %d sec", elapsed // 60, elapsed % 60)
    log.info("Total relevant (transcripts/presentations/meetings): %d", total_relevant)
    log.info("Available (not 404): %d", total_relevant - total_skipped)
    log.info("Indexed (transcripts + presentations): %d", total_indexed)
    log.info("Failed: %d", total_failed)

    summary = {
        "elapsed_seconds": elapsed,
        "total_relevant": total_relevant,
        "total_indexed": total_indexed,
        "total_skipped_404": total_skipped,
        "total_failed": total_failed,
    }
    print(json.dumps(summary, indent=2))

    # Save results
    Path("/opt/data/alpha-engine/db/").mkdir(parents=True, exist_ok=True)
    with open("/opt/data/alpha-engine/db/nse_seed_results.json", "w") as f:
        json.dump({"summary": summary, "results": all_results}, f, indent=2)


if __name__ == "__main__":
    main()