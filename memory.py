"""Thin wrapper around Hindsight. All memory access in the app goes through here."""
import os
from datetime import datetime
from hindsight_client import Hindsight

BANK_ID = os.getenv("BANK_ID", "oncall-sre-team")

MISSION = (
    "I am the institutional memory of an on-call SRE team. I remember every incident: "
    "symptoms, root cause, the fix that worked, fixes that failed, and who resolved it. "
    "I prefer fixes that have actually worked before over generic advice, and I flag "
    "when a current alert looks like a repeat of a past incident."
)


def client() -> Hindsight:
    return Hindsight(
        base_url=os.getenv("HINDSIGHT_BASE_URL", "http://localhost:8888"),
        api_key=os.getenv("HINDSIGHT_API_KEY") or None,
        timeout=60.0,
    )


def ensure_bank(c: Hindsight) -> None:
    try:
        c.create_bank(
            bank_id=BANK_ID,
            name="On-call incident memory",
            mission=MISSION,
            disposition={"skepticism": 4, "literalism": 3, "empathy": 2},
        )
    except Exception:
        pass  # bank already exists


def retain_incident(c: Hindsight, inc: dict) -> None:
    """Store a resolved incident as a narrative so Hindsight can extract facts/entities."""
    text = (
        f"Incident {inc['id']} on service {inc['service']} (severity {inc['severity']}). "
        f"Symptoms: {inc['symptoms']} Root cause: {inc['root_cause']} "
        f"Fix that worked: {inc['fix']} "
        + (f"Attempted but failed: {inc['failed_attempts']} " if inc.get("failed_attempts") else "")
        + f"Resolved by {inc['resolver']} in {inc['ttr_minutes']} minutes."
    )
    c.retain(
        bank_id=BANK_ID,
        content=text,
        context="resolved production incident postmortem",
        timestamp=datetime.fromisoformat(inc["date"]),
        document_id=inc["id"],
        metadata={"service": inc["service"], "severity": inc["severity"]},
    )


def recall_context(c: Hindsight, alert: str, max_tokens: int = 2500) -> list[str]:
    """Reflect gives a grounded briefing (fixes, resolvers, failed attempts); recall adds raw facts."""
    out = []
    try:
        brief = c.reflect(
            bank_id=BANK_ID,
            query=(
                "Which past incidents resemble this alert? For each one, state the root cause, "
                "the exact fix that worked (with settings and values), who resolved it, "
                "and any attempts that failed."
            ),
            context=alert,
            budget="mid",
        ).text
        out.append(f"[reflection] {brief}")
    except Exception as e:  # noqa: BLE001
        print(f"reflect failed, falling back to recall only: {e}")
    res = c.recall(bank_id=BANK_ID, query=alert,
                   max_tokens=max_tokens, budget="mid")
    out += [f"[{r.type}] {r.text}" for r in res.results[:6]]
    return out


def reflect(c: Hindsight, question: str) -> str:
    return c.reflect(bank_id=BANK_ID, query=question, budget="mid").text
