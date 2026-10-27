import os, pathlib, yaml
ROOT = pathlib.Path(__file__).resolve().parents[2]
QUEUE = ROOT / "content" / "queue"
MEDIA = ROOT / "media"
DB = ROOT / "data" / "ig.db"
REPORTS = ROOT / "reports"

def cfg():
    with open(ROOT / "config.yaml") as f:
        return yaml.safe_load(f)

def env(name, default=None, required=False):
    v = os.environ.get(name, default)
    if required and not v:
        raise SystemExit(f"Missing environment variable {name} (see .env.example)")
    return v

def load_dotenv():
    p = ROOT / ".env"
    if p.exists():
        for line in p.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
