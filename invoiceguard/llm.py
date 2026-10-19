"""Optional explanation layer. Deterministic template by default; local Ollama only rephrases.
The LLM never computes or changes amounts/decisions: numbers come from tools and are verified."""
from __future__ import annotations

import json
import re
import urllib.request

from .data_gen import LABELS  # noqa: F401  (kept for UI imports)


def facts(state, policy: dict) -> dict:
    d = state.decision
    titles = {c["id"]: c["title"] for c in policy["clauses"]}
    return {"decision": d["decision"], "payable": d["payable"], "not_paid": d["not_paid"],
            "reasons": d["reasons"], "clauses": [f"{v['clause_id']} {titles.get(v['clause_id'], '')}" for v in d["clauses"].values()]}


def template_explanation(state, policy: dict) -> str:
    f = facts(state, policy)
    if not f["reasons"]:
        return f"Recommendation: {f['decision']}. All checks passed; payable INR {f['payable']}. No exceptions found."
    cl = "; ".join(dict.fromkeys(f["clauses"])) or "no clause"
    return (f"Recommendation: {f['decision']}. Findings: {', '.join(f['reasons'])}. Policy basis: {cl}. "
            f"Payable now INR {f['payable']}; INR {f['not_paid']} not paid pending resolution.")


def explain(state, policy: dict, use_llm: bool = False, model: str = "llama3.2") -> tuple[str, str]:
    base = template_explanation(state, policy)
    if not use_llm:
        return base, "deterministic template"
    try:
        body = json.dumps({"model": model, "stream": False, "prompt":
                           "Rewrite for an accounts-payable clerk in 3 plain sentences. Keep every number, code and "
                           "clause id exactly. Add nothing new.\n\n" + base}).encode()
        req = urllib.request.Request("http://localhost:11434/api/generate", body, {"Content-Type": "application/json"})
        text = json.loads(urllib.request.urlopen(req, timeout=4).read())["response"].strip()
        needed = re.findall(r"\d[\d,.]*\d|\d", base)
        if all(n in text for n in needed):
            return text, f"Ollama:{model} (numbers verified against tool output)"
        return base, "template (LLM output dropped: numbers did not match tool output)"
    except Exception:
        return base, "template (local LLM unavailable - deterministic fallback)"
