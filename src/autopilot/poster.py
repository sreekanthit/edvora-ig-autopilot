import datetime as dt
from . import queue as Q
from .ig_api import IG, IGError
from .settings import cfg, ROOT

def post_due(dry_run=False, max_per_run=1):
    c = cfg(); items = Q.load_all()
    posted_today = [i for i in items if i.get("status") == "posted" and Q.parse_dt(i.get("posted_at", "1970-01-01T00:00:00+00:00")) > Q.now() - dt.timedelta(hours=24)]
    stuck = [i for i in items if i.get("status") == "posting"]
    if stuck:
        print("STOP: items stuck in 'posting' (check Instagram manually, then set status to posted/approved):", [i["id"] for i in stuck]); return 1
    room = c["max_posts_per_day"] - len(posted_today)
    todo = Q.due(items, c["require_approval"])[:max(0, min(room, max_per_run))]
    if not todo: print("Nothing due."); return 0
    ig = None if dry_run else IG()
    for it in todo:
        print(f"-> {it['type']} {it['id']}")
        if dry_run: continue
        it["status"] = "posting"; Q.save(it)      # saved BEFORE the call, so a crash can never double-post
        try:
            if it["type"] == "reel":
                vp = it.get("video_path"); vp = str(ROOT / vp) if vp else None
                mid = ig.publish_reel(it["caption"], video_url=it.get("video_url"), video_path=vp,
                                      trial=c.get("trial_reels_first", False), cover_url=it.get("cover_url"))
            elif it["type"] == "carousel":
                mid = ig.publish_carousel(it["caption"], [Q.public_url(p if str(p).startswith("http") else ROOT / p) for p in it["images"]])
            else: raise IGError(f"unknown type {it['type']}")
            it.update(status="posted", media_id=mid, posted_at=Q.now().isoformat(), error=None)
        except Exception as e:
            it.update(status="failed", error=str(e)[:500])   # never auto-retry
            print("FAILED:", e)
        Q.save(it)
    return 0
