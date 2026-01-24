from __future__ import annotations

import os
import json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def generate_strategic_narrative(context_data: dict) -> dict:
    """
    Generates a high-impact Provincial Treasury persuasion insight.
    Returns JSON (dict).
    """

    system_prompt = """
You are a Chief Infrastructure Economist advising a PROVINCIAL TREASURY.

You are reviewing a provincial road funding request.
Your role is to translate engineering deterioration into fiscal risk and budget justification.

TONE:
- Professional, urgent, financially rigorous.
- Avoid fluffy language.
- Prefer terms like: "Deferred Maintenance Liability", "Asset Impairment", "Balance Sheet Risk", "Allocative Inefficiency".
- If the scenario shows deterioration/value destruction: frame as fiscal irresponsibility and growing contingent liability.
- If the scenario shows improvement/value preservation: frame as yield on investment and risk mitigation.

OUTPUT FORMAT (JSON ONLY):
{
  "headline": "A punchy 5–8 word headline",
  "executive_summary": "2 sentences: lead with the bottom-line fiscal impact.",
  "fiscal_implications": {
    "liability_growth": "How backlog/liability grows in Rand terms if ignored.",
    "economic_risk": "Impact on provincial logistics, jobs, GDP, service delivery."
  },
  "engineering_reality": "Translate VCI change into plain language road outcomes.",
  "recommendation": "Decisive recommendation to the Provincial Budget Committee."
}
""".strip()

    start_val = float(context_data.get("raw_start_asset_value", 0) or 0)
    end_val = float(context_data.get("raw_end_asset_value", 0) or 0)
    value_destroyed = start_val - end_val  # positive = destruction

    user_prompt = f"""
REVIEW THIS FUNDING SCENARIO:

PROJECT: {context_data.get('project_name')}
DURATION: {context_data.get('duration')} years

FINANCIALS:
- Proposed Spend (NPV): {context_data.get('total_cost')}
- Asset Value at Start: {context_data.get('current_asset_value')}
- Asset Value at End: {context_data.get('future_asset_value')}
- NET VALUE DESTRUCTION (Rand): {value_destroyed:,.0f}
  (Positive means value destroyed; negative means value gained/preserved.)

CONDITION (VCI 0-100):
- Start VCI: {context_data.get('start_vci')}
- End VCI: {context_data.get('end_vci')}
- Change: {context_data.get('vci_change')}

INSTRUCTIONS:
- If NET VALUE DESTRUCTION is high, describe it as an asset impairment and deferred maintenance liability.
- If End VCI drops below 40, explicitly warn of "network collapse risk" and service delivery disruption.
- Keep it short, hard-hitting, and treasury-friendly.
""".strip()

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.7,
        )
        content = response.choices[0].message.content
        return json.loads(content)

    except Exception as e:
        print(f"OpenAI Error: {e}")
        return {
            "headline": "AI Insight Unavailable",
            "executive_summary": "AI generation failed. Please check backend logs and API key configuration.",
            "fiscal_implications": {"liability_growth": "N/A", "economic_risk": "N/A"},
            "engineering_reality": "N/A",
            "recommendation": "Retry generation after resolving the backend error.",
        }