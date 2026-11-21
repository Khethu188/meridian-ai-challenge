"""Extract adviser notes into the Meridian proposal generator's JSON format."""

import json
import os
import re
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from jsonschema import validate

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

MODEL_NAME = "gemini-3.5-flash-lite"
VALID_MODELS = {"balanced", "global-growth", "income"}


def clean_data(value):
    """Remove null values and empty nested objects/lists without changing data."""
    if isinstance(value, dict):
        cleaned = {key: clean_data(item) for key, item in value.items() if item is not None}
        return {key: item for key, item in cleaned.items() if item not in ({}, [])}
    if isinstance(value, list):
        return [clean_data(item) for item in value if item is not None]
    return value


def _infer_client_type(notes: str, extracted: str = "") -> str | None:
    """Return only a client type supported by the generator and the notes."""
    text = f"{notes}\n{extracted}".lower()
    if re.search(r"\b(family\s+trust|unit\s+trust|trust account|trust client)\b", text):
        return "Trust"
    if re.search(r"\b(company|pty\s*ltd|proprietary limited|corporation|法人|entity)\b", text):
        return "Entity"
    if re.search(r"\b(individual|person|mr\.?|mrs\.?|ms\.?|miss)\b", text):
        return "Individual"
    return None


def _normalise_horizon(value: str) -> str | None:
    """Map a stated horizon to the generator's supported dropdown options."""
    match = re.search(r"\d+", value)
    if not match:
        return None
    years = int(match.group())
    if years >= 5:
        return "5 years+"
    if years >= 3:
        return "3 years+"
    if years >= 1:
        return "1 year+"
    return None


