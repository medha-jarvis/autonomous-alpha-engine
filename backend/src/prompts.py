"""All 20 evaluation prompt templates for the Autonomous Alpha Engine."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class UCTemplate:
    """A single use-case evaluation template."""

    number: int
    name: str
    system_prompt: str
    user_prompt_template: str
    trigger_json_path: str | None = None
    alert_message_template: str | None = None


# ── UC-01: Guidance Delta & Trajectory Shift Engine ────────────────
UC01 = UCTemplate(
    number=1,
    name="Guidance Delta & Trajectory Shift Engine",
    system_prompt="You are a forensic buy-side equity analyst. Output strictly in JSON format.",
    user_prompt_template="""Compare the current quarter commentary against previous quarters to detect guidance shifts.

[CURRENT TEXT]: {current_text}
[Q-1 JSON GUIDANCE]: {q_minus_1_json}
[Q-4 JSON GUIDANCE]: {q_minus_4_json}

Task:
1. Extract current Guidance for Revenue Growth (%), Margin (%), Capex, and Volume.
2. Compare against baseline guidance.
3. Classify overall Guidance Direction as: "HARD_UPGRADE", "SOFT_UPGRADE", "MAINTAINED", "OBLIQUE_CUT", or "HARD_CUT".

JSON Schema to return exactly:
{
  "current_guidance": {"revenue": "", "margin": "", "capex": "", "volume": ""},
  "guidance_direction": "string",
  "delta_summary": "string",
  "exact_quotes": ["string"]
}""",
    trigger_json_path="$.guidance_direction",
    alert_message_template="🚨 *GUIDANCE CUT*: {ticker}\nDirection: {guidance_direction}\nSummary: {delta_summary}\nQuotes: {quotes}",
)


# ── UC-02: Management Evasiveness & Q&A Hostility Index ───────────
UC02 = UCTemplate(
    number=2,
    name="Management Evasiveness & Q&A Hostility Index",
    system_prompt="You are a behavioral financial analyst. Output strictly in JSON format.",
    user_prompt_template="""Analyze the Q&A section for management evasiveness.

[Q&A TEXT]: {qa_text}

Task:
1. Identify instances where management dodged a direct quantitative question.
2. Calculate "evasiveness_score" (1-10, where 10 is highly evasive).
3. Count defensive phrases ("as you know", "we don't break this down", "noise").

JSON Schema:
{
  "evasiveness_score": 0,
  "defensive_phrase_count": 0,
  "dodged_topics": ["string"],
  "worst_exchange": {"analyst": "string", "management": "string", "why_evasive": "string"}
}""",
    trigger_json_path="$.evasiveness_score",
    alert_message_template="⚠️ *HIGH EVASIVENESS*: {ticker}\nScore: {evasiveness_score}/10\nDodged: {dodged_topics}",
)


# ── UC-03: Safe Harbor & Risk Factor Delta Scanner ────────────────
UC03 = UCTemplate(
    number=3,
    name="Safe Harbor & Risk Factor Delta Scanner",
    system_prompt="You are a corporate risk auditor. Output strictly JSON.",
    user_prompt_template="""Compare current opening remarks against historical baselines.

[CURRENT INTRO]: {current_intro}
[PREVIOUS 4 QTR INTROS]: {baseline_intros}

Task:
1. Identify new risk factors or macro warnings introduced for the first time.
2. Filter standard legal jargon; focus on business-specific shifts (e.g., "red sea delays", "inventory write-downs").

JSON Schema:
{
  "new_risk_phrases_found": true/false,
  "extracted_new_risks": [{"phrase": "string", "business_impact": "string"}]
}""",
    trigger_json_path="$.new_risk_phrases_found",
    alert_message_template="⚠️ *NEW RISK FACTORS*: {ticker}\n{extracted_new_risks}",
)


# ── UC-04: Capex & Capacity Milestone Audit ──────────────────────
UC04 = UCTemplate(
    number=4,
    name="Capex & Capacity Milestone Audit",
    system_prompt="You are an industrial project auditor. Output strictly JSON.",
    user_prompt_template="""Audit all Capital Expenditure (Capex) projects.

