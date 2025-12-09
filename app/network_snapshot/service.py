# app/network_snapshot/service.py

from uuid import UUID
from typing import Optional, Tuple, Any, List, Dict

import json
import pandas as pd
from fastapi import HTTPException

from app.routers.projects import get_db_connection
from app.master_data.validation import parse_master_data_file  # fallback for legacy uploads
from .schemas import (
    NetworkSnapshot,
    LengthByCategory,
    AssetValueByCategory,
    UnitCostByCategory,
)


# -------------------------------------------------
# DB helper: latest upload record + workbook blob
# -------------------------------------------------


def _fetch_latest_master_data_record(
    project_id: UUID,
    user_id: str,
) -> Tuple[UUID, Optional[Dict[str, Any]], Optional[bytes], Optional[str]]:
    """
    Fetch the latest master_data_uploads row for this project+user.

    Returns:
        upload_id,
        workbook_payload (dict or None),
        file_bytes (from file_blob, or None),
        original_filename (or None)
    """
    sql = """
        SELECT
            id,
            workbook_payload,
            file_blob,
            original_filename
        FROM public.master_data_uploads
        WHERE project_id = %s AND user_id = %s
        ORDER BY created_at DESC
        LIMIT 1;
    """

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (str(project_id), user_id))
            row = cur.fetchone()

            if not row:
                raise HTTPException(
                    status_code=404,
                    detail="No master data uploads found for this project.",
                )

            upload_id, workbook_payload_raw, file_blob_raw, original_filename = row

            # workbook_payload is usually a dict (psycopg2 Json), but be defensive
            workbook_payload: Optional[Dict[str, Any]] = None
            if workbook_payload_raw is not None:
                if isinstance(workbook_payload_raw, dict):
                    workbook_payload = workbook_payload_raw
                else:
                    try:
                        workbook_payload = json.loads(workbook_payload_raw)
                    except Exception:
                        workbook_payload = None

            # Convert file_blob to bytes if present
            file_bytes: Optional[bytes] = None
            if file_blob_raw is not None:
                if isinstance(file_blob_raw, memoryview):
                    file_bytes = file_blob_raw.tobytes()
                else:
                    file_bytes = file_blob_raw

            return upload_id, workbook_payload, file_bytes, original_filename


# -------------------------------------------------
# Generic helpers
# -------------------------------------------------


def _compute_length_breakdown(
    df: pd.DataFrame,
    column: str,
) -> List[LengthByCategory]:
    """
    Group by a categorical column (e.g. road_class, surface_type)
    and sum length_km.
    """
    if column not in df.columns or "length_km" not in df.columns:
        return []

    grouped = (
        df.groupby(column)["length_km"]
        .sum()
        .reset_index()
        .sort_values("length_km", ascending=False)
    )

    results: List[LengthByCategory] = []
    for _, row in grouped.iterrows():
        label = str(row[column])
        length = float(row["length_km"] or 0)
        results.append(LengthByCategory(label=label, length_km=length))

    return results


def _get_segments_df_from_workbook(
    workbook_payload: Dict[str, Any]
) -> Optional[pd.DataFrame]:
    """
    Build a DataFrame from workbook_payload['segments'] if present.
    """
    segments = workbook_payload.get("segments")
    if not segments:
        return None

    df = pd.DataFrame(segments)
    df.columns = [str(c).strip().lower() for c in df.columns]

    if "length_km" in df.columns:
        df["length_km"] = pd.to_numeric(df["length_km"], errors="coerce").fillna(0)

    return df


def _get_sheet_df(
    workbook_payload: Dict[str, Any],
    sheet_name: str,
) -> Optional[pd.DataFrame]:
    """
    Small helper: safely convert a workbook sheet to DataFrame.
    """
    if not workbook_payload or sheet_name not in workbook_payload:
        return None

    data = workbook_payload.get(sheet_name)
    if not data:
        return None

    df = pd.DataFrame(data)
    df.columns = [str(c).strip().lower() for c in df.columns]
    return df


