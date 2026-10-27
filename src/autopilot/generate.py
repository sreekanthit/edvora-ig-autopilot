"""Draft content with Claude, using the ig-caption / ig-reel / ig-carousel SKILL.md files as instructions.
Drafts land in content/queue/ with status "draft". Nothing posts until YOU set status to "approved"."""
import datetime as dt, json, re
from .settings import ROOT, env, REPORTS, cfg
from . import queue as Q

def skill_text(name):
    p = ROOT / "skills" / name / "SKILL.md"
    return p.read_text() if p.exists() else ""

def draft(kind, topic, scheduled_at=None):
    import anthropic
    client = anthropic.Anthropic(api_key=env("ANTHROPIC_API_KEY", required=True))
    rep = REPORTS / "latest.md"; learn = rep.read_text()[:3000] if rep.exists() else "(no report yet)"
    skills = {"reel": ["ig-reel", "ig-caption"], "carousel": ["ig-carousel", "ig-caption"]}[kind]
    system = ("You write Instagram content for Edvora, an education/tech-news app for Indian students (Inter, B.Tech). "
              "Follow these skill instructions.\n\n" + "\n\n".join(skill_text(s) for s in skills) +
              "\n\nReply with ONLY a JSON object: {\"caption\": str, \"script\": str (reel voiceover or carousel slide copy), \"hook_options\": [str]}.")
    msg = client.messages.create(model=env("CLAUDE_MODEL", "claude-sonnet-5-5"), max_tokens=2000, system=system,
          messages=[{"role": "user", "content": f"Topic: {topic}\n\nWhat worked/failed recently:\n{learn}"}])
    text = msg.content[0].text; j = json.loads(re.search(r"\{.*\}", text, re.S).group(0))
    when = scheduled_at or (Q.now() + dt.timedelta(days=1)).isoformat()
    item = dict(id=f"{dt.date.today():%Y%m%d}-{kind}-{re.sub('[^a-z0-9]+','-',topic.lower())[:30]}", type=kind, status="draft",
                scheduled_at=when, caption=j["caption"], script=j.get("script"), hook_options=j.get("hook_options"),
                video_path=None if kind == "carousel" else "media/REPLACE_ME.mp4", images=[] if kind == "carousel" else None)
    Q.save(item); print("Draft saved:", item["id"], "- add the media, review, then set status to approved"); return item
