"""
Data preprocessing utilities for CINEI.

Helps users standardize their emission data into CINEI-compatible format:
- Dimensions: (month, lat, lon)
- Variables:  agriculture, industry, power, residential, transportation,
              shipping, aviation, waste, sum
- Units:      Mg/month (consistent with HTAP v3)
- Format:     NetCDF (.nc)
"""

import os
import numpy as np
from pathlib import Path


# ── CINEI standard format ─────────────────────────────────────────────────────
CINEI_STANDARD = {
    "dims":     ("month", "lat", "lon"),
    "sectors":  ["agriculture", "industry", "power", "residential",
                 "transportation", "shipping", "aviation", "waste", "sum"],
    "units":    "ton/grid/month",
    "format":   "NetCDF (.nc)",
    "months":   12,
}

# ── CINEI sector integration mapping (from core.py) ─────────────────────────
# Shows how input inventory sectors map to CINEI output sectors:
#
#   CINEI output      CEDS input              MEIC input       HTAP/other
#   ─────────────     ────────────────────    ────────────     ──────────
#   power         =   energy               +  power
#   residential   =   residential+solvents +  residential
#   industry      =   industrial           +  industry
#   transportation=   transportation       +  transportation
#   agriculture   =   agriculture          +  agriculture (outside China)
#   shipping      =   ships                +                   shipping (HTAP)
#   waste         =                                            waste (HTAP)
#   aviation      =                                            aviation (HTAP)
#   sum           =   power+residential+industry+transportation+
#                     agriculture+shipping+waste  (NO aviation in sum)
#
# Units: ton/grid/month
# Resolution: flexible (regridded to 0.25° in emis_union)

# Sector name aliases: common alternative names → CINEI standard name
SECTOR_ALIASES = {
    # agriculture
    "agr":          "agriculture",
    "agri":         "agriculture",
    "agricultural": "agriculture",
    "act":          "agriculture",
    "4a":           "agriculture",
    # industry
    "ind":          "industry",
    "industrial":   "industry",
    "idt":          "industry",
    "manufacturing":"industry",
    # power
    "pwr":          "power",
    "energy":       "power",
    "ene":          "power",
    "electricity":  "power",
    "powerplant":   "power",
    # residential
    "res":          "residential",
    "rdt":          "residential",
    "domestic":     "residential",
    "household":    "residential",
    # transportation
    "tra":          "transportation",
    "tpt":          "transportation",
    "transport":    "transportation",
    "road":         "transportation",
    "traffic":      "transportation",
    # shipping
    "shp":          "shipping",
    "ship":         "shipping",
    "marine":       "shipping",
    "international_shipping": "shipping",
    # aviation
    "avi":          "aviation",
    "air":          "aviation",
    "aircraft":     "aviation",
    # waste
    "wst":          "waste",
    "swd":          "waste",
    "solid_waste":  "waste",
    # sum / total
    "total":        "sum",
    "tot":          "sum",
    "all":          "sum",
    "anthro":       "sum",
}


# ── Public functions ──────────────────────────────────────────────────────────