def _find_first_numeric_column(
    df: pd.DataFrame,
    preferred_names: List[str],
) -> Optional[str]:
    """
    Tries a list of preferred column names; if none exist, picks
    the first numeric column, else None.
    """
    cols = set(df.columns)

    for name in preferred_names:
        if name in cols:
            return name

    # Fallback: any numeric-looking column
    numeric_cols = df.select_dtypes(include=["number"]).columns
    if len(numeric_cols) > 0:
        return numeric_cols[0]

    # Try to coerce object columns
    for col in df.columns:
        try:
            pd.to_numeric(df[col], errors="raise")
            return col
        except Exception:
            continue

    return None


# -------------------------------------------------
# Extra metrics by sheet
# -------------------------------------------------


def _compute_network_length_metrics(
    workbook_payload: Optional[Dict[str, Any]],
) -> tuple[Optional[float], List[LengthByCategory]]:
    """
    Use 'network_length' sheet if present.
    """
    if not workbook_payload:
        return None, []

    df = _get_sheet_df(workbook_payload, "network_length")
    if df is None or df.empty:
        return None, []

    # Ensure numeric length column
    length_col = _find_first_numeric_column(
        df,
        preferred_names=["length_km", "network_length_km", "length"],
    )
    if not length_col:
        return None, []

    df[length_col] = pd.to_numeric(df[length_col], errors="coerce").fillna(0)

    total_network_length_km = float(df[length_col].sum())

    # Category for breakdown – try a few expected options
    category_col = None
    for candidate in ["network_type", "road_class", "surface_type"]:
        if candidate in df.columns:
            category_col = candidate
            break

    length_by_network_type: List[LengthByCategory] = []
    if category_col:
        grouped = (
            df.groupby(category_col)[length_col]
            .sum()
            .reset_index()
            .sort_values(length_col, ascending=False)
        )
        for _, row in grouped.iterrows():
            label = str(row[category_col])
            length = float(row[length_col] or 0)
            length_by_network_type.append(
                LengthByCategory(label=label, length_km=length)
            )

    return total_network_length_km, length_by_network_type


def _compute_asset_value_metrics(
    workbook_payload: Optional[Dict[str, Any]],
) -> tuple[Optional[float], List[AssetValueByCategory]]:
    """
    Use 'asset_value' sheet if present.
    """
    if not workbook_payload:
        return None, []

    df = _get_sheet_df(workbook_payload, "asset_value")
    if df is None or df.empty:
        return None, []

    value_col = _find_first_numeric_column(
        df,
        preferred_names=["asset_value", "value", "total_value"],
    )
    if not value_col:
        return None, []

    df[value_col] = pd.to_numeric(df[value_col], errors="coerce").fillna(0)

    total_asset_value = float(df[value_col].sum())

    # Category – pick something readable if present
    category_col = None
    for candidate in ["asset_type", "network_type", "road_class", "surface_type"]:
        if candidate in df.columns:
            category_col = candidate
            break

    asset_value_by_category: List[AssetValueByCategory] = []
    if category_col:
        grouped = (
            df.groupby(category_col)[value_col]
            .sum()
            .reset_index()
            .sort_values(value_col, ascending=False)
        )
        for _, row in grouped.iterrows():
            label = str(row[category_col])
            value = float(row[value_col] or 0)
            asset_value_by_category.append(
                AssetValueByCategory(label=label, value=value)
            )

    return total_asset_value, asset_value_by_category