def apply_generator_mappings(proposal: dict, notes: str) -> dict:
    """Map extracted facts to the exact fields consumed by the Meridian UI."""
    notes_lower = notes.lower()
    goal = proposal.setdefault("goalAssessment", {})
    objective = proposal.setdefault("objective", {})
    strategy = proposal.setdefault("strategy", {})

    # Do not force every client to Individual. The generator supports all three.
    client_type = _infer_client_type(notes, str(goal.get("clientType") or ""))
    if client_type:
        goal["clientType"] = client_type

    # Keep the full adviser-stated horizon for the Goal Assessment text, while
    # mapping the separate dropdown field to one of its supported values.
    horizon = goal.get("investmentHorizon") or objective.get("investmentHorizon")
    if horizon:
        horizon = str(horizon).strip()
        goal["investmentHorizon"] = horizon
        dropdown_horizon = _normalise_horizon(horizon)
        if dropdown_horizon:
            objective["investmentHorizon"] = dropdown_horizon
        else:
            objective.pop("investmentHorizon", None)

    # Choose a model only where the notes clearly indicate one.
    if not proposal.get("applyModel"):
        if re.search(r"\bbalanced(?:[- ]ish)?\b", notes_lower):
            proposal["applyModel"] = "balanced"
        elif re.search(r"\b(global|offshore|international)\s+(equity|growth)|pure global equity", notes_lower):
            proposal["applyModel"] = "global-growth"
        elif re.search(r"\bincome\s+(portfolio|model|strategy)\b", notes_lower):
            proposal["applyModel"] = "income"

    # A bespoke/custom strategy should not also hydrate a predefined model.
    bespoke = any(term in notes_lower for term in ("bespoke", "custom", "tailored"))
    if bespoke:
        proposal.pop("applyModel", None)
        goal["portfolioModel"] = "__custom__"
        objective["targetReturnKey"] = "__custom__"
        strategy.setdefault("portfolioName", "Flexible Bespoke Portfolio")
        goal.setdefault("investmentStrategy", strategy["portfolioName"])

    # Copy the selected model label into the Goal Assessment only when present.
    model = proposal.get("applyModel")
    if model in VALID_MODELS:
        strategy.setdefault("model", model)

    # Preserve risk uncertainty. Do not convert "not a gambler" alone into a
    # confirmed risk category; use the actual notes' balanced wording if present.
    risk_text = str(goal.get("riskTolerance") or "").strip()
    risk_lower = risk_text.lower()
    balanced_signal = bool(re.search(r"\bbalanced(?:[- ]ish)?\b", notes_lower))
    cautious_signal = any(term in notes_lower for term in ("not a gambler", "risk-averse", "risk averse"))
    if balanced_signal and cautious_signal:
        objective["riskProfile"] = (
            "Balanced / moderate, pending confirmation. The client describes herself as risk-averse "
            "but wants capital growth. Confirm the risk profile once the investment horizon and "
            "income requirements have been established."
        )
        objective["riskProfileCategory"] = "Moderate"
    elif risk_lower:
        if "moderate" in risk_lower and ("aggressive" in risk_lower or "high" in risk_lower):
            objective["riskProfileCategory"] = "Moderately Aggressive"
        elif risk_lower == "moderate" or "moderate risk" in risk_lower:
            objective["riskProfileCategory"] = "Moderate"
        elif "aggressive" in risk_lower:
            objective["riskProfileCategory"] = "Aggressive"
        elif "conservative" in risk_lower:
            objective["riskProfileCategory"] = "Conservative"

    if objective.get("strategyChars") and not goal.get("strategyBullets"):
        goal["strategyBullets"] = objective["strategyChars"]

    stated_objective = goal.get("investmentObjective")
    growth = any(term in notes_lower for term in ("growth", "capital appreciation"))
    offshore = any(term in notes_lower for term in ("offshore", "overseas", "international"))
    if stated_objective:
        objective["investmentObjective"] = str(stated_objective)
    elif growth:
        objective["investmentObjective"] = "Long-term capital growth."
        goal["investmentObjective"] = "Long-term capital growth."

    if bespoke and not objective.get("strategyChars"):
        characteristics = []
        if growth:
            characteristics.append("Focus on long-term capital growth")
        if offshore:
            characteristics.append("Offshore exposure, as requested in the notes")
        if characteristics:
            objective["strategyChars"] = "\n".join(f"• {item}" for item in characteristics)

    if bespoke and not strategy.get("composition"):
        strategy["composition"] = (
            "Bespoke portfolio. Specific instruments and asset-class weights have not been provided "
            "and should be determined by the portfolio manager in line with the agreed objectives "
            "and confirmed risk tolerance."
        )

    if objective.get("targetReturn") and bespoke:
        objective["targetReturnKey"] = "__custom__"

    if goal.get("currency") and not strategy.get("currency"):
        strategy["currency"] = goal["currency"]

    # Amounts belong only in strategy.keyFigures. Migrate any legacy location.
    legacy_figures = goal.pop("keyFigures", {})
    if legacy_figures:
        strategy.setdefault("keyFigures", {}).update(legacy_figures)

    # Do not retain income drawdown when the notes explicitly say none is needed.
    if re.search(r"no\s+(current\s+)?income\s+(needed|required|requirement)|no\s+income\s+drawdown", notes_lower):
        key_figures = strategy.get("keyFigures", {})
        key_figures.pop("incomeValue", None)
        key_figures.pop("incomePct", None)
        if key_figures:
            strategy["keyFigures"] = key_figures
        else:
            strategy.pop("keyFigures", None)

    # Make missing information visible to the adviser rather than inventing it.
    existing_needs = str(proposal.get("needs") or "").strip()
    missing = []
    if not (strategy.get("keyFigures") or {}).get("totalInvestment") and re.search(
        r"(no firm number|didn.t give.{0,100}(number|amount)|amount.{0,40}(not confirmed|to be confirmed)|few million)", notes_lower
    ):
        missing.append("investment amount")
    if not (strategy.get("keyFigures") or {}).get("incomeValue") and not re.search(
        r"no\s+(current\s+)?income\s+(needed|required|requirement)", notes_lower
    ) and re.search(
        r"(?s)(didn.t give.{0,100}(monthly )?income|no (monthly )?income figure|income (figure|requirement).{0,40}(not confirmed|to be confirmed))", notes_lower
    ):
        missing.append("monthly income requirement")
    if not (goal.get("investmentHorizon") or objective.get("investmentHorizon")) and re.search(
        r"(?s)(no time horizon|didn.t give.{0,100}(time )?horizon|horizon.{0,40}(not confirmed|to be confirmed))", notes_lower
    ):
        missing.append("investment time horizon")

    if missing:
        confirmation = "[TO CONFIRM WITH CLIENT: " + ", ".join(missing) + ".]"
        if existing_needs:
            if confirmation not in existing_needs:
                proposal["needs"] = existing_needs.rstrip() + "\n\n" + confirmation
        else:
            proposal["needs"] = confirmation

    return clean_data(proposal)