[TEXT]: {text}
[HISTORICAL TRACKER DB]: {historical_capex_json}

Task:
1. Extract Project Name, Capacity, Capex (INR Cr), Target Date, Status.
2. Compare Target Date against historical dates. Compute delay in months.

JSON Schema:
{
  "capex_projects": [{
      "project_name": "string",
      "capex_inr_cr": 0,
      "original_target_date": "string",
      "current_target_date": "string",
      "delay_months": 0,
      "status": "string"
  }]
}""",
    trigger_json_path="$.capex_projects[?(@.delay_months > 3)]",
    alert_message_template="🚧 *CAPEX DELAY*: {ticker}\nProject: {project_name}\nDelay: {delay_months} months",
)


# ── UC-05: Cash Flow vs. Revenue Divergence Signal ────────────────
UC05 = UCTemplate(
    number=5,
    name="Cash Flow vs. Revenue Divergence Signal",
    system_prompt="You are a forensic accountant. Output strictly JSON.",
    user_prompt_template="""Analyze working capital and cash flow commentary.

[TEXT]: {text}

Task:
1. Extract comments on Debtor Days, Inventory, and Operating Cash Flow.
2. Classify driver as: "STRATEGIC_BUILDUP", "DETERIORATING_BARGAINING_POWER", or "NEUTRAL".

JSON Schema:
{
  "working_capital_driver": "string",
  "debtor_days_commentary": "string",
  "red_flag_detected": true/false,
  "explanation": "string"
}""",
    trigger_json_path="$.working_capital_driver",
    alert_message_template="🔴 *WORKING CAPITAL WARNING*: {ticker}\nDriver: {working_capital_driver}\n{explanation}",
)


# ── UC-06: Raw Material Pass-Through & Margin Trajectory ──────────
UC06 = UCTemplate(
    number=6,
    name="Raw Material Pass-Through & Margin Trajectory",
    system_prompt="You are a commodity & margin analyst. Output JSON only.",
    user_prompt_template="""Analyze raw material pass-through.

[TEXT]: {text}

Task:
1. Identify key raw materials.
2. Extract pricing power rating: "IMMEDIATE_PASS_THROUGH", "LAGGED_PASS_THROUGH", "NO_PASS_THROUGH".

JSON Schema:
{
  "key_raw_materials": ["string"],
  "pricing_power_rating": "string",
  "gross_margin_outlook": "EXPANDING|STABLE|COMPRESSING"
}""",
    alert_message_template="📊 *MARGIN PRESSURE*: {ticker}\nPricing Power: {pricing_power_rating}\nMargin Outlook: {gross_margin_outlook}",
)


# ── UC-07: Cross-Company Supply Chain Echo Engine ─────────────────
UC07 = UCTemplate(
    number=7,
    name="Cross-Company Supply Chain Echo Engine",
    system_prompt="You are a macro sector analyst. Output JSON only.",
    user_prompt_template="""Extract sector-level demand signals and competitor mentions.

[TEXT]: {text}
[TICKER]: {ticker}

Task:
1. Extract demand trends for specific sectors mentioned by management.
2. Extract mentions of other entities (competitors, customers).

JSON Schema:
{
  "source_ticker": "string",
  "sector_echoes": [{"target_sector": "string", "demand_trend": "ACCELERATING|STABLE|DECELERATING", "quote": "string"}],
  "mentioned_entities": [{"entity_name": "string", "context": "string", "sentiment": "POSITIVE|NEGATIVE|NEUTRAL"}]
}""",
    trigger_json_path="$.sector_echoes[?(@.demand_trend == 'DECELERATING')]",
    alert_message_template="📉 *SECTOR DECELERATION*: {ticker}\nSector: {target_sector}\nQuote: {quote}",
)


# ── UC-08: Legal, Regulatory, Tax & Auditor Scanner ───────────────
UC08 = UCTemplate(
    number=8,
    name="Legal, Regulatory, Tax & Auditor Scanner",
    system_prompt="You are a corporate legal analyst. Output JSON only.",
    user_prompt_template="""Screen for regulatory, tax, or auditor issues.

