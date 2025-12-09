import time
import requests
import pandas as pd
from pathlib import Path

# ------------- CONFIG -------------
INPUT_FILE = "network_inventory.xlsx"
OUTPUT_FILE = "network_inventory_geocoded.xlsx"

# IMPORTANT: put your own email here so Nominatim is happy
USER_EMAIL = "zakes201725@gmail.com"
# ----------------------------------


def clean_value(val: object) -> str:
    """
    Normalize a cell to a clean string.
    Turn NaN/None/'nan' into '' so they are ignored.
    """
    if val is None:
        return ""
    s = str(val).strip()
    if s == "" or s.lower() in {"nan", "none", "n/a"}:
        return ""
    return s


def normalise_place_name(name: str) -> str:
    """
    Fix common spelling / formatting issues before geocoding.
    """
    if not name:
        return name

    n = name.strip()

    # Fix common district / region typos and weird forms
    lower = n.lower()

    # 1) Richards Bay
    if lower == "richardsbay":
        return "Richards Bay"

    # 2) King Sabata Dalindyebo / Mthatha region
    if "king sebata dalindyebo" in lower or "king sabata dalindyebo" in lower:
        # We can centre everything on Mthatha for mapping
        return "Mthatha"

    # 3) Capricorn District (correct spelling)
    if "capricon district" in lower or "capricon" in lower:
        return "Capricorn District Municipality"

    return n


def build_address(row: pd.Series) -> str:
    """
    Build a simpler address for geocoding:
    Prefer District + State + Country, with some normalisation.
    """
    district_raw = clean_value(row.get("District", ""))
    state_raw = clean_value(row.get("State", ""))
    country = clean_value(row.get("Country", ""))
    name_raw = clean_value(row.get("New Name", ""))

    # Normalise
    district = normalise_place_name(district_raw)
    state = normalise_place_name(state_raw)
    name = normalise_place_name(name_raw)

    # Always force South Africa as a default country
    if not country:
        country = "South Africa"

    parts = []

    # 1) Best: District + State + Country
    if district and state:
        parts = [district, state, country]
    # 2) Name + State + Country
    elif name and state:
        parts = [name, state, country]
    # 3) District + Country
    elif district:
        parts = [district, country]
    # 4) Name + Country
    elif name:
        parts = [name, country]
    # 5) Just State + Country
    elif state:
        parts = [state, country]
    else:
        parts = [country]

    return ", ".join(parts)


def geocode(address: str) -> tuple[float | None, float | None]:
    """
    Call OpenStreetMap Nominatim to geocode an address.
    Returns (lat, lon) or (None, None) if not found.
    """
    if not address:
        return None, None

    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": address,
        "format": "json",
        "limit": 1,
        "addressdetails": 0,
    }
    headers = {
        "User-Agent": f"StraatAfricaNetworkMap/1.0 ({USER_EMAIL})"
    }

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if not data:
            print(f"  ✖ No result for: {address}")
            return None, None

        first = data[0]
        lat = float(first["lat"])
        lon = float(first["lon"])
        print(f"  ✓ {address} -> ({lat:.5f}, {lon:.5f})")
        return lat, lon
    except Exception as e:
        print(f"  ! Error geocoding '{address}': {e}")
        return None, None


def reset_obviously_wrong_sa_points(df: pd.DataFrame) -> pd.DataFrame:
    """
    For South Africa rows, reset any coordinates that are obviously not in SA
    so they can be geocoded again.
    SA roughly: lat in [-36, -22], lon in [16, 35].
    """
    lat = df["Latitude"]
    lon = df["Longitude"]

    invalid = (
        lat.notna() & lon.notna() & (
            (lat < -36) | (lat > -22) | (lon < 16) | (lon > 35)
        )
    )

    if invalid.any():
        print(f"Resetting {invalid.sum()} invalid coordinates (outside South Africa).")
        df.loc[invalid, "Latitude"] = pd.NA
        df.loc[invalid, "Longitude"] = pd.NA

    return df


def main():
    path = Path(INPUT_FILE)
    if not path.exists():
        raise FileNotFoundError(
            f"Could not find {INPUT_FILE} in this folder. "
            f"Either rename your Excel file to this, or update INPUT_FILE in the script."
        )

    print(f"Loading workbook: {INPUT_FILE}")
    df = pd.read_excel(path)

    # Ensure the expected columns exist
    required_cols = ["Latitude", "Longitude", "Country",
                     "District", "State", "Start point ", "End point ", "New Name"]
    for col in required_cols:
        if col not in df.columns:
            raise KeyError(f"Missing column in sheet: '{col}'")

    # First reset any obviously wrong coordinates (like the -30.29, 153.12 ones)
    df = reset_obviously_wrong_sa_points(df)

    # Find rows with missing coordinates
    mask_missing = df["Latitude"].isna() | df["Longitude"].isna()
    missing_df = df[mask_missing]

    print(f"Found {len(missing_df)} rows with missing coordinates.")

    if missing_df.empty:
        print("Nothing to geocode – all rows already have Lat/Lng.")
    else:
        for idx, row in missing_df.iterrows():
            name = clean_value(row.get("New Name", ""))
            print(f"\nRow {idx} — {name or '(no name)'}")

            address = build_address(row)
            print(f"  Address: {address}")

            lat, lon = geocode(address)

            if lat is not None and lon is not None:
                df.at[idx, "Latitude"] = lat
                df.at[idx, "Longitude"] = lon

            # Be nice to the free Nominatim API (1 request per second)
            time.sleep(1)

    # Save output
    out_path = path.with_name(OUTPUT_FILE)
    df.to_excel(out_path, index=False)
    print(f"\nDone. Saved updated workbook as: {out_path}")


if __name__ == "__main__":
    main()
