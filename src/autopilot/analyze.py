"""Turns stored metrics into a plain-language report. Rule-based heuristics, not guarantees."""
import collections, datetime as dt, statistics as st
from .db import conn
from .settings import cfg, REPORTS

IST = dt.timezone(dt.timedelta(hours=5, minutes=30))

def latest_rows(c):
    q = """SELECT m.media_id,m.kind,m.posted_at,m.caption,m.permalink,x.name,x.value FROM media m
           JOIN metrics x ON x.media_id=m.media_id
           WHERE x.fetched_at=(SELECT MAX(fetched_at) FROM metrics WHERE media_id=m.media_id)"""
    posts = {}
    for mid, kind, ts, cap, link, name, val in c.execute(q):
        p = posts.setdefault(mid, dict(id=mid, kind=kind, ts=dt.datetime.fromisoformat(ts.replace("Z", "+00:00").replace("+0000", "+00:00")), caption=cap, link=link))
        p[name] = val
    return list(posts.values())

def score(p):
    r = p.get("reach") or 0
    if r <= 0: return 0.0
    return (3 * (p.get("shares") or 0) + 2 * (p.get("saved") or 0) + (p.get("comments") or 0) + (p.get("likes") or 0) * 0.5) / r

def avg(xs): return round(st.mean(xs), 1) if xs else 0

def build(db_path=None, today=None):
    c = conn(db_path); today = today or dt.datetime.now(dt.timezone.utc)
    min_age = dt.timedelta(hours=cfg().get("min_post_age_hours_for_report", 48))
    posts = [p for p in latest_rows(c) if today - p["ts"] >= min_age]
    L = [f"# Edvora Instagram report - {today.astimezone(IST):%d %b %Y}", ""]
    fol = c.execute("SELECT day,followers FROM followers ORDER BY day").fetchall()
    if len(fol) >= 2: L += [f"**Followers:** {fol[0][1]} -> {fol[-1][1]} ({fol[-1][1]-fol[0][1]:+d}) between {fol[0][0]} and {fol[-1][0]}", ""]
    elif fol: L += [f"**Followers now:** {fol[-1][1]}", ""]
    if len(posts) < 5:
        L += [f"Only {len(posts)} posts are old enough to judge (need ~5+). Keep posting; this report gets useful with more data."]
        return "\n".join(L), []
    by_kind = collections.defaultdict(list)
    for p in posts: by_kind[p["kind"]].append(p)
    L += ["## Format comparison", "| Format | Posts | Avg reach | Avg shares | Avg saves | Avg score |", "|---|---|---|---|---|---|"]
    for k, ps in by_kind.items():
        L.append(f"| {k} | {len(ps)} | {avg([p.get('reach',0) for p in ps])} | {avg([p.get('shares',0) for p in ps])} | {avg([p.get('saved',0) for p in ps])} | {avg([score(p) for p in ps]):.3f} |")
    L += ["", "_score = (3*shares + 2*saves + comments + 0.5*likes) / reach. A rough heuristic that rewards shares and saves._", ""]
    hrs = collections.defaultdict(list)
    for p in posts: hrs[p["ts"].astimezone(IST).hour].append(p.get("reach", 0))
    good = sorted(((avg(v), h, len(v)) for h, v in hrs.items() if len(v) >= 2), reverse=True)[:3]
    L += ["## Best posting hours (IST)"] + ([f"- {h:02d}:00 - avg reach {a} ({n} posts)" for a, h, n in good] or ["- Not enough posts per hour yet (need 2+ per hour)."]) + [""]
    ranked = sorted(posts, key=score, reverse=True)
    def line(p): return f"- score {score(p):.3f} | reach {int(p.get('reach',0))} | {p['kind']} | \"{(p['caption'] or '').splitlines()[0][:70] if p['caption'] else ''}\" {p['link'] or ''}"
    L += ["## Top 3 (copy this hook style)"] + [line(p) for p in ranked[:3]] + ["", "## Bottom 3 (avoid)"] + [line(p) for p in ranked[-3:]] + [""]
    reels = by_kind.get("REELS", [])
    recs = []
    if reels:
        sk = [p["reels_skip_rate"] for p in reels if p.get("reels_skip_rate") is not None]
        if sk and avg(sk) > 50: recs.append("Skip rate is high: put the payoff or question in the first 2 seconds and cut the intro.")
        wt = [p["ig_reels_avg_watch_time"] / 1000 for p in reels if p.get("ig_reels_avg_watch_time")]
        if wt: recs.append(f"Average Reel watch time is {avg(wt)}s. Make Reels shorter than this plus a little, so more people watch to the end.")
    if avg([p.get("shares", 0) for p in posts]) < 1: recs.append("Shares are near zero: end posts with a send-to-a-friend ask (e.g. 'send this to your Maths friend').")
    if len(by_kind) == 2:
        a, b = sorted(by_kind.items(), key=lambda kv: -avg([score(p) for p in kv[1]]))
        recs.append(f"{a[0]} is scoring higher than {b[0]} for you right now; post more of {a[0]}, keep testing the other.")
    L += ["## Do next"] + [f"- {r}" for r in recs or ["Keep the current mix and keep testing hooks."]]
    return "\n".join(L), [score(p) for p in ranked]

def run():
    text, _ = build(); REPORTS.mkdir(exist_ok=True)
    out = REPORTS / f"{dt.date.today():%Y-%m-%d}.md"; out.write_text(text + "\n"); (REPORTS / "latest.md").write_text(text + "\n"); print(text)
