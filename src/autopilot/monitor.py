import datetime as dt
from .db import conn
from .ig_api import IG

REEL_METRICS = ["views", "reach", "saved", "shares", "likes", "comments", "total_interactions",
                "ig_reels_avg_watch_time", "ig_reels_video_view_total_time", "reels_skip_rate"]
FEED_METRICS = ["views", "reach", "saved", "shares", "likes", "comments", "follows", "profile_visits", "total_interactions"]

def run(ig=None, db_path=None, limit=50):
    ig = ig or IG(); c = conn(db_path); now = dt.datetime.now(dt.timezone.utc).isoformat()
    f = ig.followers()
    c.execute("INSERT OR REPLACE INTO followers VALUES(?,?,?)", (now[:10], f.get("followers_count"), f.get("media_count")))
    n = 0
    for m in ig.recent_media(limit):
        kind = "REELS" if m.get("media_product_type") == "REELS" else "FEED"
        c.execute("INSERT OR REPLACE INTO media VALUES(?,?,?,?,?)", (m["id"], kind, m["timestamp"], m.get("caption") or "", m.get("permalink")))
        ins = ig.media_insights(m["id"], REEL_METRICS if kind == "REELS" else FEED_METRICS)
        for k, v in ins.items():
            if v is not None: c.execute("INSERT INTO metrics VALUES(?,?,?,?)", (m["id"], now, k, float(v)))
        n += 1
    c.commit(); print(f"Monitored {n} posts. Followers: {f.get('followers_count')}")
