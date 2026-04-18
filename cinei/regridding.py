"""
Regridding utilities for CINEI.
Uses scipy for interpolation — no ESMF/xesmf dependency required.
"""

import numpy as np
import xarray as xr
import pandas as pd
from pathlib import Path
from scipy.interpolate import RegularGridInterpolator

SUPPORTED_RESOLUTIONS = [0.05, 0.1, 0.25, 0.5]


def _regrid(data, src_lat, src_lon, dst_lat, dst_lon, method='linear'):
    """
    Regrid 2D data from source to destination grid using scipy.

    Parameters
    ----------
    data : np.ndarray, shape (n_src_lat, n_src_lon)
    src_lat, src_lon : 1D arrays — source grid coordinates
    dst_lat, dst_lon : 1D arrays — destination grid coordinates
    method : str — 'linear' or 'nearest'

    Returns
    -------
    np.ndarray, shape (n_dst_lat, n_dst_lon)
    """
    # Replace NaN with 0 for interpolation
    data_filled = np.nan_to_num(data, nan=0.0)

    # Build interpolator
    interp = RegularGridInterpolator(
        (src_lat, src_lon),
        data_filled,
        method=method,
        bounds_error=False,
        fill_value=0.0,
    )

    # Build destination mesh
    dst_lon_2d, dst_lat_2d = np.meshgrid(dst_lon, dst_lat)
    pts = np.column_stack([dst_lat_2d.ravel(), dst_lon_2d.ravel()])

    result = interp(pts).reshape(len(dst_lat), len(dst_lon))
    return result.astype('float32')


def _regrid_conservative(data, src_lat, src_lon,
                         dst_lat, dst_lon, dst_res):
    """
    Conservative regridding: sum source cells into destination cells.
    Preserves total emissions (ton/month).

    For HTAP data: all variables are ton/month at 0.1°.
    Summing 0.1° cells → 0.25° cell preserves total.

    Parameters
    ----------
    data : np.ndarray (n_src_lat, n_src_lon)
        Source data in ton/month at source resolution.
    src_lat, src_lon : 1D arrays
        Source grid center coordinates (must be sorted ascending).
    dst_lat, dst_lon : 1D arrays
        Destination grid center coordinates.
    dst_res : float
        Destination resolution in degrees.

    Returns
    -------
    np.ndarray (n_dst_lat, n_dst_lon)
        Aggregated data in ton/month at destination resolution.
    """
    n_dst_lat = len(dst_lat)
    n_dst_lon = len(dst_lon)
    result    = np.zeros((n_dst_lat, n_dst_lon), dtype='float32')
    half      = dst_res / 2.0

    # Pre-compute source index ranges for each destination cell
    for i, dlat in enumerate(dst_lat):
        lat_idx = np.where(
            (src_lat >= dlat - half) & (src_lat < dlat + half))[0]
        if len(lat_idx) == 0:
            continue
        for j, dlon in enumerate(dst_lon):
            lon_idx = np.where(
                (src_lon >= dlon - half) & (src_lon < dlon + half))[0]
            if len(lon_idx) == 0:
                continue
            result[i, j] = np.nansum(
                data[lat_idx[0]:lat_idx[-1]+1,
                     lon_idx[0]:lon_idx[-1]+1])

    return result


def _check_conservation(htap_file, mon_id, lat_mask, lon_mask,
                        results, htap_vars):
    """
    Print conservation ratio table for regridded HTAP sectors.

    Conservation ratio = sum(output at dst resolution) /
                         sum(input at src resolution)
    Expected: ~1.0 for all sectors.

    Notes
    -----
    - aviation, waste, agriculture: ratio should be exactly 1.0
    - shipping: ratio may be > 1.0 because emis_union also adds
      CEDS international shipping outside China on top of HTAP
      domestic shipping. The regridding ratio itself should be ~1.0.
    """
    if htap_file is None:
        print("[CINEI] ⚠️  Conservation check skipped: HTAP file not found")
        return

    import xarray as xr
    DS = xr.open_dataset(str(htap_file))

    print(f"\n[CINEI] ── Regridding Conservation Check ────────────────")
    print(f"[CINEI] {'Sector':<15} {'Src total':>12} "
          f"{'Dst total':>12} {'Ratio':>8}  {'Status'}")
    print(f"[CINEI] {'-'*60}")

    for sector, var_name in htap_vars.items():
        # Source total
        if isinstance(var_name, list):
            src_total = sum(
                DS[v][mon_id].values[np.ix_(lat_mask, lon_mask)].sum()
                for v in var_name if v in DS
            )
        else:
            if var_name not in DS:
                print(f"[CINEI] {sector:<15} {'N/A':>12} {'N/A':>12} "
                      f"{'N/A':>8}  ⚠️  var not in HTAP")
                continue
            src_total = DS[var_name][mon_id].values[
                np.ix_(lat_mask, lon_mask)].sum()

        # Destination total
        dst_total = results[sector].sum()

        ratio  = dst_total / src_total if src_total > 0 else 0.0
        status = "✅" if 0.99 <= ratio <= 1.01 else "⚠️"

        # Special note for shipping
        note = ""
        if sector == "shipping":
            note = "  (CEDS ships added separately in emis_union)"
            status = "✅" if 0.99 <= ratio <= 1.01 else "ℹ️"

        print(f"[CINEI] {sector:<15} {src_total:>12.2f} "
              f"{dst_total:>12.2f} {ratio:>8.4f}  {status}{note}")

    print(f"[CINEI] {'-'*60}")
    print(f"[CINEI] Note: ratio=1.0 means total emissions are exactly")
    print(f"[CINEI]       conserved from source to target resolution.")
    print()
    DS.close()