[TEXT]: {text}

Task:
1. Extract mentions of litigation, tax demands, GST notices, NGT issues, USFDA observations, auditor remarks.
2. Estimate financial exposure.

JSON Schema:
{
  "regulatory_legal_issues_found": true/false,
  "issues": [{"authority": "string", "nature_of_issue": "string", "financial_exposure_inr_cr": 0, "mitigation": "string"}]
}""",
    trigger_json_path="$.regulatory_legal_issues_found",
    alert_message_template="🔴🚨 *LEGAL/REGULATORY ISSUE*: {ticker}\n{issues}",
)


# ── UC-09: Key Personnel (KMP) Turnover Alert ─────────────────────
UC09 = UCTemplate(
    number=9,
    name="Key Personnel (KMP) Turnover Alert",
    system_prompt="You are a governance analyst. Output JSON only.",
    user_prompt_template="""Scan for KMP changes.

[TEXT]: {text}

Task:
1. Identify resignation/appointment of CFO, CEO, COO, Auditor.
2. Classify as "ROUTINE" or "SUSPICIOUS" (sudden, personal reasons).

JSON Schema:
{
  "kmp_change_detected": true/false,
  "changes": [{"person": "string", "designation": "string", "event_type": "string", "classification": "ROUTINE|SUSPICIOUS"}]
}""",
    trigger_json_path="$.changes[?(@.classification == 'SUSPICIOUS')]",
    alert_message_template="🔴 *KMP TURNOVER*: {ticker}\n{changes}",
)


# ── UC-10: Product Mix & Premiumization Tracker ──────────────────
UC10 = UCTemplate(
    number=10,
    name="Product Mix & Premiumization Tracker",
    system_prompt="You are a fundamental analyst. Output JSON only.",
    user_prompt_template="""Analyze product mix and exports.

[TEXT]: {text}

Task:
1. Extract % contribution of Value-Added/High-Margin products.
2. Determine if Mix is "IMPROVING", "STABLE", or "DETERIORATING".

JSON Schema:
{
  "high_margin_share_pct": 0,
  "export_share_pct": 0,
  "mix_direction": "IMPROVING|STABLE|DETERIORATING"
}""",
    alert_message_template="📊 *MIX DETERIORATION*: {ticker}\nMix Direction: {mix_direction}\nHigh Margin: {high_margin_share_pct}% | Export: {export_share_pct}%",
)


# ── UC-11: Order Book Velocity & Execution Visibility ────────────
UC11 = UCTemplate(
    number=11,
    name="Order Book Velocity & Execution Visibility",
    system_prompt="You are a capital goods analyst. Output JSON only.",
    user_prompt_template="""Extract order book metrics.

[TEXT]: {text}

Task:
1. Extract Order Book (INR Cr), Fresh Inflow (INR Cr), L1 Pipeline.
2. Compute visibility in months and book-to-bill ratio.

JSON Schema:
{
  "total_order_book_inr_cr": 0,
  "quarterly_inflow_inr_cr": 0,
  "visibility_months": 0,
  "book_to_bill_ratio": 0,
  "inflow_trend": "GROWING|FLAT|DECLINING"
}""",
    trigger_json_path="$.inflow_trend",
    alert_message_template="📉 *ORDER INFLOW DECLINING*: {ticker}\nInflow: {quarterly_inflow_inr_cr} Cr | Book-to-Bill: {book_to_bill_ratio}",
)


# ── UC-12: Competitive Threat & Market Share Dynamics ────────────
UC12 = UCTemplate(
    number=12,
    name="Competitive Threat & Market Share Dynamics",
    system_prompt="You are a strategy analyst. Output JSON only.",
    user_prompt_template="""Analyze competitive intensity.

