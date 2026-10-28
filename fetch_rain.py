# ดึงฝนวัดจริง + ระดับทะเลสาบสงขลา และเก็บประวัติย้อนหลัง (ใช้คู่กับ fetch_water.py)
import json
import os
import urllib.request
from datetime import datetime, timezone, timedelta

BASE = "https://api-v3.thaiwater.net/api/v1/thaiwater30/public/"
LAT_MIN, LAT_MAX, LON_MIN, LON_MAX = 6.45, 7.20, 100.15, 100.65
ZONE_LAT = 6.9          # ต่ำกว่านี้ = ต้นน้ำ (แถบสะเดา)
LAKE_CODES = ["SLA005", "TA200306", "G09006-TA200306", "ONE038"]
LAKE_NAMES = ["ปากรอ", "ปากทะเลสาบสงขลา"]
KEEP_HOURS = 96
TH = timezone(timedelta(hours=7))


def get(name):
    req = urllib.request.Request(
        BASE + name, headers={"User-Agent": "Mozilla/5.0 (hatyai-flood-monitor)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def walk(o, key):
    if isinstance(o, dict):
        if key in o and "station" in o:
            yield o
        else:
            for v in o.values():
                yield from walk(v, key)
    elif isinstance(o, list):
        for e in o:
            yield from walk(e, key)


def parse_th(s):
    try:
        return datetime.strptime(str(s)[:16], "%Y-%m-%d %H:%M").replace(tzinfo=TH)
    except Exception:
        return None


def rain_stations():
    out = {"updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "source": BASE + "rain_24h"}
    try:
        stations = []
        for it in walk(get("rain_24h"), "rain_24h"):
            st = it.get("station") or {}
            geo = it.get("geocode") or {}
            lat, lon = st.get("tele_station_lat"), st.get("tele_station_long")
            if lat is None or lon is None or str(geo.get("province_code")) != "90":
                continue
            if not (LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX):
                continue
            stations.append({
                "code": st.get("tele_station_oldcode"),
                "name": (st.get("tele_station_name") or {}).get("th"),
                "lat": lat, "lon": lon,
                "rain24": it.get("rain_24h"), "rain1": it.get("rain_1h"),
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
    return out


def lake_level():
    try:
        data = get("waterlevel_load")
    except Exception:
        return None
    found = {}
    for it in walk(data, "waterlevel_msl"):
        st = it.get("station") or {}
        code = str(st.get("tele_station_oldcode") or "")
        name = (st.get("tele_station_name") or {}).get("th") or ""
        if code in LAKE_CODES or any(n in name for n in LAKE_NAMES):
            try:
                v = float(it.get("waterlevel_msl"))
            except Exception:
                continue
            found[code] = {"code": code, "name": name, "v": v,
                           "time": it.get("waterlevel_datetime")}
    for c in LAKE_CODES:
        if c in found:
            return found[c]
    return next(iter(found.values()), None)


def zone_max(rs, now):
    # ค่าฝนของแต่ละโซน = ค่าสูงสุดอันดับ 2 (กันเครื่องวัดเพี้ยนสถานีเดียว) ถ้ามีสถานีเดียวใช้ค่านั้น
    vals = {"city": [], "up": []}
    for s in rs.get("stations") or []:
        t = parse_th(s.get("time"))
        if s.get("rain24") is None or t is None or (now - t).total_seconds() > 6 * 3600:
            continue
        vals["up" if s["lat"] < ZONE_LAT else "city"].append(s["rain24"])
    res = {}
    for k, v in vals.items():
        v.sort(reverse=True)
        res[k] = v[1] if len(v) >= 2 else (v[0] if v else None)
    return res


def main():
    now = datetime.now(TH)
    rs = rain_stations()
    lake = lake_level()
    wl = {}
    try:
        with open("water.json", encoding="utf-8") as f:
            for r in json.load(f).get("records") or []:
                code = (r.get("station") or {}).get("tele_station_oldcode")
                try:
                    wl[code] = float(r.get("waterlevel_msl"))
                except Exception:
                    pass
    except Exception:
        pass
    hist = {"points": []}
    if os.path.exists("history.json"):
        try:
            with open("history.json", encoding="utf-8") as f:
                hist = json.load(f)
        except Exception:
            hist = {"points": []}
    zm = zone_max(rs, now)
    point = {"t": now.isoformat(timespec="minutes"), "wl": wl,
             "rc": zm["city"], "ru": zm["up"], "lake": lake["v"] if lake else None}
    pts = [p for p in hist.get("points", [])
           if (now - datetime.fromisoformat(p["t"])).total_seconds() < KEEP_HOURS * 3600]
    if pts and (now - datetime.fromisoformat(pts[-1]["t"])).total_seconds() < 20 * 60:
        pts[-1] = point
    else:
        pts.append(point)
    out = {"updated": now.isoformat(timespec="minutes"),
           "lake": lake or hist.get("lake"), "points": pts}
    with open("history.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))


main()
