"""
Regridding utilities for CINEI.

Handles regridding of waste (CEDS), shipping and aviation (HTAP)
sector emissions to the target output grid.
"""

import numpy as np
import xarray as xr
import pandas as pd
from pathlib import Path

# ── Supported output resolutions ─────────────────────────────────────────────
SUPPORTED_RESOLUTIONS = [0.05, 0.1, 0.25, 0.5]


def build_output_grid(lon_min, lon_max, lat_min, lat_max, res):
    """
    Build xESMF-compatible output grid.

    Parameters
    ----------
    lon_min, lon_max : float
        Longitude range.
    lat_min, lat_max : float
        Latitude range.
    res : float
        Output resolution in degrees.

    Returns
    -------
    tuple: (ds_out, lon_array, lat_array)
    """
    try:
        import xesmf as xe
    except ImportError:
        raise ImportError(
            "[CINEI] xesmf is required for regridding.\n"
            "        Install with: pip install xesmf"
        )
    half = res / 2
    ds_out = xe.util.grid_2d(
        lon_min, lon_max, res,
        lat_min, lat_max, res
    )
    lon_arr = np.arange(lon_min + half, lon_max, res, dtype=np.float32)
    lat_arr = np.arange(lat_min + half, lat_max, res, dtype=np.float32)
    return ds_out, lon_arr, lat_arr


