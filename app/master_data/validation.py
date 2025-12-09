# app/master_data/validation.py
from typing import Dict, Any, Optional, Set, Tuple, List
from io import BytesIO

import pandas as pd
from fastapi import HTTPException

# -------------------------------------------------
# Expected workbook structure
# -------------------------------------------------

# We validate only the core "segments" sheet for now.
REQUIRED_SEGMENT_COLUMNS: Set[str] = {
    "segment_id",
    "road_id",
    "road_class",
    "surface_type",
    "length_km",
}

# Other sheets are optional but expected in the Mosianedi template.
EXPECTED_SHEETS: List[str] = [
    "segments",
    "network_type_surface",
    "network_length",
    "asset_value",
    "iri_defaults",
    "road_costs",
]

# -------------------------------------------------
# Parsing helpers
# -------------------------------------------------


def parse_master_data_file(file_bytes: bytes, filename: str) -> pd.DataFrame:
    """
    Helper used for previewing the FIRST sheet only.

    - For Excel workbooks: return the first sheet as a DataFrame
      (typically the 'segments' sheet in our template).
    - For CSV: parse as a flat table.
    """
    buffer = BytesIO(file_bytes)
    name = filename.lower()

    try:
        if name.endswith((".xlsx", ".xls")):
            xls = pd.ExcelFile(buffer)
            first_sheet = xls.sheet_names[0]
            df = xls.parse(sheet_name=first_sheet)
            return df
        elif name.endswith(".csv"):
            return pd.read_csv(buffer)
        else:
            raise HTTPException(status_code=400, detail="Invalid file type.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse file: {str(e)}")


# -------------------------------------------------
# Workbook parser
# -------------------------------------------------


def parse_master_workbook(file_bytes: bytes, filename: str) -> Dict[str, Any]:
    """
    Parse our Mosianedi multi-sheet workbook into a JSON-friendly structure.

    Returns a dict like:
    {
        "segments": [ {...}, {...}, ... ],
        "network_type_surface": [ ... ],
        ...
        "_sheet_errors": { "sheet_name": "error message", ... }
    }

    For CSV uploads, this returns {} (no workbook structure).
    """
    name = filename.lower()

    # CSV or other non-Excel ⇒ no workbook
    if not name.endswith((".xlsx", ".xls")):
        return {}

    try:
        xls = pd.ExcelFile(BytesIO(file_bytes))
    except Exception as exc:
        # Don't kill the upload; just record that the workbook couldn't be opened.
        return {"_workbook_error": f"Could not open workbook: {exc}"}

    payload: Dict[str, Any] = {}
    sheet_errors: Dict[str, str] = {}

    for sheet in EXPECTED_SHEETS:
        if sheet not in xls.sheet_names:
            # Sheet is optional — just skip if not present
            continue

        try:
            df = xls.parse(sheet_name=sheet)

            # Normalise column names: lowercase + trimmed
            df.columns = [str(c).strip().lower() for c in df.columns]

            # Replace NaNs with empty strings to keep JSON clean
            df = df.fillna("")

            payload[sheet] = df.to_dict(orient="records")
        except Exception as exc:
            sheet_errors[sheet] = str(exc)

    if sheet_errors:
        payload["_sheet_errors"] = sheet_errors

    return payload


# -------------------------------------------------
# Validation helpers (segments only)
# -------------------------------------------------


def _validate_segments_df(df: pd.DataFrame) -> Tuple[str, Optional[int], Dict[str, Any]]:
    """
    Internal helper to validate that a segments-style DataFrame
    has the required columns.
    """
    row_count: Optional[int] = len(df.index)
    validation_errors: Dict[str, Any] = {}

    cols_lower = {c.lower() for c in df.columns}
    missing = [col for col in REQUIRED_SEGMENT_COLUMNS if col not in cols_lower]

    if missing:
        validation_errors["missing_columns"] = missing
        return "failed", row_count, validation_errors

    return "validated", row_count, validation_errors


def validate_flat_segments_df(df: pd.DataFrame) -> Tuple[str, Optional[int], Dict[str, Any]]:
    """
    Validate a flat (CSV / single-sheet) table as if it were the segments sheet.
    """
    return _validate_segments_df(df)


def validate_segments_sheet(
    workbook_payload: Dict[str, Any]
) -> Tuple[str, Optional[int], Dict[str, Any]]:
    """
    Validate the 'segments' sheet inside a parsed workbook payload.

    Expects workbook_payload["segments"] to be a list of dict rows.
    """
    if "segments" not in workbook_payload:
        return "failed", None, {"missing_sheet": "segments"}

    df = pd.DataFrame(workbook_payload["segments"])
    return _validate_segments_df(df)