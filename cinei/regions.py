"""
Region of interest utilities for CINEI.

Allows users to specify regions by country name, city name,
or bounding box coordinates.
"""

import numpy as np
from pathlib import Path


# ── Known region presets ──────────────────────────────────────────────────────
REGION_PRESETS = {
    # Countries
    "china":       (70.0,  150.0,  10.0,  60.0),
    "india":       (65.0,  100.0,   5.0,  40.0),
    "usa":         (-130.0, -60.0, 20.0,  55.0),
    "europe":      (-15.0,  45.0,  35.0,  75.0),
    "germany":     (  5.5,  15.5,  47.0,  55.5),
    "japan":       (125.0, 148.0,  30.0,  46.0),
    "korea":       (124.0, 132.0,  33.0,  39.0),
    # Chinese regions
    "ncp":         (112.0, 120.0,  35.0,  42.0),  # North China Plain
    "yangtze":     (108.0, 122.0,  27.0,  35.0),  # Yangtze River Delta
    "prd":         (111.0, 117.0,  21.0,  25.5),  # Pearl River Delta
    "sichuan":     (100.0, 110.0,  26.0,  34.0),  # Sichuan Basin
    # Cities (approximate 2° buffer)
    "beijing":     (114.0, 118.5,  38.5,  42.0),
    "shanghai":    (119.0, 123.5,  29.5,  33.0),
    "guangzhou":   (111.5, 115.0,  21.5,  24.5),
    "chengdu":     (101.5, 105.5,  28.5,  32.0),
    "global":      (-180.0, 180.0, -90.0,  90.0),
}


def get_region_bbox(region=None, country_shp=None,
                    lon_min=None, lon_max=None,
                    lat_min=None, lat_max=None,
                    global_domain=False):
    """
    Resolve region of interest to bounding box (lon_min, lon_max, lat_min, lat_max).

    Priority order:
    1. global_domain=True → global extent
    2. Manual bbox (lon_min/max, lat_min/max all provided)
    3. region name → lookup in presets or shapefile
    4. Default → China domain

    Parameters
    ----------
    region : str, optional
        Country or city name. Case-insensitive.
        Built-in presets: China, India, USA, Europe, Germany, Japan,
        Korea, NCP, Yangtze, PRD, Sichuan, Beijing, Shanghai, etc.
        If not in presets, looks up in country_shp by 'CNTRY_NAME'.
    country_shp : str, optional
        Path to country shapefile for dynamic lookup.
        Used when region is not in built-in presets.
    lon_min, lon_max, lat_min, lat_max : float, optional
        Manual bounding box. All four must be provided together.
    global_domain : bool, optional
        If True, return global extent. Default False.

    Returns
    -------
    tuple : (lon_min, lon_max, lat_min, lat_max, region_name)

    Examples
    --------
    >>> from cinei.regions import get_region_bbox

    >>> # By name
    >>> get_region_bbox(region='China')
    (70.0, 150.0, 10.0, 60.0, 'China')

    >>> # By city
    >>> get_region_bbox(region='Beijing')
    (114.0, 118.5, 38.5, 42.0, 'Beijing')

    >>> # Manual bbox
    >>> get_region_bbox(lon_min=100, lon_max=130, lat_min=20, lat_max=45)
    (100, 130, 20, 45, 'custom_100-130E_20-45N')

    >>> # Global
    >>> get_region_bbox(global_domain=True)
    (-180.0, 180.0, -90.0, 90.0, 'global')
    """
    # ── 1. Global ─────────────────────────────────────────────────────
    if global_domain:
        print(f"[CINEI] Region     : global")
        return (-180.0, 180.0, -90.0, 90.0, "global")

    # ── 2. Manual bbox ────────────────────────────────────────────────
    if all(v is not None for v in [lon_min, lon_max, lat_min, lat_max]):
        name = f"custom_{lon_min}-{lon_max}E_{lat_min}-{lat_max}N"
        print(f"[CINEI] Region     : {name}")
        return (lon_min, lon_max, lat_min, lat_max, name)

    # ── 3. Region name ────────────────────────────────────────────────
    if region is not None:
        key = region.lower().strip()

        # Check built-in presets first
        if key in REGION_PRESETS:
            bbox = REGION_PRESETS[key]
            print(f"[CINEI] Region     : {region} "
                  f"(lon {bbox[0]}–{bbox[1]}, lat {bbox[2]}–{bbox[3]})")
            return (*bbox, region.title())

        # Try shapefile lookup
        if country_shp is not None and Path(country_shp).exists():
            bbox = _lookup_country_shp(region, country_shp)
            if bbox:
                print(f"[CINEI] Region     : {region} "
                      f"(lon {bbox[0]:.1f}–{bbox[1]:.1f}, "
                      f"lat {bbox[2]:.1f}–{bbox[3]:.1f})")
                return (*bbox, region.title())

        # Not found
        available = list(REGION_PRESETS.keys())
        raise ValueError(
            f"[CINEI] Region '{region}' not found.\n"
            f"        Built-in presets: {available}\n"
            f"        Or provide manual bbox: "
            f"lon_min, lon_max, lat_min, lat_max\n"
            f"        Or provide country_shp for dynamic lookup."
        )

    # ── 4. Default: China ─────────────────────────────────────────────
    print(f"[CINEI] Region     : China (default)")
    return REGION_PRESETS["china"] + ("China",)


