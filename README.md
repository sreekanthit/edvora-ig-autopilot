# Edvora Instagram Autopilot

Posts your Reels and carousels on a schedule, monitors results, and writes a plain-language "what to do next" report.
Uses the **official Instagram Graph API only** (no passwords, no scraping), so your account is not at risk of a ban for botting.

```
content/queue/*.json   ->  post-due  ->  Instagram
Instagram insights     ->  monitor   ->  data/ig.db  ->  report  ->  reports/latest.md
reports/latest.md      ->  generate  ->  new drafts (you approve)  ->  queue
```

## What it does / does not do
- DOES: publish approved Reels (local mp4 upload) and image carousels, respect a daily cap, never double-post, pull views/reach/shares/saves/watch time + followers daily, rank posts, suggest next steps, draft captions/scripts with Claude using your `ig-caption`, `ig-reel`, `ig-carousel` skills.
- DOES NOT: make the videos (put finished mp4/jpg files in `media/`), or post anything you have not set to `"status": "approved"`.
- Honest expectation: automation saves time; it does not by itself create views. Hook, shares and consistency do.

## One-time setup (about 30 minutes)
1. Switch the Instagram account to **Professional (Creator or Business)**.
2. At developers.facebook.com create an app, add **Instagram** -> *API setup with Instagram login*, add your account, and generate an access token with `instagram_business_basic`, `instagram_business_content_publish`, `instagram_business_manage_insights`. While the app is in development mode with your own account you can usually publish to it without app review; check Meta's current rules.
3. Copy `.env.example` to `.env`, fill in `IG_USER_ID` and `IG_ACCESS_TOKEN`.
4. Carousel images must be **JPEG on a public URL**. Easiest: make the repo public, commit images to `media/`, and set `PUBLIC_BASE_URL=https://raw.githubusercontent.com/<you>/<repo>/main/media`. Reels upload straight from your file (no public URL needed).
5. `pip install -r requirements.txt`, then try:
   ```
   export PYTHONPATH=.
   python -m src.autopilot limit          # confirms the token works
   python -m src.autopilot post-due --dry-run
   ```
6. GitHub: add repo secrets `IG_USER_ID`, `IG_ACCESS_TOKEN` and variable `PUBLIC_BASE_URL`. The workflow then runs every 30 min and daily at ~02:00 IST. Refresh the token about every 50 days: `python -m src.autopilot refresh-token`, then update the secret.

## Daily use
1. `python -m src.autopilot generate reel "Hello World in React Native"` (needs `ANTHROPIC_API_KEY`; copy your skill files into `skills/`).
2. Add your finished `media/xxx.mp4`, edit the draft JSON, set `"status": "approved"` and a `scheduled_at`.
3. Push. The autopilot posts it at that time, monitors it, and the next report tells you what to repeat.

## Guardrails built in
- `require_approval: true` by default; `max_posts_per_day: 2`; one post per run.
- Status is saved as `posting` before the API call; if anything crashes, the run stops and asks you to check instead of risking a double post.
- Failed posts are never retried automatically.
- Tokens only in `.env` / GitHub secrets (`.env` is git-ignored).

## Known limits
- Written from Meta's docs and tested with a mock Instagram only (`python -m unittest discover -s tests`). The first real post may need small fixes: the Reels resumable-upload headers and metric names (`views`, `reels_skip_rate`, ...) are marked "in development" by Meta and can change.
- GitHub scheduled runs can be delayed by several minutes.
- Instagram limits API posting (Meta's docs state 100 posts per 24h, but also 50 in one place); `limit` shows your real quota.
