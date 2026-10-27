import argparse
from . import settings
settings.load_dotenv()

def main():
    ap = argparse.ArgumentParser(prog="autopilot"); sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("post-due", help="post the next approved, due item"); p.add_argument("--dry-run", action="store_true")
    sub.add_parser("monitor", help="pull insights + followers into the local DB")
    sub.add_parser("report", help="write reports/latest.md from stored metrics")
    g = sub.add_parser("generate", help="draft a reel/carousel with Claude"); g.add_argument("kind", choices=["reel", "carousel"]); g.add_argument("topic")
    sub.add_parser("limit", help="show your API publishing quota")
    sub.add_parser("status", help="show queue")
    sub.add_parser("refresh-token", help="refresh the long-lived Instagram token (every ~50 days)")
    a = ap.parse_args()
    if a.cmd == "post-due":
        from .poster import post_due; raise SystemExit(post_due(a.dry_run))
    if a.cmd == "monitor": from . import monitor; monitor.run()
    elif a.cmd == "report": from . import analyze; analyze.run()
    elif a.cmd == "generate": from . import generate; generate.draft(a.kind, a.topic)
    elif a.cmd == "limit": from .ig_api import IG; print(IG().publishing_limit())
    elif a.cmd == "refresh-token": from .ig_api import IG; print(IG().refresh_token())
    elif a.cmd == "status":
        from . import queue as Q
        for i in Q.load_all(): print(f"{i['status']:9} {i['type']:9} {i['scheduled_at']}  {i['id']}")

if __name__ == "__main__": main()
