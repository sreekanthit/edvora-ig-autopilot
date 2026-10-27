"""Thin client for the official Instagram Graph API (Instagram Login). No scraping, no passwords."""
import json, os, time, requests
from .settings import env, MEDIA

class IGError(Exception): pass

class IG:
    def __init__(self, user_id=None, token=None, version=None, host=None):
        self.uid = user_id or env("IG_USER_ID", required=True)
        self.token = token or env("IG_ACCESS_TOKEN", required=True)
        self.ver = version or env("IG_API_VERSION", "v23.0")
        self.host = (host or env("IG_GRAPH_HOST", "https://graph.instagram.com")).rstrip("/")

    # ---- low level ----
    def _req(self, method, path, params=None, **kw):
        p = dict(params or {}); p["access_token"] = self.token
        r = requests.request(method, f"{self.host}/{self.ver}/{path.lstrip('/')}", params=p if method == "GET" else None,
                             data=p if method == "POST" else None, timeout=120, **kw)
        try: j = r.json()
        except Exception: raise IGError(f"HTTP {r.status_code}: {r.text[:300]}")
        if r.status_code >= 400 or "error" in j: raise IGError(json.dumps(j.get("error", j)))
        return j

    def wait_finished(self, container_id, tries=10, delay=30):
        for _ in range(tries):
            s = self._req("GET", container_id, {"fields": "status_code,status"})
            code = s.get("status_code")
            if code == "FINISHED": return
            if code in ("ERROR", "EXPIRED"): raise IGError(f"container {container_id}: {s}")
            time.sleep(delay)
        raise IGError(f"container {container_id} not FINISHED in time")

    def _publish(self, container_id):
        return self._req("POST", f"{self.uid}/media_publish", {"creation_id": container_id})["id"]

    # ---- publishing ----
    def publish_reel(self, caption, video_url=None, video_path=None, share_to_feed=True, trial=False, cover_url=None):
        d = {"media_type": "REELS", "caption": caption, "share_to_feed": str(bool(share_to_feed)).lower()}
        if cover_url: d["cover_url"] = cover_url
        if trial: d["trial_params"] = json.dumps({"graduation_strategy": "MANUAL"})
        if video_url: d["video_url"] = video_url
        else: d["upload_type"] = "resumable"
        cid = self._req("POST", f"{self.uid}/media", d)["id"]
        if not video_url:
            size = os.path.getsize(video_path)
            with open(video_path, "rb") as f:
                r = requests.post(f"https://rupload.facebook.com/ig-api-upload/{self.ver}/{cid}",
                                  headers={"Authorization": f"OAuth {self.token}", "offset": "0", "file_size": str(size)},
                                  data=f, timeout=600)
            if r.status_code >= 400: raise IGError(f"resumable upload failed: {r.status_code} {r.text[:300]}")
        self.wait_finished(cid)
        return self._publish(cid)

    def publish_carousel(self, caption, image_urls):
        if not 2 <= len(image_urls) <= 20: raise IGError("carousel needs 2-20 images")
        kids = []
        for u in image_urls:
            kids.append(self._req("POST", f"{self.uid}/media", {"image_url": u, "is_carousel_item": "true"})["id"])
        for k in kids: self.wait_finished(k, tries=6, delay=10)
        cid = self._req("POST", f"{self.uid}/media", {"media_type": "CAROUSEL", "children": ",".join(kids), "caption": caption})["id"]
        self.wait_finished(cid)
        return self._publish(cid)

    def publishing_limit(self):
        return self._req("GET", f"{self.uid}/content_publishing_limit", {"fields": "quota_usage,config"})

    # ---- reading ----
    def recent_media(self, limit=50):
        return self._req("GET", f"{self.uid}/media", {"fields": "id,caption,media_type,media_product_type,timestamp,permalink", "limit": limit}).get("data", [])

    def followers(self):
        return self._req("GET", self.uid, {"fields": "followers_count,media_count,username"})

    def media_insights(self, media_id, metrics):
        """Request all metrics; if one is unsupported for this media, fall back to one-by-one."""
        def parse(j):
            out = {}
            for m in j.get("data", []):
                v = m.get("total_value", {}).get("value") if "total_value" in m else (m.get("values") or [{}])[0].get("value")
                out[m["name"]] = v
            return out
        try:
            return parse(self._req("GET", f"{media_id}/insights", {"metric": ",".join(metrics)}))
        except IGError:
            out = {}
            for m in metrics:
                try: out.update(parse(self._req("GET", f"{media_id}/insights", {"metric": m})))
                except IGError: pass
            return out

    def refresh_token(self):
        r = requests.get(f"{self.host}/refresh_access_token", params={"grant_type": "ig_refresh_token", "access_token": self.token}, timeout=60)
        return r.json()
