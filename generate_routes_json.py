import json
from pathlib import Path

import pandas as pd
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

EXCEL_PATH = Path("network_inventory_geocoded.xlsx")
OUT_PATH = Path("straatafrica-routes.json")

# Most of your data seems to live on one sheet now
SHEET_NAME = "Sheet1"

# --- Geocoder setup (Nominatim) ---
geolocator = Nominatim(user_agent="straat-africa-routes")
geocode_raw = geolocator.geocode
geocode = RateLimiter(geocode_raw, min_delay_seconds=1.1)  # be gentle

# Cache so we don't geocode same place 100 times
cache = {}


def geocode_cached(query: str):
    """Geocode with in-memory cache."""
    if not query or not query.strip():
        return None
    q = query.strip()
    if q in cache:
        return cache[q]

    try:
        loc = geocode(q)
    except Exception:
        loc = None

    cache[q] = loc
    return loc


df = pd.read_excel(EXCEL_PATH, sheet_name=SHEET_NAME)

routes = []

for idx, row in df.iterrows():
    # Try to read start / end from the various column names
    start = (
        row.get("Start point ")
        or row.get("Start point")
        or row.get("Start")
        or ""
    )
    end = (
        row.get("End point ")
        or row.get("End point")
        or row.get("End")
        or ""
    )

    start = str(start).strip()
    end = str(end).strip()

    # Skip rows without both start & end
    if not start or not end:
        continue

    district = str(row.get("District") or "").strip()
    state = str(row.get("State") or "").strip()

    loads = str(
        row.get("Loads per day")
        or row.get("Loads Per Day")
        or ""
    ).strip()

    # Build address strings (you can tweak if needed)
    base_tail = ", South Africa"
    start_query = ", ".join(
        [p for p in [start, district, state] if p]
    ) + base_tail
    end_query = ", ".join(
        [p for p in [end, district, state] if p]
    ) + base_tail

    print(f"\nRow {idx}: {start} → {end}")
    print(f"  Start: {start_query}")
    print(f"  End:   {end_query}")

    start_loc = geocode_cached(start_query)
    end_loc = geocode_cached(end_query)

    if not start_loc or not end_loc:
        print("  ✖ Could not geocode one of the points — skipping route.")
        continue

    # Bounding box sanity check (rough South Africa box)
    def in_sa(lat, lng):
        return (-35 <= lat <= -22) and (16 <= lng <= 33)

    if not in_sa(start_loc.latitude, start_loc.longitude):
        print("  ✖ Start outside SA bbox — skipping.")
        continue
    if not in_sa(end_loc.latitude, end_loc.longitude):
        print("  ✖ End outside SA bbox — skipping.")
        continue

    route_rec = {
        "id": f"route_{idx}",
        "startName": start,
        "endName": end,
        "district": district,
        "state": state,
        "loadsPerDay": loads,  # still as text e.g. "6 loads per day"
        "startLat": start_loc.latitude,
        "startLng": start_loc.longitude,
        "endLat": end_loc.latitude,
        "endLng": end_loc.longitude,
    }
    routes.append(route_rec)
    print(
        f"  ✓ Route OK ({route_rec['startLat']:.5f},{route_rec['startLng']:.5f})"
        f" → ({route_rec['endLat']:.5f},{route_rec['endLng']:.5f})"
    )

print(f"\nCollected {len(routes)} routes")

OUT_PATH.write_text(json.dumps(routes, indent=2), encoding="utf-8")
print(f"Written to {OUT_PATH}")