def check_user_data(file_path, file_type=None):
    """
    Diagnose a user-provided emission file and report issues.

    Checks dimensions, sector variable names, units, and data validity.
    Provides actionable suggestions to fix any issues found.

    Parameters
    ----------
    file_path : str
        Path to the emission file (.nc or .txt).
    file_type : str, optional
        File type: 'netcdf', 'txt'. Auto-detected if None.

    Returns
    -------
    dict
        Diagnosis report with keys:
        - 'status'   : 'ok', 'warning', or 'error'
        - 'issues'   : list of issue descriptions
        - 'suggestions' : list of fix suggestions
        - 'info'     : dict of detected file properties

    Examples
    --------
    >>> import cinei
    >>> report = cinei.check_user_data('/path/to/my_emission.nc')
    >>> print(report['status'])
    >>> for issue in report['issues']:
    ...     print(issue)
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"[CINEI] File not found: {file_path}")

    # Auto-detect file type
    if file_type is None:
        suffix = file_path.suffix.lower()
        if suffix in (".nc", ".nc4", ".netcdf"):
            file_type = "netcdf"
        elif suffix in (".txt", ".csv", ".dat"):
            file_type = "txt"
        else:
            raise ValueError(
                f"[CINEI] Cannot detect file type for: {file_path.name}\n"
                f"        Please specify file_type='netcdf' or file_type='txt'"
            )

    print(f"[CINEI] Checking: {file_path.name}")
    print(f"[CINEI] Type    : {file_type}")
    print()

    if file_type == "netcdf":
        return _check_netcdf(file_path)
    elif file_type == "txt":
        return _check_txt(file_path)


def standardize_netcdf(file_path, save_path=None,
                       sector_mapping=None, month_dim=None,
                       lat_dim=None, lon_dim=None):
    """
    Standardize a NetCDF emission file to CINEI format.

    Automatically fixes:
    - Dimension order → (month, lat, lon)
    - Sector variable names → CINEI standard names
    - Missing 'sum' variable → computed from available sectors

    Parameters
    ----------
    file_path : str
        Path to input NetCDF file.
    save_path : str, optional
        Output path. Default: adds '_cinei_standard' suffix.
    sector_mapping : dict, optional
        Manual sector name mapping, e.g. {'agr': 'agriculture'}.
        Use this when auto-detection fails.
        e.g. {'my_agr_var': 'agriculture', 'my_ind_var': 'industry'}
    month_dim : str, optional
        Name of the month/time dimension if auto-detection fails.
    lat_dim : str, optional
        Name of the latitude dimension if auto-detection fails.
    lon_dim : str, optional
        Name of the longitude dimension if auto-detection fails.

    Returns
    -------
    str
        Path to the standardized output file.

    Examples
    --------
    >>> import cinei
    >>> # Auto-standardize
    >>> out = cinei.standardize_netcdf('/path/to/my_emission.nc')

    >>> # With manual sector mapping
    >>> out = cinei.standardize_netcdf(
    ...     '/path/to/my_emission.nc',
    ...     sector_mapping={
    ...         'agr_emis':   'agriculture',
    ...         'ind_emis':   'industry',
    ...         'pow_emis':   'power',
    ...         'res_emis':   'residential',
    ...         'tra_emis':   'transportation',
    ...     }
    ... )
    """
    import xarray as xr

    file_path = Path(file_path)
    ds = xr.open_dataset(file_path)

    print(f"[CINEI] Standardizing: {file_path.name}")
    print(f"[CINEI] Current dims  : {dict(ds.dims)}")
    print(f"[CINEI] Current vars  : {list(ds.data_vars)}")
    print()

    fixes = []

    # ── Step 1: Identify dimensions ───────────────────────────────────
    month_dim = month_dim or _find_dim(ds, ["month", "time", "months", "mon"])
    lat_dim   = lat_dim   or _find_dim(ds, ["lat", "latitude", "y", "LAT"])
    lon_dim   = lon_dim   or _find_dim(ds, ["lon", "longitude", "x", "LON"])

    if not all([month_dim, lat_dim, lon_dim]):
        missing = [n for n, d in
                   [("month", month_dim), ("lat", lat_dim), ("lon", lon_dim)]
                   if not d]
        raise ValueError(
            f"[CINEI] Cannot auto-detect dimensions: {missing}\n"
            f"        Available dims: {list(ds.dims)}\n"
            f"        Please specify month_dim, lat_dim, lon_dim manually."
        )

    # ── Step 2: Fix dimension names ───────────────────────────────────
    rename_dims = {}
    if month_dim != "month":
        rename_dims[month_dim] = "month"
        fixes.append(f"Renamed dim '{month_dim}' → 'month'")
    if lat_dim != "lat":
        rename_dims[lat_dim] = "lat"
        fixes.append(f"Renamed dim '{lat_dim}' → 'lat'")
    if lon_dim != "lon":
        rename_dims[lon_dim] = "lon"
        fixes.append(f"Renamed dim '{lon_dim}' → 'lon'")

    if rename_dims:
        ds = ds.rename(rename_dims)

    # ── Step 3: Fix dimension order → (month, lat, lon) ──────────────
    for var in ds.data_vars:
        if set(["month", "lat", "lon"]).issubset(set(ds[var].dims)):
            current_order = ds[var].dims
            if current_order != ("month", "lat", "lon"):
                ds[var] = ds[var].transpose("month", "lat", "lon")
                fixes.append(f"Transposed '{var}': {current_order} → (month, lat, lon)")

    # ── Step 4: Rename sector variables ──────────────────────────────
    if sector_mapping is None:
        sector_mapping = _auto_detect_sectors(list(ds.data_vars))

    rename_vars = {}
    for old_name, new_name in sector_mapping.items():
        if old_name in ds.data_vars and old_name != new_name:
            rename_vars[old_name] = new_name
            fixes.append(f"Renamed variable '{old_name}' → '{new_name}'")

    if rename_vars:
        ds = ds.rename(rename_vars)

    # ── Step 5: Check for missing sectors ────────────────────────────
    present   = [s for s in CINEI_STANDARD["sectors"] if s in ds.data_vars]
    missing_s = [s for s in CINEI_STANDARD["sectors"]
                 if s not in ds.data_vars and s != "sum"]

    if missing_s:
        print(f"[CINEI] ⚠️  Missing sectors: {missing_s}")
        print(f"[CINEI]    These will be filled with zeros.")
        ref_var = list(ds.data_vars)[0]
        for s in missing_s:
            ds[s] = xr.zeros_like(ds[ref_var])
            fixes.append(f"Added zero-filled variable '{s}' (missing sector)")

    # ── Step 6: Compute/update 'sum' ─────────────────────────────────
    sum_sectors = [s for s in CINEI_STANDARD["sectors"]
                   if s != "sum" and s in ds.data_vars]
    ds["sum"] = sum(ds[s] for s in sum_sectors)
    ds["sum"].attrs["description"] = "Total anthropogenic emissions (sum of all sectors)"
    fixes.append(f"Computed 'sum' from: {sum_sectors}")

    # ── Step 7: Add standard attributes ──────────────────────────────
    ds.attrs["cinei_standardized"] = "True"
    ds.attrs["cinei_version"]      = "2.0.1"
    ds.attrs["units"]              = CINEI_STANDARD["units"]
    ds.attrs["conventions"]        = "CINEI standard format"

    # ── Step 8: Save output ───────────────────────────────────────────
    if save_path is None:
        save_path = file_path.parent / (
            file_path.stem + "_cinei_standard.nc"
        )
    save_path = Path(save_path)
    ds.to_netcdf(save_path)
    ds.close()

    # ── Report ────────────────────────────────────────────────────────
    print(f"[CINEI] ✅ Standardization complete!")
    print(f"[CINEI] Fixes applied ({len(fixes)}):")
    for f in fixes:
        print(f"          • {f}")
    print(f"[CINEI] Output: {save_path}")
    return str(save_path)


def txt_to_netcdf(file_path, lat_col="lat", lon_col="lon",
                  month_col="month", sector_cols=None,
                  save_path=None, resolution=None):
    """
    Convert a text/CSV emission file to CINEI-standard NetCDF.

    Expected txt format (columns): lat, lon, month, sector1, sector2, ...

    Parameters
    ----------
    file_path : str
        Path to the .txt or .csv file.
    lat_col : str
        Name of the latitude column. Default: 'lat'.
    lon_col : str
        Name of the longitude column. Default: 'lon'.
    month_col : str
        Name of the month column (1-12). Default: 'month'.
    sector_cols : dict, optional
        Mapping of column names to CINEI sector names.
        e.g. {'agr': 'agriculture', 'ind': 'industry'}
        If None, auto-detected using SECTOR_ALIASES.
    save_path : str, optional
        Output .nc file path. Default: same name as input with .nc extension.
    resolution : float, optional
        Grid resolution in degrees. Auto-detected if None.

    Returns
    -------
    str
        Path to the output NetCDF file.

    Examples
    --------
    >>> import cinei
    >>> out = cinei.txt_to_netcdf(
    ...     '/path/to/emission.txt',
    ...     sector_cols={
    ...         'agr':  'agriculture',
    ...         'ind':  'industry',
    ...         'pow':  'power',
    ...         'res':  'residential',
    ...         'tra':  'transportation',
    ...     }
    ... )
    """
    import pandas as pd
    import xarray as xr

    file_path = Path(file_path)
    print(f"[CINEI] Converting: {file_path.name}")

    # ── Read file ─────────────────────────────────────────────────────
    sep = "\t" if file_path.suffix == ".txt" else ","
    try:
        df = pd.read_csv(file_path, sep=sep)
    except Exception:
        df = pd.read_csv(file_path, sep=None, engine="python")

    print(f"[CINEI] Columns   : {list(df.columns)}")
    print(f"[CINEI] Rows      : {len(df)}")

    # ── Validate required columns ─────────────────────────────────────
    for col in [lat_col, lon_col, month_col]:
        if col not in df.columns:
            raise ValueError(
                f"[CINEI] Column '{col}' not found.\n"
                f"        Available: {list(df.columns)}"
            )

    # ── Auto-detect sector columns ────────────────────────────────────
    if sector_cols is None:
        sector_cols = {}
        for col in df.columns:
            if col in [lat_col, lon_col, month_col]:
                continue
            normalized = col.lower().strip()
            if normalized in SECTOR_ALIASES:
                sector_cols[col] = SECTOR_ALIASES[normalized]
            elif normalized in CINEI_STANDARD["sectors"]:
                sector_cols[col] = normalized

        if not sector_cols:
            raise ValueError(
                f"[CINEI] No sector columns detected automatically.\n"
                f"        Please provide sector_cols manually.\n"
                f"        Example: sector_cols={{'agr': 'agriculture', "
                f"'ind': 'industry'}}\n"
                f"        Available columns: {list(df.columns)}"
            )

    print(f"[CINEI] Detected sectors: {sector_cols}")

    # ── Build coordinate arrays ───────────────────────────────────────
    lats   = np.sort(df[lat_col].unique())
    lons   = np.sort(df[lon_col].unique())
    months = np.sort(df[month_col].unique())

    if resolution is None:
        resolution = round(float(lats[1] - lats[0]), 4) if len(lats) > 1 else 0.1

    print(f"[CINEI] Grid      : {len(lats)} lats × {len(lons)} lons × "
          f"{len(months)} months")
    print(f"[CINEI] Resolution: {resolution}°")

    # ── Build xarray Dataset ──────────────────────────────────────────
    data_vars = {}
    for col, cinei_name in sector_cols.items():
        arr = np.full((len(months), len(lats), len(lons)), np.nan)
        for _, row in df.iterrows():
            mi = np.searchsorted(months, row[month_col])
            li = np.searchsorted(lats,   row[lat_col])
            lo = np.searchsorted(lons,   row[lon_col])
            arr[mi, li, lo] = row[col]
        data_vars[cinei_name] = (["month", "lat", "lon"], arr)

    # Add missing sectors as zeros
    for sector in CINEI_STANDARD["sectors"]:
        if sector != "sum" and sector not in data_vars:
            data_vars[sector] = (["month", "lat", "lon"],
                                 np.zeros((len(months), len(lats), len(lons))))
            print(f"[CINEI] ⚠️  '{sector}' not found → filled with zeros")

    # Compute sum
    sector_arrays = [data_vars[s][1] for s in CINEI_STANDARD["sectors"]
                     if s != "sum"]
    data_vars["sum"] = (["month", "lat", "lon"],
                        np.nansum(sector_arrays, axis=0))

    ds = xr.Dataset(
        data_vars,
        coords={"month": months, "lat": lats, "lon": lons}
    )
    ds.attrs["units"]           = "ton/grid/month"
    ds.attrs["resolution"]      = f"{resolution} degrees"
    ds.attrs["cinei_converted"] = "True"
    ds.attrs["source_file"]     = file_path.name

    # ── Save ──────────────────────────────────────────────────────────
    if save_path is None:
        save_path = file_path.with_suffix(".nc")
    ds.to_netcdf(save_path)
    print(f"[CINEI] ✅ Saved: {save_path}")
    return str(save_path)


def show_cinei_standard():
    """
    Print the CINEI standard format requirements.

    Examples
    --------
    >>> import cinei
    >>> cinei.show_cinei_standard()
    """
    print("=" * 60)
    print("  CINEI Standard Emission Data Format")
    print("=" * 60)
    print(f"  Format     : {CINEI_STANDARD['format']}")
    print(f"  Dimensions : {CINEI_STANDARD['dims']}")
    print(f"              month = 1–12 (integer)")
    print(f"              lat   = latitude in degrees")
    print(f"              lon   = longitude in degrees")
    print(f"  Variables  : (one per sector)")
    for s in CINEI_STANDARD["sectors"]:
        note = " ← computed automatically" if s == "sum" else ""
        print(f"              {s:<20}{note}")
    print(f"  Units      : {CINEI_STANDARD['units']}")
    print()
    print("  Accepted sector name aliases (auto-mapped):")
    by_sector = {}
    for alias, standard in SECTOR_ALIASES.items():
        by_sector.setdefault(standard, []).append(alias)
    for sector, aliases in by_sector.items():
        print(f"    {sector:<20} ← {', '.join(aliases)}")
    print("=" * 60)


# ── Internal helpers ──────────────────────────────────────────────────────────

def _check_netcdf(file_path):
    """Check a NetCDF file and return diagnosis report."""
    import xarray as xr

    ds     = xr.open_dataset(file_path)
    issues = []
    suggestions = []
    info   = {
        "dims":      dict(ds.dims),
        "variables": list(ds.data_vars),
        "attrs":     dict(ds.attrs),
    }

    # Check dimensions
    has_month = any(d in ds.dims for d in ["month", "time", "months", "mon"])
    has_lat   = any(d in ds.dims for d in ["lat", "latitude", "y", "LAT"])
    has_lon   = any(d in ds.dims for d in ["lon", "longitude", "x", "LON"])

    if not has_month:
        issues.append("❌ No month/time dimension found")
        suggestions.append(
            "Add a month dimension (1-12) or rename existing time dim")
    if not has_lat:
        issues.append("❌ No latitude dimension found")
        suggestions.append("Rename your latitude dim to 'lat'")
    if not has_lon:
        issues.append("❌ No longitude dimension found")
        suggestions.append("Rename your longitude dim to 'lon'")

    # Check dimension order
    for var in ds.data_vars:
        if len(ds[var].dims) == 3:
            if ds[var].dims != ("month", "lat", "lon"):
                issues.append(
                    f"⚠️  Variable '{var}' has dims {ds[var].dims}, "
                    f"expected (month, lat, lon)")
                suggestions.append(
                    f"Use cinei.standardize_netcdf() to auto-fix dimension order")

    # Check sector variables
    detected   = _auto_detect_sectors(list(ds.data_vars))
    found      = list(detected.values())
    missing_s  = [s for s in CINEI_STANDARD["sectors"]
                  if s not in found and s != "sum"]
    unmatched  = [v for v in ds.data_vars if v not in detected]

    if missing_s:
        issues.append(f"⚠️  Missing sectors: {missing_s}")
        suggestions.append(
            f"Provide sector_mapping to standardize_netcdf(), e.g.:\n"
            f"        sector_mapping={{'{unmatched[0] if unmatched else 'your_var'}': "
            f"'{missing_s[0]}'}}")
    if unmatched:
        issues.append(f"⚠️  Unrecognized variables: {unmatched}")
        suggestions.append(
            f"Use sector_mapping to map these to CINEI sector names")

    # Check units
    unit_found = ds.attrs.get("units", "")
    if unit_found and unit_found != CINEI_STANDARD["units"]:
        issues.append(
            f"⚠️  Units '{unit_found}' differ from CINEI standard "
            f"'{CINEI_STANDARD['units']}'")
        suggestions.append("Ensure units are Mg/month before integrating")

    ds.close()

    status = "ok" if not issues else (
        "error" if any("❌" in i for i in issues) else "warning"
    )

    # Print report
    print(f"[CINEI] ── Diagnosis Report ──────────────────────")
    print(f"[CINEI] Status    : {status.upper()}")
    print(f"[CINEI] Dims      : {info['dims']}")
    print(f"[CINEI] Variables : {info['variables']}")
    if detected:
        print(f"[CINEI] Detected sectors: {detected}")
    if issues:
        print(f"\n[CINEI] Issues found ({len(issues)}):")
        for i in issues:
            print(f"          {i}")
        print(f"\n[CINEI] Suggestions:")
        for s in suggestions:
            print(f"          → {s}")
    else:
        print(f"[CINEI] ✅ File looks compatible with CINEI standard!")
    print(f"\n[CINEI] To auto-fix: cinei.standardize_netcdf('{file_path}')")

    return {"status": status, "issues": issues,
            "suggestions": suggestions, "info": info}


def _check_txt(file_path):
    """Check a txt/csv file and return diagnosis report."""
    import pandas as pd

    issues      = []
    suggestions = []

    try:
        df = pd.read_csv(file_path, sep=None, engine="python", nrows=5)
    except Exception as e:
        return {"status": "error",
                "issues": [f"❌ Cannot read file: {e}"],
                "suggestions": ["Check file encoding and delimiter"],
                "info": {}}

    info = {"columns": list(df.columns), "sample_rows": 5}

    # Check required columns
    for col in ["lat", "lon", "month"]:
        if col not in df.columns:
            issues.append(f"⚠️  Expected column '{col}' not found")
            suggestions.append(
                f"Specify {col}_col parameter in txt_to_netcdf()")

    # Check sector columns
    detected = {}
    for col in df.columns:
        if col.lower() in SECTOR_ALIASES:
            detected[col] = SECTOR_ALIASES[col.lower()]
        elif col.lower() in CINEI_STANDARD["sectors"]:
            detected[col] = col.lower()

    if not detected:
        issues.append("⚠️  No sector columns auto-detected")
        suggestions.append(
            "Provide sector_cols={'your_col': 'agriculture'} manually")
    else:
        info["detected_sectors"] = detected

    status = "ok" if not issues else "warning"

    print(f"[CINEI] ── Diagnosis Report ──────────────────────")
    print(f"[CINEI] Status  : {status.upper()}")
    print(f"[CINEI] Columns : {info['columns']}")
    if detected:
        print(f"[CINEI] Detected sectors: {detected}")
    if issues:
        print(f"\n[CINEI] Issues ({len(issues)}):")
        for i in issues:
            print(f"          {i}")
        print(f"\n[CINEI] Suggestions:")
        for s in suggestions:
            print(f"          → {s}")
    else:
        print(f"[CINEI] ✅ File looks compatible!")
    print(f"\n[CINEI] To convert: cinei.txt_to_netcdf('{file_path}')")

    return {"status": status, "issues": issues,
            "suggestions": suggestions, "info": info}


def _find_dim(ds, candidates):
    """Find first matching dimension name from candidates."""
    for c in candidates:
        if c in ds.dims:
            return c
    return None


def _auto_detect_sectors(var_names):
    """Auto-detect sector names from variable list using aliases."""
    detected = {}
    for var in var_names:
        normalized = var.lower().strip()
        if normalized in CINEI_STANDARD["sectors"]:
            detected[var] = normalized
        elif normalized in SECTOR_ALIASES:
            detected[var] = SECTOR_ALIASES[normalized]
    return detected
