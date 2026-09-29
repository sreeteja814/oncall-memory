"""On-call triage agent: Groq LLM + Hindsight memory."""
import os
import time
from openai import OpenAI
import memory

SYSTEM = (
    "You are an on-call SRE copilot. Given a live alert, output: 1) most likely root cause, "
    "2) first 3 actions in order, 3) what NOT to try. Be concise and concrete. "
    "If past incidents are provided, cite their IDs and reuse fixes that worked; do not "
    "repeat approaches recorded as failed. If none are relevant, say so and stay generic. "
    "When citing a past incident, quote the exact fix that worked (settings and values), the "
    "resolver's name, and any approach that failed. Prefer the most similar incident first. "
    "Only state settings, values and numbers that appear in the provided memory; never invent "
    "current values. If the memory does not say, tell the engineer to check the current value."
)


def llm() -> OpenAI:
    return OpenAI(base_url="https://api.groq.com/openai/v1", api_key=os.environ["GROQ_API_KEY"])


def chat(messages, retries: int = 3) -> str:
    """Groq models occasionally error on tool/format edge cases; retry with backoff, then fall back."""
    models = [os.getenv("LLM_MODEL", "openai/gpt-oss-120b"), "qwen/qwen3-32b"]
    last = None
    for model in models:
        for i in range(retries):
            try:
                r = llm().chat.completions.create(model=model, messages=messages, temperature=0.2)
                return r.choices[0].message.content or ""
            except Exception as e:  # noqa: BLE001
                last = e
                time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"LLM failed after retries: {last}")


def triage(alert: str, use_memory: bool = True, hs=None) -> tuple[str, list[str]]:
    recalled: list[str] = []
    user = f"Live alert:\n{alert}"
    if use_memory:
        hs = hs or memory.client()
        recalled = memory.recall_context(hs, alert)
        if recalled:
            user += "\n\nRelevant team memory (from Hindsight):\n" + \
                "\n".join(f"- {m}" for m in recalled)
    answer = chat([{"role": "system", "content": SYSTEM},
                  {"role": "user", "content": user}])
    return answer, recalled


def close_incident(inc: dict, hs=None) -> None:
    """The learning loop: every resolved incident becomes memory for the next one."""
    memory.retain_incident(hs or memory.client(), inc)
