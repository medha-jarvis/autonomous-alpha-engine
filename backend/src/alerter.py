"""Telegram alert dispatcher."""

from __future__ import annotations

import json
import logging
from typing import Any

import requests

from prompts import UC_BY_NUMBER

logger = logging.getLogger(__name__)


class Alerter:
    """Sends formatted alerts to Telegram based on evaluation results."""

    def __init__(self, bot_token: str, chat_id: str) -> None:
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.chat_id = chat_id
        self.session = requests.Session()

    def send_message(self, text: str, parse_mode: str = "Markdown") -> bool:
        """Send a plain message to Telegram."""
        url = f"{self.base_url}/sendMessage"
        try:
            resp = self.session.post(
                url,
                json={
                    "chat_id": self.chat_id,
                    "text": text,
                    "parse_mode": parse_mode,
                    "disable_web_page_preview": True,
                },
                timeout=10,
            )
            resp.raise_for_status()
            return True
        except Exception:
            logger.exception("Failed to send Telegram message")
            return False

    def send_alert(
        self,
        ticker: str,
        uc_number: int,
        eval_result: dict[str, Any],
        company_name: str = "",
    ) -> bool:
        """Format and send an alert for a triggered evaluation."""
        uc = UC_BY_NUMBER.get(uc_number)
        if not uc or not uc.alert_message_template:
            return False

        result = eval_result.get("result", eval_result)
        if isinstance(result, str):
            try:
                result = json.loads(result)
            except (json.JSONDecodeError, TypeError):
                result = {}

        quotes = ""
        if isinstance(result.get("exact_quotes"), list):
            quotes = "\n".join(f"> {q}" for q in result["exact_quotes"][:2])

        # Format the alert template with actual values
        try:
            message = uc.alert_message_template.format(
                ticker=ticker,
                company=company_name or ticker,
                **result,
                quotes=quotes,
            )
        except (KeyError, ValueError):
            message = (
                f"*{uc.name}* for *{ticker}*\n"
                f"```json\n{json.dumps(result, indent=2)[:800]}\n```"
            )

        full_message = (
            f"🤖 *Alpha Engine Alert*\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"{message}\n"
            f"━━━━━━━━━━━━━━━━"
        )

        return self.send_message(full_message)

    def send_summary(
        self,
        ticker: str,
        company_name: str,
        quarter: str,
        eval_results: list[dict[str, Any]],
    ) -> bool:
        """Send a summary of all 20 evaluations for a transcript."""
        triggered = [r for r in eval_results if r.get("triggered") and not r.get("error")]
        total = len(eval_results)
        errors = [r for r in eval_results if r.get("error")]

        lines = [
            f"📄 *Alpha Engine — {company_name} ({ticker})*",
            f"📅 Quarter: {quarter}",
            f"━━━━━━━━━━━━━━━━",
            f"✅ Evaluations completed: {total}",
        ]

        if triggered:
            lines.append(f"🚨 *ALERTS: {len(triggered)}*")
            for tr in triggered:
                uc = UC_BY_NUMBER.get(tr.get("uc_number", 0))
                name = uc.name if uc else f"UC-{tr['uc_number']:02d}"
                lines.append(f"  ⚠️ UC-{tr['uc_number']:02d}: {name}")

        if errors:
            lines.append(f"❌ Errors: {len(errors)}")

        if not triggered and not errors:
            lines.append("✅ No alerts triggered.")

        return self.send_message("\n".join(lines))

    def send_daily_digest(self, alerts: list[dict[str, Any]]) -> bool:
        """Send a daily digest of all alerts across all stocks."""
        if not alerts:
            return self.send_message(
                "📊 *Alpha Engine Daily Digest*\n"
                "━━━━━━━━━━━━━━━━\n"
                "No alerts triggered today.\n"
                "Portfolio: All clear. ✅"
            )

        lines = [
            "📊 *Alpha Engine Daily Digest*",
            f"━━━━━━━━━━━━━━━━",
            f"🚨 *{len(alerts)} alert(s) today:*",
            "",
        ]
        for alert in alerts:
            ticker = alert.get("ticker", "?")
            uc_num = alert.get("uc_number", 0)
            uc = UC_BY_NUMBER.get(uc_num)
            name = uc.name if uc else f"UC-{uc_num}"
            lines.append(f"• *{ticker}* — {name}")

        return self.send_message("\n".join(lines))