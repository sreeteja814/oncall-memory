# oncall-memory — an incident-response agent that remembers every outage

Most on-call copilots give the same generic advice ("check logs, restart pods") every time.
This one is backed by [Hindsight](https://hindsight.vectorize.io/) agent memory, so it recalls
*your team's* past incidents: root causes, fixes that worked, and fixes that **failed**.

## Where Hindsight is used
| Call | Where | Why |
|---|---|---|
| `create_bank(mission, disposition)` | `memory.ensure_bank` | Gives the bank an SRE identity; skeptical disposition |
| `retain(...)` with `timestamp`, `document_id` | `memory.retain_incident` | Each resolved incident is stored; Hindsight extracts facts, entities, and consolidates repeats into observations |
| `recall(...)` | `agent.triage` | Live alert -> semantic + keyword + graph + temporal retrieval of similar incidents |
| `reflect(...)` | `cli.py ask` | Cross-incident reasoning: "which services keep repeating failures?" |
| Learning loop | `agent.close_incident` | Every resolution is retained, so incident #N+1 is smarter |

## Run it
```bash
pip install -r requirements.txt
cp .env.example .env   # add Hindsight + Groq keys (Cloud promo: MEMHACK99)
python cli.py seed
python cli.py demo
python cli.py ask "Which services have repeated failures and what was the common cause?"
python cli.py resolve  # log a new incident, then re-run triage
```

## The demo story (60 seconds)
1. Alert on `invoice-api`: 504s, healthy pods, right after a deploy adding a job.
2. **Without memory:** generic checklist (restart pods, scale out).
3. **With memory:** recalls INC-1042 and INC-1103 (checkout-api pool exhaustion), suggests checking
   PgBouncer pool size and whether the new job bypasses it, and warns that restarts and scaling out
   failed before.
4. Run `resolve`, then triage a similar alert: the new fix is now in memory.

## Design notes
- Incidents are retained as narratives (not JSON) so Hindsight's extraction builds entity links across services.
- Failed attempts are retained explicitly; that is what lets the agent say what *not* to try.
- Groq calls retry with backoff and fall back to a second model to survive function/format errors.
