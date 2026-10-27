import datetime as dt, json, os, sys, tempfile, unittest, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from src.autopilot import queue as Q, analyze, monitor, poster, db

class FakeIG:
    uid = "1"
    def __init__(self): self.reels = []; self.cars = []
    def publish_reel(self, caption, **k): self.reels.append(caption); return "M_REEL"
    def publish_carousel(self, caption, urls): self.cars.append(urls); return "M_CAR"
    def followers(self): return {"followers_count": 100, "media_count": 8}
    def recent_media(self, limit=50):
        out = []
        for i in range(8):
            ts = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=3 + i)).strftime("%Y-%m-%dT%H:%M:%S+0000")
            out.append({"id": f"m{i}", "caption": f"Hook {i}\nbody", "media_product_type": "REELS" if i % 2 else "FEED", "timestamp": ts, "permalink": f"https://ig/p/{i}"})
        return out
    def media_insights(self, mid, metrics):
        i = int(mid[1:]); return {"reach": 1000 + i * 100, "shares": i, "saved": i * 2, "likes": 50, "comments": 3, "views": 2000}

class T(unittest.TestCase):
    def test_monitor_and_report(self):
        p = os.path.join(tempfile.mkdtemp(), "t.db"); monitor.run(FakeIG(), p)
        text, scores = analyze.build(p)
        self.assertIn("Format comparison", text); self.assertEqual(len(scores), 8); self.assertIn("Do next", text)
    def test_due_selection(self):
        now = Q.now(); mk = lambda s, d: dict(id=s, status=s, scheduled_at=(now + dt.timedelta(hours=d)).isoformat())
        items = [mk("approved", -1), mk("draft", -1), dict(mk("approved", 5), id="future")]
        self.assertEqual([i["id"] for i in Q.due(items, True)], ["approved"])
    def test_poster_marks_posted_and_blocks_stuck(self):
        d = pathlib.Path(tempfile.mkdtemp()); Q.QUEUE = d; poster.Q.QUEUE = d
        import src.autopilot.queue as qq; qq.QUEUE = d
        item = dict(id="a", type="reel", status="approved", scheduled_at="2020-01-01T00:00:00+05:30", caption="hi", video_path="media/x.mp4")
        Q.save(item); fake = FakeIG(); poster.IG = lambda: fake
        self.assertEqual(poster.post_due(), 0)
        got = json.loads((d / "a.json").read_text()); self.assertEqual((got["status"], got["media_id"]), ("posted", "M_REEL"))
        Q.save(dict(id="b", type="reel", status="posting", scheduled_at="2020-01-01T00:00:00+05:30", caption="x"))
        self.assertEqual(poster.post_due(), 1)
if __name__ == "__main__": unittest.main()
