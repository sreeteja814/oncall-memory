"""Usage:
  python cli.py seed                   # load 12 months of incident history into Hindsight
  python cli.py triage "<alert text>"  # triage with memory
  python cli.py triage --no-memory "<alert>"
  python cli.py resolve                # log a resolved incident interactively (learning loop)
  python cli.py ask "<question>"       # reflect over the whole history
  python cli.py demo                   # before/after side by side
"""
import sys
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

load_dotenv()
import memory, agent, seed_data  # noqa: E402

console = Console()


def main(argv):
    if not argv:
        print(__doc__); return
    cmd, hs = argv[0], memory.client()
    memory.ensure_bank(hs)
    if cmd == "seed":
        for inc in seed_data.INCIDENTS:
            memory.retain_incident(hs, inc)
            console.print(f"[green]retained[/] {inc['id']} {inc['service']}")
    elif cmd == "triage":
        use_mem = "--no-memory" not in argv
        alert = [a for a in argv[1:] if not a.startswith("--")][0]
        ans, rec = agent.triage(alert, use_mem, hs)
        console.print(Panel(ans, title=f"triage (memory={'on' if use_mem else 'off'}, {len(rec)} memories)"))
    elif cmd == "ask":
        console.print(Panel(memory.reflect(hs, argv[1]), title="reflect"))
    elif cmd == "resolve":
        inc = {k: input(f"{k}: ") for k in ["id", "date", "service", "severity", "symptoms", "root_cause", "fix", "resolver"]}
        inc["ttr_minutes"] = int(input("ttr_minutes: "))
        inc["failed_attempts"] = input("failed_attempts (optional): ")
        agent.close_incident(inc, hs)
        console.print("[green]Retained. The next similar alert will know.[/]")
    elif cmd == "demo":
        alert = seed_data.DEMO_ALERT
        console.print(Panel(alert, title="LIVE ALERT"))
        a, _ = agent.triage(alert, use_memory=False)
        console.print(Panel(a, title="WITHOUT memory (generic)", border_style="red"))
        b, rec = agent.triage(alert, use_memory=True, hs=hs)
        console.print(Panel("\n".join(rec) or "(none)", title="Recalled from Hindsight", border_style="yellow"))
        console.print(Panel(b, title="WITH Hindsight memory", border_style="green"))
    else:
        print(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
