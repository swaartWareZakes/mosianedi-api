import pandas as pd
import json
from pathlib import Path

EXCEL_PATH = Path("network_inventory_geocoded.xlsx")
OUT_PATH = Path("straatafrica-network.json")

# In your current file, everything is in Sheet1
SHEETS = ["Sheet1"]

records = []

for sheet in SHEETS:
    df = pd.read_excel(EXCEL_PATH, sheet_name=sheet)

    for idx, row in df.iterrows():
        lat = row.get("Latitude")
        lng = row.get("Longitude")

        # skip if no coordinates
        try:
            lat_f = float(lat)
            lng_f = float(lng)
        except (TypeError, ValueError):
            continue

        # SA bounding box sanity-check
        if not (-35 <= lat_f <= -22 and 16 <= lng_f <= 33):
            continue

        name = str(row.get("New Name") or "").strip()
        district = str(row.get("District") or "").strip()
        state = str(row.get("State") or "").strip()

        # SAFE SCREEN COUNT
        no_screens = row.get("No of Screens")
        if pd.isna(no_screens):
            no_screens = 1
        else:
            no_screens = int(no_screens)

        # Handle routes (Start/End)
        start = str(row.get("Start point ") or row.get("Start") or "").strip()
        end = str(row.get("End point ") or row.get("End") or "").strip()

        route = None
        if start or end:
            route = f"{start} – {end}".strip(" –")

        rec = {
            "id": f"{sheet.strip().replace(' ', '_')}_{idx}",
            "name": name,
            "rank": district,
            "city": state,
            "route": route,
            "screens": no_screens,
            "lat": lat_f,
            "lng": lng_f,
        }
        records.append(rec)

print(f"Collected {len(records)} locations")

OUT_PATH.write_text(json.dumps(records, indent=2), encoding="utf-8")
print(f"Written to {OUT_PATH}")
