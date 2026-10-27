import datetime as dt, json, pathlib
from .settings import QUEUE, MEDIA, env

def _p(i): return QUEUE / f"{i}.json"

def load_all():
    items = []
    for p in sorted(QUEUE.glob("*.json")):
        d = json.loads(p.read_text()); d.setdefault("id", p.stem); items.append(d)
    return items

def save(item): _p(item["id"]).write_text(json.dumps(item, indent=2, ensure_ascii=False) + "\n")

def now(): return dt.datetime.now(dt.timezone.utc)

def parse_dt(s):
    d = dt.datetime.fromisoformat(s)
    return d if d.tzinfo else d.replace(tzinfo=dt.timezone(dt.timedelta(hours=5, minutes=30)))

def due(items, require_approval=True, at=None):
    at = at or now(); ok = {"approved"} if require_approval else {"approved", "draft"}
    c = [i for i in items if i.get("status") in ok and parse_dt(i["scheduled_at"]) <= at]
    return sorted(c, key=lambda i: parse_dt(i["scheduled_at"]))

def public_url(path):
    """Map a local file under ./media to a public URL (PUBLIC_BASE_URL/<relative path>)."""
    if str(path).startswith("http"): return path
    base = env("PUBLIC_BASE_URL", required=True).rstrip("/")
    rel = pathlib.Path(path).resolve().relative_to(MEDIA.resolve())
    return f"{base}/{rel.as_posix()}"