def _compute_unit_cost_metrics(
    workbook_payload: Optional[Dict[str, Any]],
) -> List[UnitCostByCategory]:
    """
    Use 'road_costs' sheet if present.

    We look for a cost-per-km style column and group by surface_type or
    maintenance_type, depending on what exists.
    """
    if not workbook_payload:
        return []

    df = _get_sheet_df(workbook_payload, "road_costs")
    if df is None or df.empty:
        return []

    cost_col = _find_first_numeric_column(
        df,
        preferred_names=[
            "cost_per_km",
            "unit_cost_per_km",
            "unit_cost",
            "cost",
        ],
    )
    if not cost_col:
        return []

    df[cost_col] = pd.to_numeric(df[cost_col], errors="coerce").fillna(0)

    # Choose a category column
    category_col = None
    for candidate in ["surface_type", "treatment_type", "maintenance_type", "road_class"]:
        if candidate in df.columns:
            category_col = candidate
            break

    if not category_col:
        # No category → summarise a single “all” bucket
        avg_cost = float(df[cost_col].mean())
        return [
            UnitCostByCategory(label="All", cost_per_km=avg_cost),
        ]

    grouped = (
        df.groupby(category_col)[cost_col]
        .mean()
        .reset_index()
        .sort_values(cost_col, ascending=False)
    )

    results: List[UnitCostByCategory] = []
    for _, row in grouped.iterrows():
        label = str(row[category_col])
        cost = float(row[cost_col] or 0)
        results.append(UnitCostByCategory(label=label, cost_per_km=cost))

    return results


# -------------------------------------------------
# Public service
# -------------------------------------------------


def get_network_snapshot(
    project_id: UUID,
    user_id: str,
) -> NetworkSnapshot:
    """
    Compute a lightweight 'network snapshot' for the latest
    master data upload.

    Sources:
    - segments sheet      → core totals + breakdowns
    - network_length      → total_network_length_km, length_by_network_type
    - asset_value         → total_asset_value, asset_value_by_category
    - road_costs          → unit_costs_by_surface
    """
    # 1) Get latest upload record
    upload_id, workbook_payload, file_bytes, filename = _fetch_latest_master_data_record(
        project_id=project_id,
        user_id=user_id,
    )

    # 2) Get segments DataFrame
    df_segments: Optional[pd.DataFrame] = None
    if workbook_payload:
        df_segments = _get_segments_df_from_workbook(workbook_payload)

    # Fallback to blob (legacy uploads)
    if df_segments is None:
        if not file_bytes or not filename:
            raise HTTPException(
                status_code=500,
                detail="No usable workbook payload or file blob found for snapshot.",
            )
        df_segments = parse_master_data_file(file_bytes, filename)
        df_segments.columns = [str(c).strip().lower() for c in df_segments.columns]
        if "length_km" in df_segments.columns:
            df_segments["length_km"] = pd.to_numeric(
                df_segments["length_km"], errors="coerce"
            ).fillna(0)

    if "length_km" not in df_segments.columns:
        raise HTTPException(
            status_code=400,
            detail="The master data (segments) does not contain a 'length_km' column.",
        )

    # 3) Core metrics from segments
    total_segments = int(len(df_segments.index))
    total_length_km = float(df_segments["length_km"].sum())

    total_roads: Optional[int] = None
    if "road_id" in df_segments.columns:
        total_roads = int(df_segments["road_id"].nunique())

    length_by_road_class = (
        _compute_length_breakdown(df_segments, "road_class")
        if "road_class" in df_segments.columns
        else []
    )
    length_by_surface_type = (
        _compute_length_breakdown(df_segments, "surface_type")
        if "surface_type" in df_segments.columns
        else []
    )

    # 4) Extra metrics from other sheets
    total_network_length_km, length_by_network_type = _compute_network_length_metrics(
        workbook_payload
    )
    total_asset_value, asset_value_by_category = _compute_asset_value_metrics(
        workbook_payload
    )
    unit_costs_by_surface = _compute_unit_cost_metrics(workbook_payload)

    # 5) Build response
    return NetworkSnapshot(
        project_id=project_id,
        upload_id=upload_id,
        total_length_km=total_length_km,
        total_segments=total_segments,
        total_roads=total_roads,
        length_by_road_class=length_by_road_class,
        length_by_surface_type=length_by_surface_type,
        total_network_length_km=total_network_length_km,
        length_by_network_type=length_by_network_type,
        total_asset_value=total_asset_value,
        asset_value_by_category=asset_value_by_category,
        unit_costs_by_surface=unit_costs_by_surface,
    )