[TEXT]: {text}

Task:
1. Assess Competitive Intensity: "LOW", "MODERATE", "HIGH".
2. Extract Market Share Trajectory: "GAINING", "STABLE", "LOSING".
3. Identify specific threats (e.g. Chinese imports).

JSON Schema:
{
  "competitive_intensity": "LOW|MODERATE|HIGH",
  "market_share_trajectory": "GAINING|STABLE|LOSING",
  "threat_sources": ["string"]
}""",
    trigger_json_path="$.market_share_trajectory",
    alert_message_template="🔴 *MARKET SHARE LOSS*: {ticker}\nThreats: {threat_sources}",
)


# ── UC-13: Promoter Credibility & Historical Promise Audit ────────
UC13 = UCTemplate(
    number=13,
    name="Promoter Credibility & Historical Promise Audit",
    system_prompt="You are an activist investor. Output JSON only.",
    user_prompt_template="""Audit historical promises.

[8-QTR TRANSCRIPTS]: {historical_transcripts}

Task:
1. Identify explicit promises made 4-8 quarters ago (growth, debt, capex).
2. Check actual outcomes in recent quarters.
3. Assign Credibility Score (0-100%).

JSON Schema:
{
  "credibility_score_pct": 0,
  "promises_audited": [{"promise": "string", "actual_outcome": "string", "status": "FULFILLED|MISSED"}]
}""",
    alert_message_template="👤 *PROMOTER CREDIBILITY*: {ticker}\nScore: {credibility_score_pct}%\nKept: {kept_count}|Missed: {missed_count}",
)


# ── UC-14: Customer Concentration & Client Loss Radar ─────────────
UC14 = UCTemplate(
    number=14,
    name="Customer Concentration & Client Loss Radar",
    system_prompt="You are an equity analyst. Output JSON only.",
    user_prompt_template="""Analyze client concentration risk.

[TEXT]: {text}

Task:
1. Extract Top 1/5/10 client revenue share (%).
2. Classify Churn Risk: "NONE", "MODERATE", "HIGH".

JSON Schema:
{
  "top_5_client_share_pct": 0,
  "client_churn_risk": "NONE|MODERATE|HIGH",
  "findings": "string"
}""",
    trigger_json_path="$.client_churn_risk",
    alert_message_template="🔴 *CLIENT CONCENTRATION RISK*: {ticker}\nTop-5 Share: {top_5_client_share_pct}%\nRisk: {client_churn_risk}",
)


# ── UC-15: R&D Pipeline & Patent Velocity ────────────────────────
UC15 = UCTemplate(
    number=15,
    name="R&D Pipeline & Patent Velocity",
    system_prompt="You are a pharma/specialty chemical analyst. Output JSON.",
    user_prompt_template="""Analyze R&D pipeline.

[TEXT]: {text}

Task:
1. Extract R&D spend % and new SKUs launched.
2. Determine Innovation Velocity: "ACCELERATING", "STABLE", "LAGGING".

JSON Schema:
{
  "rd_spend_pct_sales": 0,
  "new_skus_launched_count": 0,
  "innovation_velocity": "ACCELERATING|STABLE|LAGGING"
}""",
)


# ── UC-16: Debt Structure & Covenant Watch ───────────────────────
UC16 = UCTemplate(
    number=16,
    name="Debt Structure & Covenant Watch",
    system_prompt="You are a credit risk analyst. Output JSON only.",
    user_prompt_template="""Analyze leverage commentary.

[TEXT]: {text}

Task:
1. Extract Gross Debt, Net Debt, Cost of Debt.
2. Classify Debt Trajectory: "DELEVERAGING", "STABLE", "LEVERAGING".
3. Check for financial stress or covenant breaches.

