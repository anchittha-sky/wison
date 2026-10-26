import json
import urllib.request
from datetime import datetime, timezone

URL = "https://api-v3.thaiwater.net/api/v1/thaiwater30/public/waterlevel_load"
NEEDLES = ["X.44", "X.90", "X.173A", "X.174",
           "บ้านหาดใหญ่ใน", "บ้านบางศาลา", "บ้านม่วงก็อง", "บ้านคลองหวะ"]


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
        "source": URL,
    }
    try:
        req = urllib.request.Request(
            URL, headers={"User-Agent": "Mozilla/5.0 (hatyai-flood-monitor)"})
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read().decode("utf-8"))
        recs = find(data)
        out["count"] = len(recs)
        out["records"] = recs[:30]
        if not recs:
            out["note"] = "ไม่พบสถานีที่ค้นหา"
            out["sample"] = json.dumps(data, ensure_ascii=False)[:1500]
    except Exception as e:
        out["error"] = str(e)
    with open("water.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)


main()
