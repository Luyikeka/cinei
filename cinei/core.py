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
from .regridding import regrid_aggregation, SUPPORTED_RESOLUTIONS
from .utils import get_mapper_path, get_country_shp, get_province_shp
from .utils import get_mapper_path, get_country_shp, get_province_shp


# ── Month lookup tables ───────────────────────────────────────────────────────
_MONTH_NAME = {
    1: "Jan", 2: "Feb",  3: "Mar",  4: "Apr",
    5: "May", 6: "Jun",  7: "Jul",  8: "Aug",
    9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec",
}
_MONTH_STR = {m: f"{m:02d}" for m in range(1, 13)}


def emis_union(species, month, year,
               outer_dir, inner_dir, save_dir,
               mapper_path=None, country_shp=None, province_shp=None,
               agg_dir=None,
               output_res=0.25,
               global_domain=False,
               lon_min=70.0, lon_max=150.0,
               lat_min=10.0, lat_max=60.0):
    """
    Integrate emissions from outer (global background) and inner
    (regional) inventories onto a unified output grid.

    Parameters
    ----------
    species : str
        Species name. Case-insensitive. Auto-mapped to outer/inner
        inventory naming via mapper_path.
        e.g. 'SO2', 'NOx', 'CO', 'BC', 'PM2.5'
    month : int
        Month as integer 1-12 (e.g. 1 for January).
        Auto-converts to month name, index, and string internally.
    year : str or int
        Target year (e.g. '2017' or 2017).
    outer_dir : str
        Directory for outer (global background) inventory NetCDF files.
        Currently supports CEDS format.
        Pattern: CEDS_Glb_0.5x0.5_anthro_{spec}__monthly_{year}.nc
    inner_dir : str
        Directory for inner (regional) inventory NetCDF files.
        Currently supports MEIC format.
        Pattern: {year}_{month:02d}_{sector}_{spec}.nc
    save_dir : str
        Directory to save integrated output NetCDF files.
    mapper_path : str
        Path to Integrated_mapper.csv.
        Maps species names across inventories and provides unit conversion.
    country_shp : str
        Path to world country shapefile (must have 'CNTRY_NAME' column).
    province_shp : str
        Path to China province shapefile (must have '行政区划_c' column).
    agg_dir : str, optional
        Directory containing HTAP NetCDF files for automatic regridding
        of aggregated sectors (waste, shipping, aviation).
        Pattern: edgar_HTAPv3_{year}_{spec}.nc
        If None, aggregated sectors are set to zero (with warning).
    output_res : float, optional
        Output grid resolution in degrees.
        Options: 0.05, 0.1, 0.25, 0.5. Default: 0.25.
    global_domain : bool, optional
        If True, use global extent (-180 to 180, -90 to 90).
        If False, use regional extent defined by lon/lat min/max.
        Default: False.
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

    >>> # Minimal call — China domain, 0.25°
    >>> output = cinei.emis_union(
    ...     species='SO2',
    ...     month=1,
    ...     year='2017',
    ...     outer_dir='/work/bb1554/data/CEDS',
    ...     inner_dir='/work/bb1554/data/MEIC/2017',
    ...     save_dir='/work/bb1554/output/cinei',
    ...     mapper_path='/work/bb1554/data/Integrated_mapper.csv',
    ...     country_shp='/work/bb1554/data/shapefiles/country.shp',
    ...     province_shp='/work/bb1554/data/shapefiles/province.shp',
    ...     agg_dir='/work/bb1554/data/HTAP',
    ... )

    >>> # Custom region at 0.1°
    >>> output = cinei.emis_union(
    ...     species='NOx', month=7, year='2017',
    ...     outer_dir=..., inner_dir=..., save_dir=...,
    ...     mapper_path=..., country_shp=..., province_shp=...,
    ...     agg_dir=...,
    ...     output_res=0.1,
    ...     global_domain=False,
    ...     lon_min=100.0, lon_max=130.0,
    ...     lat_min=20.0,  lat_max=45.0,
    ... )

    >>> # Global domain at 0.5°
    >>> output = cinei.emis_union(
    ...     species='CO', month=3, year='2017',
    ...     outer_dir=..., inner_dir=..., save_dir=...,
    ...     mapper_path=..., country_shp=..., province_shp=...,
    ...     output_res=0.5,
    ...     global_domain=True,
    ... )
    """
    year = str(year)

    # ── Auto-resolve bundled data files ──────────────────────────────
    if mapper_path is None:
        mapper_path = get_mapper_path()
        print(f"[CINEI] mapper_path : using bundled default")
    if country_shp is None:
        country_shp = get_country_shp()
        print(f"[CINEI] country_shp : using bundled default")
    if province_shp is None:
        province_shp = get_province_shp()
        print(f"[CINEI] province_shp: using bundled default")

    # ── Auto-convert month ────────────────────────────────────────────
    if month not in range(1, 13):
        raise ValueError(
            f"[CINEI] Invalid month: {month}. Must be integer 1-12."
        )
    mon_name = _MONTH_NAME[month]   # e.g. 'Jan'
    mon_id   = month - 1            # 0-based index for xarray isel
    mon_str  = _MONTH_STR[month]    # e.g. '01'

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
        domain_str = "global"
    else:
        _lon_min, _lon_max = lon_min, lon_max
        _lat_min, _lat_max = lat_min, lat_max
        domain_str = f"{_lon_min}-{_lon_max}E_{_lat_min}-{_lat_max}N"

    print(f"[CINEI] ── emis_union ──────────────────────────────")
    print(f"[CINEI] Species    : {species}")
    print(f"[CINEI] Month      : {month:02d} ({mon_name})")
    print(f"[CINEI] Year       : {year}")
    print(f"[CINEI] Resolution : {output_res}°")
    print(f"[CINEI] Domain     : {domain_str}")
    print()

    # ── Validate paths ────────────────────────────────────────────────
    for path, name in [
        (outer_dir,    'outer_dir'),
        (inner_dir,    'inner_dir'),
        (mapper_path,  'mapper_path'),
        (country_shp,  'country_shp'),
        (province_shp, 'province_shp'),
    ]:
        _check_path(path, name)
    if agg_dir:
        _check_path(agg_dir, 'agg_dir')
    os.makedirs(save_dir, exist_ok=True)

    # ── Read mapper → auto-resolve species names ──────────────────────
    mapper    = pd.read_csv(mapper_path)
    mapper    = mapper.set_index('MEIC')
    # Normalize species input
    sp_upper  = species.upper()
    # Find matching MEIC key (case-insensitive)
    meic_keys = [k for k in mapper.index if k.upper() == sp_upper]
    if not meic_keys:
        raise ValueError(
            f"[CINEI] Species '{species}' not found in mapper.\n"
            f"        Available: {list(mapper.index)}"
        )
    meic_spec = meic_keys[0]                        # e.g. 'SO2'
    ceds_spec = mapper.loc[meic_spec, 'CEDS']       # e.g. 'SO2'
    par       = mapper.loc[meic_spec, 'partition']
    M         = mapper.loc[meic_spec, 'weight']
    V         = mapper.loc[meic_spec, 'if VOC']

    print(f"[CINEI] Mapper     : {meic_spec} → CEDS:{ceds_spec}  "
          f"VOC:{V}  partition:{par}  weight:{M}")

    # ── Build output coordinate arrays ────────────────────────────────
    half       = output_res / 2
    lon_arange = np.arange(_lon_min + half, _lon_max, output_res,
                           dtype=np.float32)
    lat_arange = np.arange(_lat_min + half, _lat_max, output_res,
                           dtype=np.float32)

    # ── Read outer (global background) inventory ──────────────────────
    outer_path = os.path.join(
        outer_dir,
        f'CEDS_Glb_0.5x0.5_anthro_{ceds_spec}__monthly_{year}.nc')
    if ceds_spec == 'BC':
        outer_path = os.path.join(
            outer_dir, 'CEDS_Glb_0.5x0.5_anthro_BC__monthly_2016.nc')
    _check_path(outer_path, 'outer inventory file (CEDS)')

    ds       = rioxarray.open_rasterio(outer_path, masked=True)
    re_lat   = np.arange(ds.y.values.min(), ds.y.values.max(), output_res)
    re_lon   = np.arange(ds.x.values.min(), ds.x.values.max(), output_res)
    emis_all = ds.interp(y=re_lat, x=re_lon).isel(time=mon_id)
    outer_bg = emis_all.sel(x=lon_arange, y=lat_arange, method="nearest")

    # ── Grid cell area and unit conversion ────────────────────────────
    lon_2d, lat_2d = np.meshgrid(lon_arange, lat_arange)
    area = ll_area(lat_2d, output_res)
    if V == 'Y':
        unit_outer = outer_bg * 0.001 * area * 2678400 * 1000000 * par / M
    else:
        unit_outer = outer_bg * 0.001 * area * 2678400 * 1000000 * par

    # ── Clip outer background to region (exclude China / Taiwan) ─────
    country    = gpd.read_file(country_shp)
    China_shp  = country[country['CNTRY_NAME'] == 'China']
    province   = gpd.read_file(province_shp)
    Taiwan_shp = province[province['行政区划_c'] == '台湾省']
    mChina     = gpd.overlay(China_shp, Taiwan_shp, how='difference')
    unit_outer.rio.write_crs("epsg:4326", inplace=True)
    outer_clipped = unit_outer.rio.clip(
        mChina.geometry, mChina.crs, drop=False, invert=True)

    # ── Get aggregated sectors (waste, shipping, aviation) ────────────
    n_lat = len(lat_arange)
    n_lon = len(lon_arange)

    if agg_dir is not None:
        print(f"[CINEI] Regridding aggregated sectors...")
        ds_agg = regrid_aggregation(
            mon_id      = mon_id,
            meic_spec   = meic_spec,
            year        = year,
            ceds_dir    = outer_dir,
            htap_dir    = agg_dir,
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
        ds_agg.rio.write_crs("epsg:4326", inplace=True)
        agg_clipped = ds_agg.rio.clip(
            mChina.geometry, mChina.crs, drop=False, invert=True)
        doagr_clip = np.nan_to_num(agg_clipped['agriculture'].values, nan=0)
        dms_agr    = doagr - doagr_clip[::-1]
    else:
        print(f"[CINEI] ⚠️  agg_dir not provided → "
              f"waste/shipping/aviation set to zero.")
        zeros    = np.zeros((n_lat, n_lon), dtype='float32')
        allwst   = zeros
        alldoshp = zeros
        all_avi  = zeros
        dms_agr  = zeros

    # ── Read inner (regional) inventory files ─────────────────────────
    inner_spec = 'PM10' if meic_spec == 'PMcoarse' else meic_spec
    pattern    = f'*_{mon_name}_*_{inner_spec}.*'

    fn_act = os.path.join(inner_dir, fnmatch.filter(
        fnmatch.filter(os.listdir(inner_dir), pattern), '*agr*nc')[0])
    fn_idt = os.path.join(inner_dir, fnmatch.filter(
        fnmatch.filter(os.listdir(inner_dir), pattern), '*ind*nc')[0])
    fn_pwr = os.path.join(inner_dir, fnmatch.filter(
        fnmatch.filter(os.listdir(inner_dir), pattern), '*pow*nc')[0])
    fn_rdt = os.path.join(inner_dir, fnmatch.filter(
        fnmatch.filter(os.listdir(inner_dir), pattern), '*res*nc')[0])
    fn_tpt = os.path.join(inner_dir, fnmatch.filter(
        fnmatch.filter(os.listdir(inner_dir), pattern), '*tra*nc')[0])

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

    # ── Merge: outer background (clipped) + inner regional ───────────
    pwr_union = np.nan_to_num(outer_clipped['energy'],         nan=0) + pwr
    res_union = (np.nan_to_num(outer_clipped['residential'],   nan=0) +
                 np.nan_to_num(outer_clipped['solvents'],      nan=0) + rdt)
    idt_union = np.nan_to_num(outer_clipped['industrial'],     nan=0) + idt
    shp_union = np.nan_to_num(outer_clipped['ships'],          nan=0) + alldoshp
    tpt_union = np.nan_to_num(outer_clipped['transportation'], nan=0) + tpt
    act_union = np.nan_to_num(outer_clipped['agriculture'],    nan=0) + dms_agr
    swd_union = allwst
    avi_union = all_avi
    sum_union = (pwr_union + res_union + idt_union + shp_union +
                 swd_union + tpt_union + act_union)

    # ── Build output Dataset ──────────────────────────────────────────
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

    myds.attrs['unit']       = ('million mole/month/grid'
                                if V == 'Y' else 'ton/month/grid')
    myds.attrs['resolution'] = f'{output_res}° x {output_res}°'
    myds.attrs['domain']     = domain_str
    myds.attrs['conventions']= 'NETCDF3_CLASSIC'
    myds.attrs['comments']   = (
        'Integrated inventories: outer global background (CEDS) + '
        'inner regional (MEIC) with uniform VOC speciation (MOZART).')
    myds.attrs['authors']    = 'Yijuan Zhang, University of Bremen.'
    myds.attrs['title']      = (
        f'Integrated anthropogenic emissions ({domain_str}) '
        f'{meic_spec} {year}-{mon_str}')

    # ── Write output ──────────────────────────────────────────────────
    output_spec = mapper.loc[meic_spec, 'output species']
    res_str     = str(output_res).replace('.', 'p')
    output = os.path.join(
        save_dir,
        f'Integrated_Anthropogenic_{year}_{mon_name}_'
        f'{output_spec}_{res_str}deg_{domain_str}.nc')
    myds.to_netcdf(output, format="NETCDF3_CLASSIC")
    print(f"[CINEI] ✅ Output saved: {output}")
    return output


def _check_path(path, name):
    """Raise a clear error if a required path does not exist."""
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"[CINEI] Required path not found: '{path}'\n"
            f"  Parameter : {name}\n"
            f"  Please provide a valid path when calling emis_union().")
