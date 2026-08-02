"""Asynchronous LLM evaluator — runs all 20 UC pipelines via OpenRouter."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

import aiohttp

from prompts import ALL_UC_TEMPLATES, UCTemplate
from template_engine import fill_template

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


class Evaluator:
    """Runs all 20 evaluation pipelines asynchronously against OpenRouter."""

    def __init__(
        self,
        api_key: str,
        model: str = "deepseek/deepseek-v4-flash",
        max_concurrent: int = 5,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def _call_llm(
        self,
        session: aiohttp.ClientSession,
        system_prompt: str,
        user_prompt: str,
    ) -> dict[str, Any]:
        """Call OpenRouter API with JSON mode."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://alpha-engine.local",
            "X-Title": "Autonomous Alpha Engine",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
            "max_tokens": 4096,
        }

        async with self.semaphore:
            for attempt in range(3):
                try:
                    async with session.post(
                        OPENROUTER_URL, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=120)
                    ) as resp:
                        if resp.status == 429:
                            retry_after = int(resp.headers.get("Retry-After", "5"))
                            logger.warning("Rate limited, waiting %ds", retry_after)
                            await asyncio.sleep(retry_after)
                            continue
                        resp.raise_for_status()
                        data = await resp.json()
                        content = data["choices"][0]["message"]["content"]
                        return json.loads(content)
                except asyncio.TimeoutError:
                    logger.warning("Timeout on attempt %d/3", attempt + 1)
                    await asyncio.sleep(2 ** attempt)
                except (json.JSONDecodeError, KeyError, aiohttp.ClientError) as e:
                    logger.warning("LLM error (attempt %d/3): %s", attempt + 1, e)
                    await asyncio.sleep(2 ** attempt)
            return {"error": f"Failed after 3 attempts"}

    async def evaluate(
        self,
        uc: UCTemplate,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Run a single evaluation use case.

        ``context`` must have the template variables the UC needs
        (e.g. ``current_text``, ``qa_text``, ``q_minus_1_json``, etc.)
        """
        # Ensure all template variables are present
        try:
            user_prompt = fill_template(uc.user_prompt_template, context)
        except KeyError as e:
            logger.warning(
                "Missing template variable %s for UC-%02d: %s",
                e, uc.number, uc.name,
            )
            return {
                "uc_number": uc.number,
                "uc_name": uc.name,
                "error": f"Missing context variable: {e}",
            }

        async with aiohttp.ClientSession() as session:
            result = await self._call_llm(session, uc.system_prompt, user_prompt)

        return {
            "uc_number": uc.number,
            "uc_name": uc.name,
            "result": result,
            "triggered": self._check_trigger(uc, result),
            "error": result.get("error"),
        }

    async def evaluate_all(
        self,
        context: dict[str, Any],
        uc_filter: list[int] | None = None,
    ) -> list[dict[str, Any]]:
        """Run ALL 20 evaluation pipelines in parallel.

        Optionally filter to specific UC numbers.
        """
        templates = [
            uc for uc in ALL_UC_TEMPLATES
            if uc_filter is None or uc.number in uc_filter
        ]

        tasks = [self.evaluate(uc, context) for uc in templates]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        final = []
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                final.append({
                    "uc_number": templates[i].number,
                    "uc_name": templates[i].name,
                    "error": str(r),
                    "result": {},
                    "triggered": False,
                })
            else:
                final.append(r)

        return final

    @staticmethod
    def _check_trigger(uc: UCTemplate, result: dict) -> bool:
        """Check if the evaluation result triggers an alert.

        Uses a simple JSON-path-like check for the trigger field.
        """
        if not uc.trigger_json_path:
            return False

        path = uc.trigger_json_path
        # Simple path parsing: "$.field" or "$.field[?(@.subfield == 'value')]"
        if path.startswith("$."):
            field = path[2:]
            # Handle array filter expressions
            if "[?(@." in field:
                base_field = field.split("[")[0]
                val = result.get(base_field)
                if isinstance(val, list):
                    for item in val:
                        if isinstance(item, dict):
                            # Check condition like field > 3 or field == "value"
                            cond = field.split("[?(@.")[1].rstrip(")]")
                            if ">=" in cond:
                                k, v = cond.split(">=")
                                if item.get(k.strip(), 0) >= float(v):
                                    return True
                            elif ">" in cond:
                                k, v = cond.split(">")
                                if item.get(k.strip(), 0) > float(v):
                                    return True
                            elif "==" in cond:
                                k, v = cond.split("==")
                                target = v.strip().strip("'\"")
                                if item.get(k.strip()) == target:
                                    return True
            else:
                val = result.get(field)
                if isinstance(val, bool):
                    return val
                if isinstance(val, (int, float)):
                    # For UC-02: evasiveness >= 7
                    if field == "evasiveness_score":
                        return val >= 7
                    if field == "credibility_score_pct":
                        return val < 65
                    return val > 0
                if isinstance(val, str):
                    return val in ("OBLIQUE_CUT", "HARD_CUT", "DETERIORATING_BARGAINING_POWER",
                                    "HIGH", "LOSING", "DECLINING", "SUSPICIOUS")
        return False


def build_context(
    transcript_data: dict[str, Any],
    previous_evals: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build the context dict for evaluation pipelines.

    ``transcript_data`` contains the current transcript fields.
    ``previous_evals`` contains evaluation results from previous quarters.
    """
    return {
        "current_text": transcript_data.get("full_text", ""),
        "text": transcript_data.get("full_text", ""),
        "qa_text": transcript_data.get("qa_section", ""),
        "current_intro": transcript_data.get("prepared_remarks", ""),
        "q_minus_1_json": json.dumps(previous_evals[-1] if previous_evals and len(previous_evals) > 0 else {}),
        "q_minus_4_json": json.dumps(previous_evals[-3] if previous_evals and len(previous_evals) > 3 else {}),
        "baseline_intros": json.dumps(previous_evals[-4:] if previous_evals else []),
        "historical_capex_json": json.dumps(previous_evals[-2:] if previous_evals else []),
        "ticker": transcript_data.get("ticker", ""),
        "historical_transcripts": json.dumps(previous_evals[-8:] if previous_evals else []),
    }