def extract_proposal(notes: str) -> str:
    """Use Gemini to extract facts, map them to the generator and validate JSON."""
    if not isinstance(notes, str) or not notes.strip():
        raise ValueError("Please provide adviser notes.")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is missing from .env")

    client = genai.Client(api_key=api_key)
    prompt = f'''You are an accurate investment-proposal information extraction assistant.
Return ONE valid JSON object only. Do not use Markdown fences.

RULES
- Extract only information explicitly stated or unambiguously expressed. Never invent facts.
- Omit unknown fields. Never use null, empty strings or placeholders.
- Use strings for text and money/fee values. Allocation percentages must be numbers.
- Convert money to digit-only strings (R4.5 million -> "4500000", USD 1.2m -> "1200000").
- Do not convert monthly income to annual income.
- fees.advisorFee must be a numeric string without % (0.75% -> "0.75").
- Standardise "CPI plus five" as "CPI + 5%".
- Do not invent benchmark, asset allocations, instruments, holdings, platform, wrapper or mandate.
- If the adviser says no income is needed, do not create an income drawdown.
- If information is missing or deferred to a later meeting, explain it in "needs" and list the exact items to confirm.
- Distinguish stated facts from tentative impressions. Use wording such as "pending confirmation" for tentative risk descriptions.
- introGreetTo is "client" unless the notes explicitly say to address the advisor.

FIELD MAPPING
- clientName, clientEmail, introduction: client details and concise opening.
- needs: concise summary of known needs plus explicit [TO CONFIRM WITH CLIENT: ...] items for missing amount, income need, horizon or other key facts.
- goalAssessment.clientType: exactly Individual, Entity or Trust when supported by the notes.
- goalAssessment.mandateType, wrapper, currency: only if stated/unambiguous.
- goalAssessment.portfolioModel: "__custom__" for bespoke/custom/tailored; otherwise a named model ID only if explicitly selected.
- goalAssessment.investmentStrategy: strategy name or description supported by the notes.
- goalAssessment.investmentHorizon: full stated horizon, e.g. "10+ years" or "10-year+".
- goalAssessment.riskTolerance: preserve the stated risk wording; do not turn an informal phrase into a certain risk category.
- goalAssessment.investmentObjective: concise statement of the client's objective.
- goalAssessment.limitations, rationale: explicit constraints and concise rationale grounded in notes.
- objective.investmentHorizon: full stated horizon; the application maps it to its dropdown separately.
- objective.riskProfile: risk discussion, including uncertainty where applicable.
- objective.riskProfileCategory: only when supported; use a standard category if clearly indicated.
- objective.targetReturn, benchmark: only if explicitly stated.
- objective.investmentObjective, strategyChars: only supported by the notes.
- strategy.portfolioName: concise name grounded in the notes; do not invent a strategy model.
- strategy.currency: only if stated.
- strategy.keyFigures.totalInvestment: total initial investment as digits only.
- strategy.keyFigures.incomeValue: monthly income only if explicitly requested with an amount.
- strategy.composition, rationale: only supported by notes; do not fabricate holdings or percentages.
- strategy.allocation: include only explicitly stated asset-class percentages.
- fees.advisorFee, management, adminFee, brokerage: only stated fees.

Return only these possible fields (omit unknowns):
{{
  "clientName": "string",
  "clientEmail": "string",
  "introGreetTo": "client",
  "applyModel": "balanced | global-growth | income",
  "introduction": "string",
  "needs": "string",
  "goalAssessment": {{
    "clientType": "string", "mandateType": "string", "wrapper": "string",
    "currency": "string", "portfolioModel": "string", "investmentStrategy": "string",
    "investmentHorizon": "string", "riskTolerance": "string", "investmentObjective": "string",
    "limitations": "string", "rationale": "string", "strategyBullets": "string"
  }},
  "objective": {{
    "targetReturn": "string", "targetReturnKey": "string", "benchmark": "string",
    "riskProfileCategory": "string", "riskProfile": "string", "investmentHorizon": "string",
    "investmentObjective": "string", "strategyChars": "string"
  }},
  "strategy": {{
    "model": "string", "portfolioName": "string", "currency": "string",
    "composition": "string", "rationale": "string",
    "allocation": [{{"class": "string", "key": "string", "percent": 0}}],
    "keyFigures": {{"totalInvestment": "string", "incomeValue": "string"}}
  }},
  "fees": {{"management": "string", "advisorFee": "string", "adminFee": "string", "brokerage": "string"}}
}}

ADVISER NOTES:
{notes}
'''

    response = None
    for attempt in range(3):
        try:
            response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
            break
        except Exception as error:
            if "503" in str(error) and attempt < 2:
                print(f"Gemini is busy. Retrying ({attempt + 1}/2)...")
                time.sleep(5)
            else:
                raise

    if response is None or not response.text:
        raise ValueError("Gemini returned an empty response.")

    raw_text = response.text.strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.split("\n", 1)[1].removesuffix("```").strip()

    try:
        proposal = json.loads(raw_text)
    except json.JSONDecodeError as error:
        raise ValueError(f"Gemini returned invalid JSON: {error}") from error

    if not isinstance(proposal, dict):
        raise ValueError("Gemini response must be a JSON object.")

    proposal = clean_data(proposal)
    if proposal.get("introGreetTo") not in ("client", "advisor"):
        proposal["introGreetTo"] = "client"
    if proposal.get("applyModel") not in VALID_MODELS:
        proposal.pop("applyModel", None)

    proposal = apply_generator_mappings(proposal, notes)

    schema_path = BASE_DIR / "schema.json"
    if not schema_path.exists():
        raise FileNotFoundError("schema.json must be in the same folder as agent.py")
    with schema_path.open("r", encoding="utf-8") as file:
        schema = json.load(file)
    validate(instance=proposal, schema=schema)

    return json.dumps(proposal, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    sample_path = BASE_DIR / "sample-inputs" / "04-voice-note-transcript.txt"
    sample_notes = sample_path.read_text(encoding="utf-8")
    print(extract_proposal(sample_notes))
