"""Orchestrator — ties the full pipeline together: poll → process → index → eval → alert."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import dotenv

# Load env before importing config
dotenv.load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from config import Config, lookup_scrip_code  # noqa: E402
from bse_client import BSEClient  # noqa: E402
from pdf_processor import download_and_process  # noqa: E402
from typesense_client import (  # noqa: E402
    TypesenseClient,
    ensure_collections,
    CONCALL_TRANSCRIPTS_SCHEMA,
    EVALUATIONS_SCHEMA,
)
from evaluator import Evaluator, build_context  # noqa: E402
from alerter import Alerter  # noqa: E402
from prompts import ALL_UC_TEMPLATES  # noqa: E402

logger = logging.getLogger(__name__)

# Also import and configure r2_storage
from r2_storage import configure as configure_r2, upload_pdf, build_object_key  # noqa: E402


class AlphaEngine:
    """Main orchestration class for the Autonomous Alpha Engine."""

    def __init__(self, config: Config | None = None) -> None:
        self.config = config or Config()
        self.bse = BSEClient()
        self.ts = TypesenseClient(
            host=self.config.typesense_host,
            port=self.config.typesense_port,
            api_key=self.config.typesense_api_key,
            protocol=self.config.typesense_protocol,
        )
        self.evaluator = Evaluator(
            api_key=self.config.openrouter_api_key,
            model=self.config.llm_model,
        )
        self.alerter = Alerter(
            bot_token=self.config.telegram_bot_token,
            chat_id=self.config.telegram_chat_id,
        )

        # Configure R2
        configure_r2(
            account_id=self.config.r2_account_id,
            access_key=self.config.r2_access_key_id,
            secret_key=self.config.r2_secret_access_key,
            bucket=self.config.r2_bucket_name,
            token=self.config.r2_token_value,
        )

        # Initialize DB for tracking processed announcements
        self._init_db()

    def _init_db(self) -> None:
        """Initialize SQLite DB for tracking processed news_ids."""
        db_dir = Path(self.config.data_dir) / "db"
        db_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = str(db_dir / "pipeline.db")
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS processed_announcements (
                news_id TEXT PRIMARY KEY,
                ticker TEXT NOT NULL,
                processed_at INTEGER NOT NULL,
                quarter TEXT,
                fiscal_year TEXT,
                pdf_url_r2 TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS alerts_sent (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                news_id TEXT NOT NULL,
                uc_number INTEGER NOT NULL,
                ticker TEXT NOT NULL,
                sent_at INTEGER NOT NULL,
                UNIQUE(news_id, uc_number)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS portfolio_stocks (
                ticker TEXT PRIMARY KEY,
                bse_scrip_code INTEGER,
                added_at INTEGER NOT NULL,
                active INTEGER DEFAULT 1
            )
        """)
        # Seed portfolio stocks
        for ticker, scrip in self.config.portfolio_stocks.items():
            conn.execute(
                "INSERT OR IGNORE INTO portfolio_stocks (ticker, bse_scrip_code, added_at) VALUES (?, ?, ?)",
                (ticker, scrip, int(time.time())),
            )
        conn.commit()
        conn.close()
        logger.info("Initialized DB at %s", self.db_path)

    def _get_processed_ids(self) -> set[str]:
        """Return set of already-processed news IDs."""
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute("SELECT news_id FROM processed_announcements").fetchall()
        conn.close()
        return {r[0] for r in rows}

    def _mark_processed(
        self,
        news_id: str,
        ticker: str,
        quarter: str = "",
        fiscal_year: str = "",
        pdf_url_r2: str = "",
    ) -> None:
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT OR IGNORE INTO processed_announcements VALUES (?, ?, ?, ?, ?, ?)",
            (news_id, ticker, int(time.time()), quarter, fiscal_year, pdf_url_r2),
        )
        conn.commit()
        conn.close()

    def _alert_already_sent(self, news_id: str, uc_number: int) -> bool:
        conn = sqlite3.connect(self.db_path)
        row = conn.execute(
            "SELECT 1 FROM alerts_sent WHERE news_id = ? AND uc_number = ?",
            (news_id, uc_number),
        ).fetchone()
        conn.close()
        return row is not None

    def _mark_alert_sent(self, news_id: str, uc_number: int, ticker: str) -> None:
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT OR IGNORE INTO alerts_sent (news_id, uc_number, ticker, sent_at) VALUES (?, ?, ?, ?)",
            (news_id, uc_number, ticker, int(time.time())),
        )
        conn.commit()
        conn.close()

    def _estimate_quarter(self, announcement_date: str) -> tuple[str, str]:
        """Estimate quarter and fiscal year from announcement date."""
        try:
            dt = datetime.fromisoformat(announcement_date.replace("Z", ""))
        except (ValueError, AttributeError):
            dt = datetime.now()

        month = dt.month
        year = dt.year

        # Fiscal year: Apr-Mar. Q1=Apr-Jun, Q2=Jul-Sep, Q3=Oct-Dec, Q4=Jan-Mar
        if 4 <= month <= 6:
            quarter = "Q1"
            fiscal_year = f"FY{year - 2000}-{year - 1999}"
        elif 7 <= month <= 9:
            quarter = "Q2"
            fiscal_year = f"FY{year - 2000}-{year - 1999}"
        elif 10 <= month <= 12:
            quarter = "Q3"
            fiscal_year = f"FY{year - 2000}-{year - 1999}"
        else:  # Jan-Mar
            quarter = "Q4"
            fiscal_year = f"FY{year - 1 - 2000}-{year - 2000}"

        return quarter, fiscal_year

    def poll_and_process(self) -> list[dict[str, Any]]:
        """Main pipeline: poll BSE → process new → index → evaluate → alert.

        Returns a list of processing results.
        """
        results = []
        processed_ids = self._get_processed_ids()

        # Step 1: Poll BSE for new transcripts
        logger.info("Polling BSE for new announcements...")
        new_announcements = self.bse.check_for_new_transcripts(processed_ids, days_back=15)
        logger.info("Found %d new announcements", len(new_announcements))

        for ann in new_announcements:
            ticker = ann["ticker"]
            news_id = ann["news_id"]
            result = self._process_single(ann)
            results.append(result)

        if not new_announcements:
            logger.info("No new announcements to process")

        return results

    def _process_single(self, ann: dict) -> dict[str, Any]:
        """Process a single announcement through the full pipeline."""
        ticker = ann["ticker"]
        news_id = ann["news_id"]
        company_name = ann["company_name"]
        subcategory = ann["subcategory"]
        quarter, fiscal_year = self._estimate_quarter(ann["announcement_date"])

        result = {
            "ticker": ticker,
            "news_id": news_id,
            "company_name": company_name,
            "subcategory": subcategory,
            "status": "processing",
            "quarter": quarter,
            "fiscal_year": fiscal_year,
        }

        logger.info(
            "Processing %s: %s (%s %s) — %s",
            ticker, subcategory, quarter, fiscal_year, news_id[:8],
        )

        try:
            # Step 2: Download PDF and extract text
            pdf_bytes, transcript = download_and_process(ann)

            # Step 3: Upload PDF to R2
            object_key = build_object_key(
                ticker, news_id, ann["attachment_name"], quarter, fiscal_year,
            )
            pdf_url_r2 = upload_pdf(pdf_bytes, object_key)
            result["pdf_url_r2"] = pdf_url_r2

            # Step 4: Index into Typesense
            doc = {
                "news_id": news_id,
                "company_name": company_name,
                "ticker": ticker,
                "bse_scrip_code": self.bse.get_scrip_code(ticker),
                "quarter": quarter,
                "fiscal_year": fiscal_year,
                "announcement_date": ann["announcement_date"],
                "subcategory": subcategory,
                "pdf_url_r2": pdf_url_r2,
                "pdf_url_bse": ann["pdf_url_bse"],
                "full_text": transcript.full_text[:50000],
                "prepared_remarks": transcript.prepared_remarks[:20000],
                "qa_section": transcript.qa_section[:20000],
                "created_at": int(time.time()),
            }
            self.ts.index_document("concall_transcripts", doc)

            # Step 5: Run 20 evaluations asynchronously
            context = build_context(doc)
            eval_results = asyncio.run(self.evaluator.evaluate_all(context))
            result["evaluations"] = eval_results

            # Step 6: Index evaluations + send alerts
            alerts_triggered = []
            for eval_result in eval_results:
                uc_num = eval_result.get("uc_number", 0)
                uc_name = eval_result.get("uc_name", "")

                # Index evaluation result
                eval_doc = {
                    "transcript_id": news_id,
                    "ticker": ticker,
                    "company_name": company_name,
                    "quarter": quarter,
                    "fiscal_year": fiscal_year,
                    "uc_number": uc_num,
                    "uc_name": uc_name,
                    "result_json": json.dumps(eval_result.get("result", {})),
                    "alert_triggered": eval_result.get("triggered", False),
                    "created_at": int(time.time()),
                }
                self.ts.index_document("evaluations", eval_doc)

                # Send alert if triggered and not already sent
                triggered = eval_result.get("triggered", False)
                if triggered and not self._alert_already_sent(news_id, uc_num):
                    self.alerter.send_alert(ticker, uc_num, eval_result, company_name)
                    self._mark_alert_sent(news_id, uc_num, ticker)
                    alerts_triggered.append(uc_num)

            # Step 7: Send summary alert
            self.alerter.send_summary(ticker, company_name, f"{quarter} {fiscal_year}", eval_results)

            # Mark as processed
            self._mark_processed(news_id, ticker, quarter, fiscal_year, pdf_url_r2)

            result["status"] = "completed"
            result["alerts"] = alerts_triggered
            logger.info(
                "Completed %s: %d evals, %d alerts",
                ticker, len(eval_results), len(alerts_triggered),
            )

        except Exception:
            logger.exception("Failed to process %s (%s)", ticker, news_id[:8])
            result["status"] = "failed"
            result["error"] = "See logs for details"

        return result

    def backfill(self, quarters: int = 8) -> list[dict[str, Any]]:
        """Backfill historical transcripts for all portfolio stocks.

        This fetches announcements going back ``quarters`` worth of time
        (approximately 2 years).
        """
        days_back = quarters * 95  # ~95 days per quarter
        results = []
        processed_ids = self._get_processed_ids()

        logger.info("Starting backfill: %d quarters (~%d days)", quarters, days_back)

        for ticker in self.config.portfolio_stocks:
            anns = self.bse.fetch_announcements(ticker, days_back=days_back)
            for ann in anns:
                if ann["news_id"] not in processed_ids:
                    result = self._process_single(ann)
                    results.append(result)

        logger.info("Backfill complete: %d transcripts processed", len(results))
        return results

    def search(self, query: str, limit: int = 10) -> dict:
        """Search across all indexed transcripts."""
        return self.ts.search("concall_transcripts", query, limit=limit)

    def get_stock_evaluations(self, ticker: str, limit: int = 20) -> list[dict]:
        """Get latest evaluations for a specific stock."""
        result = self.ts.search(
            "evaluations",
            query="",
            filters=f"ticker:={ticker.upper()}",
            limit=limit,
            sort_by="created_at:desc",
        )
        return result.get("hits", [])

    def get_stock_transcripts(self, ticker: str, limit: int = 10) -> list[dict]:
        """Get transcripts for a specific stock."""
        result = self.ts.search(
            "concall_transcripts",
            query="",
            filters=f"ticker:={ticker.upper()}",
            limit=limit,
            sort_by="created_at:desc",
        )
        return result.get("hits", [])


# ── Entry point for cron job ─────────────────────────────────────
def run_poll() -> None:
    """Entry point called by the cron job."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    engine = AlphaEngine()
    ensure_collections(engine.ts)
    results = engine.poll_and_process()

    triggered = [r for r in results if r.get("alerts")]
    logger.info(
        "Poll cycle complete: %d processed, %d with alerts",
        len(results), len(triggered),
    )


def run_backfill() -> None:
    """Entry point for initial backfill."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    engine = AlphaEngine()
    ensure_collections(engine.ts)
    results = engine.backfill(quarters=8)
    logger.info("Backfill complete: %d transcripts", len(results))


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "backfill":
        run_backfill()
    else:
        run_poll()