def regrid_aggregation(mon_id, meic_spec, year,
                       ceds_dir, htap_dir, mapper_path,
                       output_res=0.25,
                       lon_min=70.0, lon_max=150.0,
                       lat_min=10.0, lat_max=60.0,
                       method="conservative"):
    """
    Regrid and aggregate waste (CEDS), shipping and aviation (HTAP)
    sectors to the target output grid.

    This replaces the need for pre-computed agg_path files.
    Previously hardcoded to China 0.25°; now fully parameterized.

    Parameters
    ----------
    mon_id : int
        Month index, 0-based (0 = January, 11 = December).
    meic_spec : str
        MEIC species name (e.g. 'SO2', 'NOx').
    year : str
        Year as string (e.g. '2017').
    ceds_dir : str
        Directory containing CEDS NetCDF files.
        Expected pattern: CEDS_Glb_0.5x0.5_anthro_{spec}__monthly_{year}.nc
    htap_dir : str
        Directory containing HTAP NetCDF files.
        Expected pattern: edgar_HTAPv3_{year}_{spec}.nc
    mapper_path : str
        Path to Integrated_mapper.csv.
    output_res : float, optional
        Output grid resolution in degrees.
        Options: 0.05, 0.1, 0.25, 0.5. Default: 0.25.
    lon_min, lon_max : float, optional
        Longitude range. Default: 70.0, 150.0 (China domain).
    lat_min, lat_max : float, optional
        Latitude range. Default: 10.0, 60.0 (China domain).
    method : str, optional
        xESMF regridding method. Default: 'conservative'.

    Returns
    -------
    xr.Dataset
        Dataset with variables: waste, shipping, aviation, agriculture
        Dimensions: (lat, lon) at target resolution.
    """
    try:
        import xesmf as xe
    except ImportError:
        raise ImportError(
            "[CINEI] xesmf is required for regridding.\n"
            "        Install with: pip install xesmf"
        )

    if output_res not in SUPPORTED_RESOLUTIONS:
        raise ValueError(
            f"[CINEI] Unsupported resolution: {output_res}\n"
            f"        Available: {SUPPORTED_RESOLUTIONS}"
        )

    ceds_dir = Path(ceds_dir)
    htap_dir = Path(htap_dir)

    # ── Read mapper ───────────────────────────────────────────────────
    mapper = pd.read_csv(mapper_path)
    mapper = mapper.set_index('MEIC')
    par = mapper.loc[meic_spec, 'partition']
    M   = mapper.loc[meic_spec, 'weight']
    V   = mapper.loc[meic_spec, 'if VOC']

    # ── Build grids ───────────────────────────────────────────────────
    ds_out, lon_out, lat_out = build_output_grid(
        lon_min, lon_max, lat_min, lat_max, output_res
    )

    # 0.5° grid (CEDS)
    lon_50 = np.arange(lon_min + 0.25, lon_max + 0.25, 0.5, dtype=np.float32)
    lat_50 = np.arange(lat_min + 0.25, lat_max + 0.25, 0.5, dtype=np.float32)
    ds_coarse = xe.util.grid_2d(
        lon_min + 0.25, lon_max + 0.25, 0.5,
        lat_min + 0.25, lat_max + 0.25, 0.5
    )

    # 0.1° grid (HTAP)
    lon_10 = np.arange(lon_min + 0.05, lon_max + 0.05, 0.1, dtype=np.float32)
    lat_10 = np.arange(lat_min + 0.05, lat_max + 0.05, 0.1, dtype=np.float32)
    ds_fine = xe.util.grid_2d(
        lon_min + 0.05, lon_max + 0.05, 0.1,
        lat_min + 0.05, lat_max + 0.05, 0.1
    )

    # ── Grid cell areas ───────────────────────────────────────────────
    from .utils import ll_area
    area_fine   = ll_area(ds_fine.lat.values,   0.1)
    area_coarse = ll_area(ds_coarse.lat.values, 0.5)

    n_lat = len(lat_out)
    n_lon = len(lon_out)

    # ── 1. Waste (from CEDS) ──────────────────────────────────────────
    mapper_ceds   = mapper.dropna()
    specs_ceds    = mapper_ceds.index.values
    ceds_spec     = mapper.loc[meic_spec, 'CEDS'] if meic_spec in specs_ceds else None

    if ceds_spec is not None:
        ceds_waste_path = ceds_dir / f"CEDS_Glb_0.5x0.5_anthro_{ceds_spec}__monthly_{year}.nc"
        if ceds_waste_path.exists():
            DS_wst = xr.open_dataset(str(ceds_waste_path))
            re_wst = DS_wst['waste'][mon_id].sel(
                lat=lat_50, lon=lon_50, method="nearest")
            ds_coarse['wst'] = re_wst * 0.001 * area_coarse * 2678400 * 1000000
            regridder_cs = xe.Regridder(
                ds_coarse, ds_out, method, periodic=True, reuse_weights=True)
            wst_raw = regridder_cs(ds_coarse['wst'].values)
            waste = wst_raw * par / M if V == 'Y' else wst_raw
        else:
            print(f"[CINEI] ⚠️  CEDS waste file not found: {ceds_waste_path.name}")
            waste = np.zeros((n_lat, n_lon), dtype='float32')
    else:
        waste = np.zeros((n_lat, n_lon), dtype='float32')

    # ── 2. Shipping (from HTAP) ───────────────────────────────────────
    htap_path = htap_dir / f"edgar_HTAPv3_{year}_{meic_spec}.nc"
    if not htap_path.exists():
        print(f"[CINEI] ⚠️  HTAP file not found: {htap_path.name}")
        shipping  = np.zeros((n_lat, n_lon), dtype='float32')
        aviation  = np.zeros((n_lat, n_lon), dtype='float32')
        agr_htap  = np.zeros((n_lat, n_lon), dtype='float32')
    else:
        DS_htap = xr.open_dataset(str(htap_path))

        # Shipping
        re_shp = DS_htap['HTAPv3_5_3_Domestic_shipping'][mon_id].sel(
            lat=lat_10, lon=lon_10, method="nearest")
        ds_fine['shp'] = re_shp * area_fine
        regridder_fn = xe.Regridder(
            ds_fine, ds_out, method, periodic=True, reuse_weights=True)
        shp_raw  = regridder_fn(ds_fine['shp'].values)
        shipping = shp_raw / M if V == 'Y' else shp_raw

        # Aviation
        re_avi = DS_htap['HTAPv3_2_1_Domestic_Aviation'][mon_id].sel(
            lat=lat_10, lon=lon_10, method="nearest")
        ds_fine['avi'] = re_avi * area_fine
        avi_raw  = regridder_fn(ds_fine['avi'].values)
        aviation = avi_raw / M if V == 'Y' else avi_raw

        # Agriculture (outside region, from HTAP)
        re_agr = DS_htap['HTAPv3_4A_Enteric_Fermentation'][mon_id].sel(
            lat=lat_10, lon=lon_10, method="nearest") \
            if 'HTAPv3_4A_Enteric_Fermentation' in DS_htap else \
            xr.zeros_like(re_avi)
        ds_fine['agr'] = re_agr * area_fine
        agr_raw  = regridder_fn(ds_fine['agr'].values)
        agr_htap = agr_raw / M if V == 'Y' else agr_raw

        DS_htap.close()

    # ── Build output Dataset ──────────────────────────────────────────
    ds = xr.Dataset(
        {
            "waste":       (("lat", "lon"), waste.astype('float32')),
            "shipping":    (("lat", "lon"), shipping.astype('float32')),
            "aviation":    (("lat", "lon"), aviation.astype('float32')),
            "agriculture": (("lat", "lon"), agr_htap.astype('float32')),
        },
        coords={'lon': lon_out, 'lat': lat_out}
    )
    ds.attrs['resolution'] = f"{output_res}°"
    ds.attrs['year']       = year
    ds.attrs['month_idx']  = mon_id

    return ds