def check_data_coverage(data_lon_min, data_lon_max,
                        data_lat_min, data_lat_max,
                        region_lon_min, region_lon_max,
                        region_lat_min, region_lat_max,
                        region_name=""):
    """
    Check if data domain covers the requested region of interest.

    Parameters
    ----------
    data_lon_min/max, data_lat_min/max : float
        Extent of the input data.
    region_lon_min/max, region_lat_min/max : float
        Requested region of interest.
    region_name : str
        Name for display purposes.

    Returns
    -------
    bool
        True if data fully covers the region.

    Raises
    ------
    ValueError if data does not cover the region.
    """
    covered = (
        data_lon_min <= region_lon_min and
        data_lon_max >= region_lon_max and
        data_lat_min <= region_lat_min and
        data_lat_max >= region_lat_max
    )

    if not covered:
        raise ValueError(
            f"[CINEI] Data does not cover the requested region!\n"
            f"        Region '{region_name}': "
            f"lon [{region_lon_min}, {region_lon_max}], "
            f"lat [{region_lat_min}, {region_lat_max}]\n"
            f"        Data extent: "
            f"lon [{data_lon_min:.2f}, {data_lon_max:.2f}], "
            f"lat [{data_lat_min:.2f}, {data_lat_max:.2f}]\n"
            f"        Please choose a smaller region or use "
            f"a dataset with wider coverage."
        )
    return True


def list_regions():
    """Print all available built-in region presets."""
    print("[CINEI] Built-in region presets:")
    print(f"  {'Name':<15} {'Lon min':>8} {'Lon max':>8} "
          f"{'Lat min':>8} {'Lat max':>8}")
    print(f"  {'-'*55}")
    for name, (lon0, lon1, lat0, lat1) in REGION_PRESETS.items():
        print(f"  {name.title():<15} {lon0:>8.1f} {lon1:>8.1f} "
              f"{lat0:>8.1f} {lat1:>8.1f}")


# ── Internal helpers ──────────────────────────────────────────────────────────

def _lookup_country_shp(region_name, country_shp_path):
    """Look up country bounds from shapefile."""
    try:
        import geopandas as gpd
        gdf = gpd.read_file(country_shp_path)

        # Try different common column names
        for col in ['CNTRY_NAME', 'NAME', 'name', 'country', 'COUNTRY']:
            if col in gdf.columns:
                match = gdf[gdf[col].str.lower() == region_name.lower()]
                if not match.empty:
                    bounds = match.total_bounds  # [minx, miny, maxx, maxy]
                    # Add 1° buffer
                    return (
                        float(bounds[0]) - 1.0,
                        float(bounds[2]) + 1.0,
                        float(bounds[1]) - 1.0,
                        float(bounds[3]) + 1.0,
                    )
    except Exception as e:
        print(f"[CINEI] ⚠️  Shapefile lookup failed: {e}")
    return None