JSON Schema:
{
  "net_debt_inr_cr": 0,
  "debt_trajectory": "DELEVERAGING|STABLE|LEVERAGING",
  "financial_stress_flag": true/false
}""",
    trigger_json_path="$.financial_stress_flag",
    alert_message_template="🔴 *FINANCIAL STRESS*: {ticker}\nNet Debt: {net_debt_inr_cr} Cr\nTrajectory: {debt_trajectory}",
)


# ── UC-17: ESG, Labor & Operational Disturbance ─────────────────
UC17 = UCTemplate(
    number=17,
    name="ESG, Labor & Operational Disturbance",
    system_prompt="You are an operational auditor. Output JSON only.",
    user_prompt_template="""Scan for operational disruptions.

[TEXT]: {text}

Task:
1. Identify plant shutdowns, strikes, accidents, pollution notices.
2. Extract days lost and financial impact.

JSON Schema:
{
  "operational_disruption_found": true/false,
  "disruption_details": {"type": "string", "days_lost": 0}
}""",
    trigger_json_path="$.operational_disruption_found",
    alert_message_template="🔴 *OPERATIONAL DISRUPTION*: {ticker}\n{disruption_details}",
)


# ── UC-18: Subsidiary & JV Drag Probe ────────────────────────────
UC18 = UCTemplate(
    number=18,
    name="Subsidiary & JV Drag Probe",
    system_prompt="You are a corporate structuring analyst. Output JSON only.",
    user_prompt_template="""Analyze subsidiary drag.

[TEXT]: {text}

Task:
1. Compare Standalone vs Conso divergence.
2. List drag subsidiaries and promised breakeven timelines.

JSON Schema:
{
  "standalone_vs_conso_divergence": "CONSO_WEAKER|CONSO_STRONGER|ALIGNED",
  "drag_subsidiaries": [{"entity": "string", "breakeven_timeline": "string"}]
}""",
)


# ── UC-19: Subsidy & PLI Scheme Dependency ───────────────────────
UC19 = UCTemplate(
    number=19,
    name="Subsidy & PLI Scheme Dependency",
    system_prompt="You are a policy analyst. Output JSON only.",
    user_prompt_template="""Analyze PLI/Subsidy reliance.

[TEXT]: {text}

Task:
1. Extract PLI incentive accrued.
2. Classify Policy Risk Level: "LOW", "MODERATE", "HIGH".

JSON Schema:
{
  "pli_accrued_inr_cr": 0,
  "policy_risk_level": "LOW|MODERATE|HIGH"
}""",
)


# ── UC-20: Analyst Probing Radar & Repetition Index ──────────────
UC20 = UCTemplate(
    number=20,
    name="Analyst Probing Radar & Repetition Index",
    system_prompt="You are a behavioral metadata extractor. Output JSON only.",
    user_prompt_template="""Analyze Q&A topic concentration.

[Q&A TEXT]: {qa_text}

Task:
1. Categorize all questions into core subjects.
2. Count distinct analysts probing the same subject.
3. Identify if analysts expressed explicit skepticism.

JSON Schema:
{
  "high_probe_topics": [{"topic": "string", "distinct_analysts_count": 0, "analyst_skepticism_detected": true/false}]
}""",
    trigger_json_path="$.high_probe_topics[?(@.distinct_analysts_count >= 3)]",
    alert_message_template="🔍 *HIGH ANALYST PROBE*: {ticker}\nTopic: {topic}\nAnalysts: {distinct_analysts_count}",
)


# ── Master List ──────────────────────────────────────────────────
ALL_UC_TEMPLATES: list[UCTemplate] = [
    UC01, UC02, UC03, UC04, UC05,
    UC06, UC07, UC08, UC09, UC10,
    UC11, UC12, UC13, UC14, UC15,
    UC16, UC17, UC18, UC19, UC20,
]

UC_BY_NUMBER: dict[int, UCTemplate] = {uc.number: uc for uc in ALL_UC_TEMPLATES}


def get_alert_threshold(uc_template: UCTemplate) -> str | None:
    """Return the JSON path to check for alert triggering."""
    return uc_template.trigger_json_path