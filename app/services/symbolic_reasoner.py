from __future__ import annotations

SELF_HARM_PATTERNS = ("kill myself", "suicide", "end it", "want to disappear", "not exist", "hurt myself")


def reason_about_message(text: str) -> dict[str, object]:
    """Deterministically convert high-risk language into facts and rule conclusions."""
    lowered = text.lower()
    facts: list[str] = []
    rules: list[str] = []
    conclusion = "NO_CRISIS_PROTOCOL"
    if any(pattern in lowered for pattern in SELF_HARM_PATTERNS):
        facts.append("EXPRESSES(user,self_harm_intent)")
        rules.append("EXPRESSES(x,self_harm_intent)->HIGH_RISK(x)")
        rules.append("HIGH_RISK(x)->CRISIS_PROTOCOL(x)")
        conclusion = "CRISIS_PROTOCOL"
    return {"facts": facts, "rules_triggered": rules, "conclusion": conclusion}
