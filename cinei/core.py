"""Core functionality for CINEI emission integration."""

import pandas as pd
import rioxarray
import xarray as xr
import numpy as np
import geopandas as gpd
import fnmatch
import os
from pathlib import Path
from .utils import ll_area
from .regridding import regrid_aggregation, build_output_grid, SUPPORTED_RESOLUTIONS


def emis_union(ceds_dir, meic_dir, save_dir, spec_ceds, spec_meic,
               mon, mon_id, mon_agg, year,
               mapper_path, country_shp, province_shp,
               htap_dir=None, agg_dir=None,
               output_res=0.25,
               global_domain=False,
               lon_min=70.0, lon_max=150.0,
               lat_min=10.0, lat_max=60.0):
    """
    Integrate emissions data from CEDS (global background) and MEIC
    (regional) inventories onto a unified output grid.

    Parameters
    ----------
    ceds_dir : str
        Directory for CEDS NetCDF files.
        Pattern: CEDS_Glb_0.5x0.5_anthro_{spec}__monthly_{year}.nc
    meic_dir : str
        Directory for MEIC NetCDF files.
        Pattern: {year}_{month:02d}_{sector}_{spec}.nc
    save_dir : str
        Directory to save integrated output NetCDF files.
    spec_ceds : str
        CEDS species name (e.g. 'SO2', 'NOx', 'BC').
    spec_meic : str
        MEIC species name (e.g. 'SO2', 'NOx', 'PMcoarse').
    mon : str
        Month name abbreviation (e.g. 'Jan', 'Feb').
    mon_id : int
        Month index, 0-based (0 = January).
    mon_agg : str
        Month string for legacy agg_dir files (e.g. '01', '02').
        Only used when agg_dir is provided.
    year : str
        Year as string (e.g. '2017').
    mapper_path : str
        Path to Integrated_mapper.csv.
    country_shp : str
        Path to world country shapefile (must have 'CNTRY_NAME' column).
    province_shp : str
        Path to China province shapefile (must have '行政区划_c' column).
    htap_dir : str, optional
        Directory containing HTAP NetCDF files for regridding.
        If provided, regrid_aggregation() is called automatically.
        Pattern: edgar_HTAPv3_{year}_{spec}.nc
    agg_dir : str, optional
        Legacy: directory with pre-computed aggregated sector files.
        Used only when htap_dir is None.
        Pattern: regridded_aggregated_sectors1{year}{mon_agg}_{spec}.nc
    output_res : float, optional
        Output grid resolution in degrees.
        Options: 0.05, 0.1, 0.25, 0.5. Default: 0.25.
    global_domain : bool, optional
        If True, use global extent (-180 to 180, -90 to 90).
        If False, use regional extent defined by lon_min/max, lat_min/max.
        Default: False (China regional domain).
    lon_min, lon_max : float, optional
        Longitude range for regional domain. Default: 70.0, 150.0.
        Ignored when global_domain=True.
    lat_min, lat_max : float, optional
        Latitude range for regional domain. Default: 10.0, 60.0.
        Ignored when global_domain=True.

    Returns
    -------
    str
        Path to the output integrated NetCDF file.

    Examples
    --------
    >>> import cinei
    >>> # Regional (China, 0.25°) — default
    >>> output = cinei.emis_union(
    ...     ceds_dir='/work/bb1554/data/CEDS',
    ...     meic_dir='/work/bb1554/data/MEIC/2017',
    ...     save_dir='/work/bb1554/output/cinei',
    ...     spec_ceds='SO2', spec_meic='SO2',
    ...     mon='Jan', mon_id=0, mon_agg='01', year='2017',
    ...     mapper_path='/work/bb1554/data/Integrated_mapper.csv',
    ...     country_shp='/work/bb1554/data/shapefiles/country.shp',
    ...     province_shp='/work/bb1554/data/shapefiles/province.shp',
    ...     htap_dir='/work/bb1554/data/HTAP',
    ... )

    >>> # Custom region at 0.1° resolution
    >>> output = cinei.emis_union(
    ...     ...,
    ...     output_res=0.1,
    ...     global_domain=False,
    ...     lon_min=100.0, lon_max=130.0,
    ...     lat_min=20.0,  lat_max=45.0,
    ... )

    >>> # Global domain at 0.5°
    >>> output = cinei.emis_union(
    ...     ...,
    ...     output_res=0.5,
    ...     global_domain=True,
    ... )
    """
    # ── Validate resolution ───────────────────────────────────────────
    if output_res not in SUPPORTED_RESOLUTIONS:
        raise ValueError(
            f"[CINEI] Unsupported output_res: {output_res}\n"
            f"        Available: {SUPPORTED_RESOLUTIONS}"
        )

    # ── Set domain ────────────────────────────────────────────────────
    if global_domain:
        _lon_min, _lon_max = -180.0, 180.0
        _lat_min, _lat_max =  -90.0,  90.0
        print(f"[CINEI] Domain     : Global")
    else:
        _lon_min, _lon_max = lon_min, lon_max
        _lat_min, _lat_max = lat_min, lat_max
        print(f"[CINEI] Domain     : Regional "
              f"({_lon_min}–{_lon_max}°E, {_lat_min}–{_lat_max}°N)")

    print(f"[CINEI] Resolution : {output_res}°")
    print(f"[CINEI] Species    : CEDS={spec_ceds}, MEIC={spec_meic}")
    print(f"[CINEI] Month      : {mon} (index {mon_id})")
    print()

    # ── Validate input paths ──────────────────────────────────────────
    _check_path(ceds_dir,    'ceds_dir')
    _check_path(meic_dir,    'meic_dir')
    _check_path(mapper_path, 'mapper_path')
    _check_path(country_shp, 'country_shp')
    _check_path(province_shp,'province_shp')
    if agg_dir:
        _check_path(agg_dir, 'agg_dir')
    os.makedirs(save_dir, exist_ok=True)

    # ── Build output coordinate arrays ────────────────────────────────
    half = output_res / 2
    lon_arange = np.arange(_lon_min + half, _lon_max, output_res,
                           dtype=np.float32)
    lat_arange = np.arange(_lat_min + half, _lat_max, output_res,
                           dtype=np.float32)

    # ── Read CEDS (global background) data ───────────────────────────
    pre_ceds  = 'CEDS_Glb_0.5x0.5_anthro_'
    post_ceds = f'__monthly_{year}.nc'
    ceds_path = os.path.join(ceds_dir, pre_ceds + spec_ceds + post_ceds)
    if spec_ceds == 'BC':
        ceds_path = os.path.join(
            ceds_dir, 'CEDS_Glb_0.5x0.5_anthro_BC__monthly_2016.nc')

    ds = rioxarray.open_rasterio(ceds_path, masked=True)
    re_lat = np.arange(ds.y.values.min(), ds.y.values.max(), output_res)
    re_lon = np.arange(ds.x.values.min(), ds.x.values.max(), output_res)
    emis_all   = ds.interp(y=re_lat, x=re_lon)
    emis_all   = emis_all.isel(time=mon_id)
    global_bg  = emis_all.sel(x=lon_arange, y=lat_arange, method="nearest")

    # ── Calculate grid cell area ──────────────────────────────────────
    lon_2d, lat_2d = np.meshgrid(lon_arange, lat_arange)
    area = ll_area(lat_2d, output_res)

    # ── Unit conversion using mapper ──────────────────────────────────
    mapper   = pd.read_csv(mapper_path)
    mapper   = mapper.set_index('MEIC')
    meic_spec = spec_meic
    par = mapper.loc[meic_spec, 'partition']
    M   = mapper.loc[meic_spec, 'weight']
    V   = mapper.loc[meic_spec, 'if VOC']
    if V == 'Y':
        unit_global_bg = global_bg * 0.001 * area * 2678400 * 1000000 * par / M
    else:
        unit_global_bg = global_bg * 0.001 * area * 2678400 * 1000000 * par

    # ── Clip global background to region (excluding Taiwan if China) ──
    country    = gpd.read_file(country_shp)
    China_shp  = country[country['CNTRY_NAME'] == 'China']
    province   = gpd.read_file(province_shp)
    Taiwan_shp = province[province['行政区划_c'] == '台湾省']
    mChina     = gpd.overlay(China_shp, Taiwan_shp, how='difference')

    unit_global_bg.rio.write_crs("epsg:4326", inplace=True)
    global_bg_clipped = unit_global_bg.rio.clip(
        mChina.geometry, mChina.crs, drop=False, invert=True)

    # ── Get aggregated sectors (waste, shipping, aviation, agr) ──────
    if htap_dir is not None:
        # ── Auto-regrid using regrid_aggregation() ────────────────────
        print(f"[CINEI] Regridding sectors from HTAP/CEDS...")
        ds_agg = regrid_aggregation(
            mon_id      = mon_id,
            meic_spec   = meic_spec,
            year        = year,
            ceds_dir    = ceds_dir,
            htap_dir    = htap_dir,
            mapper_path = mapper_path,
            output_res  = output_res,
            lon_min     = _lon_min,
            lon_max     = _lon_max,
            lat_min     = _lat_min,
            lat_max     = _lat_max,
        )
        allwst   = ds_agg['waste'].values
        alldoshp = ds_agg['shipping'].values
        all_avi  = ds_agg['aviation'].values
        doagr    = ds_agg['agriculture'].values

        # Clip agriculture to outside China
        ds_agg.rio.write_crs("epsg:4326", inplace=True)
        agg_clipped = ds_agg.rio.clip(
            mChina.geometry, mChina.crs, drop=False, invert=True)
        doagr_clip = np.nan_to_num(
            agg_clipped['agriculture'].values, nan=0)
        dms_agr = doagr - doagr_clip[::-1]

    elif agg_dir is not None:
        # ── Legacy: read pre-computed agg files ───────────────────────
        agg_path = os.path.join(
            agg_dir,
            f'regridded_aggregated_sectors1{year}{mon_agg}_{meic_spec}.nc')
        _check_path(agg_path, 'agg_path (derived)')
        ds_agg_raster = rioxarray.open_rasterio(agg_path, masked=True)
        ds_agg_raster.rio.write_crs("epsg:4326", inplace=True)
        agg_clipped = ds_agg_raster.rio.clip(
            mChina.geometry, mChina.crs, drop=False, invert=True)
        DS_agg   = xr.open_dataset(agg_path)
        allwst   = DS_agg['waste'].values
        alldoshp = DS_agg['shipping'].values
        all_avi  = DS_agg['aviation'].values
        doagr    = DS_agg['agriculture'].values
        doagr_clip = np.nan_to_num(
            agg_clipped['agriculture'].values, nan=0)
        dms_agr  = doagr - doagr_clip[0][::-1]
    else:
        raise ValueError(
            "[CINEI] Either 'htap_dir' or 'agg_dir' must be provided.\n"
            "        Recommended: provide htap_dir for automatic regridding."
        )

    # ── Read MEIC sector files ────────────────────────────────────────
    if spec_meic == 'PMcoarse':
        spec_meic = 'PM10'
    pattern = f'*_{mon}_*_{spec_meic}.*'

    fn_act = os.path.join(meic_dir, fnmatch.filter(
        fnmatch.filter(os.listdir(meic_dir), pattern), '*agr*nc')[0])
    fn_idt = os.path.join(meic_dir, fnmatch.filter(
        fnmatch.filter(os.listdir(meic_dir), pattern), '*ind*nc')[0])
    fn_pwr = os.path.join(meic_dir, fnmatch.filter(
        fnmatch.filter(os.listdir(meic_dir), pattern), '*pow*nc')[0])
    fn_rdt = os.path.join(meic_dir, fnmatch.filter(
        fnmatch.filter(os.listdir(meic_dir), pattern), '*res*nc')[0])
    fn_tpt = os.path.join(meic_dir, fnmatch.filter(
        fnmatch.filter(os.listdir(meic_dir), pattern), '*tra*nc')[0])

    n_lat = len(lat_arange)
    n_lon = len(lon_arange)

    act = xr.open_dataset(fn_act)['z'][:].values.reshape((n_lat, n_lon))[::-1]
    idt = xr.open_dataset(fn_idt)['z'][:].values.reshape((n_lat, n_lon))[::-1]
    pwr = xr.open_dataset(fn_pwr)['z'][:].values.reshape((n_lat, n_lon))[::-1]
    rdt = xr.open_dataset(fn_rdt)['z'][:].values.reshape((n_lat, n_lon))[::-1]
    tpt = xr.open_dataset(fn_tpt)['z'][:].values.reshape((n_lat, n_lon))[::-1]

    act = np.where(act > 0.0, act, 0.0)
    idt = np.where(idt > 0.0, idt, 0.0)
    pwr = np.where(pwr > 0.0, pwr, 0.0)
    rdt = np.where(rdt > 0.0, rdt, 0.0)
    tpt = np.where(tpt > 0.0, tpt, 0.0)

    # ── Merge sectors ─────────────────────────────────────────────────
    # global_bg_clipped = global background (CEDS), clipped outside China
    # MEIC regional values fill inside China
    pwr_union = np.nan_to_num(global_bg_clipped['energy'],         nan=0) + pwr
    res_union = (np.nan_to_num(global_bg_clipped['residential'],   nan=0) +
                 np.nan_to_num(global_bg_clipped['solvents'],      nan=0) + rdt)
    idt_union = np.nan_to_num(global_bg_clipped['industrial'],     nan=0) + idt
    shp_union = np.nan_to_num(global_bg_clipped['ships'],          nan=0) + alldoshp
    tpt_union = np.nan_to_num(global_bg_clipped['transportation'], nan=0) + tpt
    act_union = np.nan_to_num(global_bg_clipped['agriculture'],    nan=0) + dms_agr
    swd_union = allwst
    avi_union = all_avi
    sum_union = (pwr_union + res_union + idt_union + shp_union +
                 swd_union + tpt_union + act_union)

    # ── Build output xarray Dataset ───────────────────────────────────
    myds = xr.Dataset(
        {"energy":         (("lat", "lon"), pwr_union),
         "residential":    (("lat", "lon"), res_union),
         "industry":       (("lat", "lon"), idt_union),
         "agriculture":    (("lat", "lon"), act_union),
         "transportation": (("lat", "lon"), tpt_union),
         "waste":          (("lat", "lon"), swd_union),
         "shipping":       (("lat", "lon"), shp_union),
         "aviation":       (("lat", "lon"), avi_union),
         "sum":            (("lat", "lon"), sum_union)},
        coords={'lon': lon_arange, 'lat': lat_arange})

    domain_str = "global" if global_domain else (
        f"{_lon_min}-{_lon_max}E_{_lat_min}-{_lat_max}N")

    myds.attrs['unit'] = ('million mole/month/grid'
                          if V == 'Y' else 'ton/month/grid')
    myds.attrs['conventions']  = 'NETCDF3_CLASSIC'
    myds.attrs['resolution']   = f'{output_res}° x {output_res}°'
    myds.attrs['domain']       = domain_str
    myds.attrs['comments'] = (
        'Integrated inventories: global background (CEDS) + regional '
        '(MEIC for China) with uniform VOC speciation (MOZART mechanism).')
    myds.attrs['projection'] = (
        f'Latitude-Longitude gridded data at '
        f'{output_res} x {output_res} decimal degrees.')
    myds.attrs['authors'] = 'Yijuan Zhang, University of Bremen.'
    myds.attrs['title']   = (
        f'Integrated anthropogenic emission inventory '
        f'({domain_str}) in {year}')

    # ── Write output ──────────────────────────────────────────────────
    output_spec = mapper.loc[spec_meic, 'output species']
    res_str     = str(output_res).replace('.', 'p')
    output = os.path.join(
        save_dir,
        f'Integrated_Anthropogenic_{year}_{mon}_{output_spec}'
        f'_{res_str}deg_{domain_str}.nc')
    myds.to_netcdf(output, format="NETCDF3_CLASSIC")
    print(f"[CINEI] ✅ Output saved: {output}")
    return output


def _check_path(path, name):
    """Raise a clear error if a required path does not exist."""
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"[CINEI] Required path not found: '{path}'\n"
            f"  Parameter: {name}\n"
            f"  Please provide a valid path when calling emis_union().")
