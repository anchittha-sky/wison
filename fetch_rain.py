import json
import urllib.request
from datetime import datetime, timezone

URL = "https://api-v3.thaiwater.net/api/v1/thaiwater30/public/rain_24h"
# กรอบพื้นที่ลุ่มน้ำอู่ตะเภา (หาดใหญ่ - สะเดา - คลองหอยโข่ง)
LAT_MIN, LAT_MAX, LON_MIN, LON_MAX = 6.45, 7.20, 100.15, 100.65


def walk(o):
    if isinstance(o, dict):
        if "rain_24h" in o and "station" in o:
            yield o
        else:
            for v in o.values():
                yield from walk(v)
    elif isinstance(o, list):
        for e in o:
            yield from walk(e)


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
        stations = []
        for it in walk(data):
            st = it.get("station") or {}
            geo = it.get("geocode") or {}
            lat, lon = st.get("tele_station_lat"), st.get("tele_station_long")
            if lat is None or lon is None:
                continue
            if str(geo.get("province_code")) != "90":
                continue
            if not (LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX):
                continue
            stations.append({
                "code": st.get("tele_station_oldcode"),
                "name": (st.get("tele_station_name") or {}).get("th"),
                "lat": lat,
                "lon": lon,
                "rain24": it.get("rain_24h"),
                "rain1": it.get("rain_1h"),
                "time": it.get("rainfall_datetime"),
                "agency": ((it.get("agency") or {}).get("agency_shortname") or {}).get("th"),
            })
        stations.sort(key=lambda s: -(s["rain24"] or 0))
        out["count"] = len(stations)
        out["stations"] = stations
    except Exception as e:
        out["error"] = str(e)[:200]
    with open("rain_stations.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)


main()