def regrid_aggregation(mon_id, meic_spec, year,
                       ceds_dir, htap_dir, mapper_path,
                       output_res=0.25,
                       lon_min=70.0, lon_max=150.0,
                       lat_min=10.0, lat_max=60.0,
                       method="linear",
                       check_conservation=True):
    """
    Regrid and aggregate waste (CEDS), shipping and aviation (HTAP)
    sectors to the target output grid using scipy interpolation.

    Parameters
    ----------
    mon_id : int
        Month index, 0-based (0 = January).
    meic_spec : str
        MEIC species name (e.g. 'NMVOC', 'SO2').
    year : str
        Year as string (e.g. '2017').
    ceds_dir : str
        Directory containing CEDS NetCDF files.
    htap_dir : str
        Directory containing HTAP NetCDF files.
        Pattern: edgar_HTAPv3_{year}_{spec}.nc
    mapper_path : str
        Path to Integrated_mapper.csv.
    output_res : float, optional
        Output resolution in degrees. Default: 0.25.
    lon_min, lon_max : float, optional
        Longitude range. Default: 70.0, 150.0.
    lat_min, lat_max : float, optional
        Latitude range. Default: 10.0, 60.0.
    method : str, optional
        Interpolation method: 'linear' or 'nearest'. Default: 'linear'.
    check_conservation : bool, optional
        If True, print conservation ratio table after regridding.
        Ratio = sum(output) / sum(input) — expected ~1.0 for all sectors.
        Shipping may differ slightly (CEDS ships added in emis_union).
        Default: True.

    Returns
    -------
    xr.Dataset
        Dataset with variables: waste, shipping, aviation, agriculture.
        Dimensions: (lat, lon) at target resolution.
    """
    if output_res not in SUPPORTED_RESOLUTIONS:
        raise ValueError(
            f"[CINEI] Unsupported resolution: {output_res}\n"
            f"        Available: {SUPPORTED_RESOLUTIONS}"
        )

    ceds_dir = Path(ceds_dir)
    htap_dir = Path(htap_dir)

    # ── Read mapper ───────────────────────────────────────────────────
    mapper    = pd.read_csv(mapper_path)
    mapper    = mapper.set_index('MEIC')
    par       = mapper.loc[meic_spec, 'partition']
    M         = mapper.loc[meic_spec, 'weight']
    V         = mapper.loc[meic_spec, 'if VOC']

    # ── Output grid ───────────────────────────────────────────────────
    half    = output_res / 2
    lon_out = np.arange(lon_min + half, lon_max, output_res, dtype=np.float32)
    lat_out = np.arange(lat_min + half, lat_max, output_res, dtype=np.float32)
    n_lat   = len(lat_out)
    n_lon   = len(lon_out)

    from .utils import ll_area
    lon_2d_out, lat_2d_out = np.meshgrid(lon_out, lat_out)

    # ── 1. Waste (from CEDS) ──────────────────────────────────────────
    mapper_ceds = mapper.dropna()
    ceds_spec   = mapper.loc[meic_spec, 'CEDS'] \
                  if meic_spec in mapper_ceds.index else None

    waste = np.zeros((n_lat, n_lon), dtype='float32')
    if ceds_spec is not None:
        ceds_path = ceds_dir / \
            f"CEDS_Glb_0.5x0.5_anthro_{ceds_spec}__monthly_{year}.nc"
        if ceds_path.exists():
            DS_wst   = xr.open_dataset(str(ceds_path))
            lat_50   = DS_wst.lat.values
            lon_50   = DS_wst.lon.values
            wst_data = DS_wst['waste'][mon_id].values  # (lat, lon)

            # Convert units
            lon_2d_50, lat_2d_50 = np.meshgrid(lon_50, lat_50)
            area_50  = ll_area(lat_2d_50, 0.5)
            wst_conv = wst_data * 0.001 * area_50 * 2678400 * 1000000

            # Clip to domain
            lat_mask = (lat_50 >= lat_min) & (lat_50 <= lat_max)
            lon_mask = (lon_50 >= lon_min) & (lon_50 <= lon_max)
            lat_src  = lat_50[lat_mask]
            lon_src  = lon_50[lon_mask]
            wst_src  = wst_conv[np.ix_(lat_mask, lon_mask)]

            # Regrid
            wst_raw = _regrid(wst_src, lat_src, lon_src,
                               lat_out, lon_out, method)
            waste   = wst_raw * par / M if V == 'Y' else wst_raw
            DS_wst.close()
        else:
            print(f"[CINEI] ⚠️  CEDS waste file not found: {ceds_path.name}")

    # ── 2. HTAP sectors (shipping, aviation, agriculture) ─────────────
    shipping  = np.zeros((n_lat, n_lon), dtype='float32')
    aviation  = np.zeros((n_lat, n_lon), dtype='float32')
    agr_htap  = np.zeros((n_lat, n_lon), dtype='float32')

    # Look for HTAP file — check both in htap_dir and subdirectories
    htap_file = htap_dir / f"edgar_HTAPv3_{year}_{meic_spec}.nc"
    if not htap_file.exists():
        # Try in subdirectory gridmaps_05x05_emissions_NMVOC/
        for sub in htap_dir.rglob(f"edgar_HTAPv3_{year}_{meic_spec}.nc"):
            htap_file = sub
            break

    if htap_file.exists():
        DS_htap  = xr.open_dataset(str(htap_file))
        lat_10   = DS_htap.lat.values
        lon_10   = DS_htap.lon.values
        lat_mask = (lat_10 >= lat_min) & (lat_10 <= lat_max)
        lon_mask = (lon_10 >= lon_min) & (lon_10 <= lon_max)
        lat_src  = lat_10[lat_mask]
        lon_src  = lon_10[lon_mask]

        def _regrid_htap(var_name):
            if var_name not in DS_htap:
                print(f"[CINEI] ⚠️  HTAP variable not found: {var_name}")
                return np.zeros((n_lat, n_lon), dtype='float32')
            # HTAP unit: ton/month/grid at 0.1°
            # Regrid to output resolution conservatively (sum, not interpolate)
            data     = DS_htap[var_name][mon_id].values  # no area multiplication
            data_src = data[np.ix_(lat_mask, lon_mask)]
            raw      = _regrid_conservative(data_src, lat_src, lon_src,
                                             lat_out, lon_out, output_res)
            return raw / M if V == 'Y' else raw

        shipping = _regrid_htap('HTAPv3_5_3_Domestic_shipping')
        aviation = _regrid_htap('HTAPv3_2_1_Domestic_Aviation')
        waste    = _regrid_htap('HTAPv3_7_Waste')
        agr_live = _regrid_htap('HTAPv3_8_2_Agriculture_livestock')
        agr_crop = _regrid_htap('HTAPv3_8_3_Agriculture_crops')
        agr_htap = agr_live + agr_crop
        DS_htap.close()
    else:
        print(f"[CINEI] ⚠️  HTAP file not found: "
              f"edgar_HTAPv3_{year}_{meic_spec}.nc")
        print(f"[CINEI]    Searched in: {htap_dir}")

    # ── Conservation check ───────────────────────────────────────────
    if check_conservation:
        _check_conservation(
            htap_file   = htap_file if htap_file.exists() else None,
            mon_id      = mon_id,
            lat_mask    = lat_mask if htap_file.exists() else None,
            lon_mask    = lon_mask if htap_file.exists() else None,
            results     = {
                'aviation':    aviation,
                'waste':       waste,
                'agriculture': agr_htap,
                'shipping':    shipping,
            },
            htap_vars   = {
                'aviation':    'HTAPv3_2_1_Domestic_Aviation',
                'waste':       'HTAPv3_7_Waste',
                'agriculture': ['HTAPv3_8_2_Agriculture_livestock',
                                'HTAPv3_8_3_Agriculture_crops'],
                'shipping':    'HTAPv3_5_3_Domestic_shipping',
            }
        )

    # ── Build output Dataset ──────────────────────────────────────────
    ds = xr.Dataset(
        {
            "waste":       (("lat", "lon"), waste),
            "shipping":    (("lat", "lon"), shipping),
            "aviation":    (("lat", "lon"), aviation),
            "agriculture": (("lat", "lon"), agr_htap),
        },
        coords={'lon': lon_out, 'lat': lat_out}
    )
    ds.attrs['resolution'] = f"{output_res}°"
    ds.attrs['year']       = year
    ds.attrs['month_idx']  = mon_id
    return ds
