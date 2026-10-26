import json
import urllib.request
from datetime import datetime, timezone

BASE = "https://api-v3.thaiwater.net/api/v1/thaiwater30/public/"
NAMES = ["rain_24h", "rain_3d", "rain_today", "rain_yesterday", "rain_load", "rain_hourly"]
NEEDLES = ["สนามบินหาดใหญ่", "หาดใหญ่", "สะเดา", "คลองหอยโข่ง"]


def match(o):
    s = json.dumps(o, ensure_ascii=False)
    return any(n in s for n in NEEDLES)


def find(o):
    out = []
    if isinstance(o, dict):
        for v in o.values():
            out += find(v)
    elif isinstance(o, list):
        for e in o:
            if isinstance(e, dict) and match(e):
                sub = [h for v in e.values() if isinstance(v, list) for h in find(v)]
                out += sub if sub else [e]
            else:
                out += find(e)
    return out


def main():
    out = {
        "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "endpoints": {},
    }
    for name in NAMES:
        info = {}
        try:
            req = urllib.request.Request(
                BASE + name,
                headers={"User-Agent": "Mozilla/5.0 (hatyai-flood-monitor)"})
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read().decode("utf-8"))
            recs = find(data)
            info["ok"] = True
            info["count"] = len(recs)
            info["records"] = recs[:15]
            if not recs:
                info["sample"] = json.dumps(data, ensure_ascii=False)[:600]
        except Exception as e:
            info["ok"] = False
            info["error"] = str(e)[:200]
        out["endpoints"][name] = info
    with open("rain.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)


main()
