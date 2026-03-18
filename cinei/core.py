"""Core functionality for CINEI emission integration."""
from __future__ import annotations
from typing import List, Literal, Union

import pandas as pd
import rioxarray
import xarray as xr
import numpy as np
import geopandas as gpd
import fnmatch
import os
from pathlib import Path
from .utils import ll_area, get_mapper_path, get_country_shp, get_province_shp
from .regridding import regrid_aggregation, SUPPORTED_RESOLUTIONS
from .preprocess import check_user_data, standardize_netcdf
from .regions import get_region_bbox, check_data_coverage, list_regions
from .voc_speciation import nmvoc_speciation as _nmvoc_speciation


# ── Supported sectors ────────────────────────────────────────────────────────
SECTORS = Literal[
    "energy",
    "residential",
    "industry",
    "agriculture",
    "transportation",
    "waste",
    "shipping",
    "aviation",
]

ALL_SECTORS = [
    "energy",
    "residential",
    "industry",
    "agriculture",
    "transportation",
    "waste",
    "shipping",
    "aviation",
]

# ── Supported inventory sources ───────────────────────────────────────────────
SUPPORTED_OUTER = ['CEDS', 'EDGAR', 'HTAP', 'user']
SUPPORTED_INNER = ['MEIC', 'user', 'EDGAR', 'HTAP']

# ── Month lookup ──────────────────────────────────────────────────────────────
_MONTH_NAME = {
    1: "Jan", 2: "Feb",  3: "Mar",  4: "Apr",
    5: "May", 6: "Jun",  7: "Jul",  8: "Aug",
    9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec",
}
_MONTH_STR = {m: f"{m:02d}" for m in range(1, 13)}

# Reverse mapping: any string format → integer month
_MONTH_TO_INT = {
    # Zero-padded strings
    "01": 1,  "02": 2,  "03": 3,  "04": 4,
    "05": 5,  "06": 6,  "07": 7,  "08": 8,
    "09": 9,  "10": 10, "11": 11, "12": 12,
    # Plain integers as strings
    "1": 1,  "2": 2,  "3": 3,  "4": 4,
    "5": 5,  "6": 6,  "7": 7,  "8": 8,
    "9": 9,
    # Month name abbreviations
    "jan": 1,  "feb": 2,  "mar": 3,  "apr": 4,
    "may": 5,  "jun": 6,  "jul": 7,  "aug": 8,
    "sep": 9,  "oct": 10, "nov": 11, "dec": 12,
    # Full month names
    "january": 1,  "february": 2,  "march": 3,    "april": 4,
    "may": 5,      "june": 6,      "july": 7,      "august": 8,
    "september": 9,"october": 10,  "november": 11, "december": 12,
}


def _parse_month(month):
    """
    Parse any month input to integer 1-12.

    Accepts:
    - int       : 1, 2, ... 12
    - str zero-padded : '01', '02', ... '12'
    - str plain : '1', '2', ... '12'
    - str name  : 'Jan', 'January', 'jan', 'JAN'

    Returns
    -------
    int : month as 1-12
    """
    if isinstance(month, int):
        if month not in range(1, 13):
            raise ValueError(
                f"[CINEI] Invalid month: {month}. Must be 1-12."
            )
        return month

    if isinstance(month, str):
        key = month.strip().lower()
        if key in _MONTH_TO_INT:
            return _MONTH_TO_INT[key]

    raise ValueError(
        f"[CINEI] Cannot parse month: '{month}'\n"
        f"        Accepted formats:\n"
        f"          Integer   : 1, 2, ... 12\n"
        f"          Zero-padded: '01', '02', ... '12'\n"
        f"          Abbreviated: 'Jan', 'Feb', ... 'Dec'\n"
        f"          Full name  : 'January', 'February', ..."
    )

# ── CEDS file pattern ─────────────────────────────────────────────────────────
# {outer_dir}/CEDS_Glb_0.5x0.5_anthro_{ceds_spec}__monthly_{year}.nc
_CEDS_PATTERN = "CEDS_Glb_0.5x0.5_anthro_{spec}__monthly_{year}.nc"
_CEDS_BC_FILE = "CEDS_Glb_0.5x0.5_anthro_BC__monthly_2016.nc"


def emis_union(species, month, year,
               outer_dir, inner_dir, save_dir,
               outer_source='CEDS',
               inner_source='MEIC',
               agg_dir=None,
               nmvoc_speciation=False,
               mapper_path=None,
               country_shp=None,
               province_shp=None,
               output_res=0.25,
               sectors: Union[List[Literal["energy","residential","industry",
                   "agriculture","transportation","waste","shipping","aviation"]],
                   str] = "all",
               region=None,
               global_domain=False,
               lon_min=None, lon_max=None,
               lat_min=None, lat_max=None):
    """
    Integrate emissions from outer (global background) and inner
    (regional) inventories onto a unified output grid.

    Parameters
    ----------
    species : str
        Species name. Case-insensitive. Auto-mapped via mapper.
        e.g. 'SO2', 'NOx', 'CO', 'BC', 'PM2.5'
    month : int
        Month as integer 1-12. Auto-converts to all required formats.
    year : str or int
        Target year (e.g. 2017).
    outer_dir : str
        Directory for outer (global background) inventory files.
    inner_dir : str
        Directory for inner (regional) inventory files.
    save_dir : str
        Directory to save output NetCDF files.
    outer_source : str, optional
        Outer inventory type. Options: 'CEDS', 'EDGAR', 'HTAP', 'user'.
        Default: 'CEDS'.
        - 'CEDS'  : CEDS v_2021_04_21 format
        - 'EDGAR' : EDGAR v8.1 format
        - 'HTAP'  : HTAP v3 format
        - 'user'  : user-provided data (auto-checked and standardized)
    inner_source : str, optional
        Inner inventory type. Options: 'MEIC', 'user', 'EDGAR', 'HTAP'.
        Default: 'MEIC'.
    agg_dir : str, optional
        Directory for aggregated sector files (HTAP for waste/shipping/aviation).
        If None, these sectors are set to zero with a warning.
    mapper_path : str, optional
        Path to Integrated_mapper.csv.
        Default: bundled cinei/data/Integrated_mapper.csv.
    country_shp : str, optional
        Path to country shapefile.
        Default: bundled cinei/data/country.shp.
    province_shp : str, optional
        Path to province shapefile.
        Default: bundled cinei/data/分省.shp.
    output_res : float, optional
        Output resolution in degrees. Options: 0.05, 0.1, 0.25, 0.5.
        Default: 0.25.
    region : str, optional
        Region name for automatic bbox lookup.
        e.g. 'China', 'Beijing', 'NCP', 'Germany', 'India'.
        Call cinei.list_regions() to see all presets.
    global_domain : bool, optional
        If True, use global extent. Default False.
    lon_min, lon_max, lat_min, lat_max : float, optional
        Manual bounding box. Used when region is None and
        global_domain is False.
        Default: China domain (70-150E, 10-60N).

    Returns
    -------
    str
        Path to the output integrated NetCDF file.

    Examples
    --------
    >>> import cinei

    >>> # Minimal — China, CEDS outer, MEIC inner, 0.25°
    >>> cinei.emis_union(
    ...     species='SO2', month=1, year=2017,
    ...     outer_dir='/data/CEDS',
    ...     inner_dir='/data/MEIC/2017',
    ...     save_dir='/data/output',
    ...     agg_dir='/data/HTAP',
    ... )

    >>> # EDGAR as outer inventory
    >>> cinei.emis_union(
    ...     species='NOx', month=7, year=2017,
    ...     outer_source='EDGAR',
    ...     outer_dir='/data/EDGAR',
    ...     inner_dir='/data/MEIC/2017',
    ...     save_dir='/data/output',
    ... )

    >>> # User-provided outer data (auto-checked/standardized)
    >>> cinei.emis_union(
    ...     species='SO2', month=1, year=2017,
    ...     outer_source='user',
    ...     outer_dir='/data/my_inventory',
    ...     inner_dir='/data/MEIC/2017',
    ...     save_dir='/data/output',
    ... )

    >>> # Region by name
    >>> cinei.emis_union(
    ...     species='SO2', month=1, year=2017,
    ...     outer_dir='/data/CEDS',
    ...     inner_dir='/data/MEIC/2017',
    ...     save_dir='/data/output',
    ...     region='Beijing',
    ... )

    >>> # Custom resolution
    >>> cinei.emis_union(
    ...     species='CO', month=3, year=2017,
    ...     outer_dir='/data/CEDS',
    ...     inner_dir='/data/MEIC/2017',
    ...     save_dir='/data/output',
    ...     output_res=0.1,
    ...     region='NCP',
    ... )
    """
    year = str(year)

    # ── Auto-resolve bundled data ─────────────────────────────────────
    if mapper_path  is None: mapper_path  = get_mapper_path()
    if country_shp  is None: country_shp  = get_country_shp()
    if province_shp is None: province_shp = get_province_shp()

    # ── Validate sources ──────────────────────────────────────────────
    if outer_source not in SUPPORTED_OUTER:
        raise ValueError(
            f"[CINEI] Invalid outer_source: '{outer_source}'\n"
            f"        Available: {SUPPORTED_OUTER}"
        )
    if inner_source not in SUPPORTED_INNER:
        raise ValueError(
            f"[CINEI] Invalid inner_source: '{inner_source}'\n"
            f"        Available: {SUPPORTED_INNER}"
        )

    # ── Validate resolution ───────────────────────────────────────────
    if output_res not in SUPPORTED_RESOLUTIONS:
        raise ValueError(
            f"[CINEI] Invalid output_res: {output_res}\n"
            f"        Available: {SUPPORTED_RESOLUTIONS}"
        )

    # ── Auto-convert month (accepts int, '01', 'Jan', 'January') ────────
    month    = _parse_month(month)
    mon_name = _MONTH_NAME[month]   # e.g. 'Jan'
    mon_id   = month - 1            # 0-based xarray index
    mon_str  = _MONTH_STR[month]    # e.g. '01'
    print(f"[CINEI] Month      : {mon_str} ({mon_name})")

    # ── Validate and resolve sectors ─────────────────────────────────
    if sectors == "all":
        active_sectors = ALL_SECTORS.copy()
    else:
        invalid = [s for s in sectors if s not in ALL_SECTORS]
        if invalid:
            raise ValueError(
                f"[CINEI] Invalid sectors: {invalid}\n"
                f"        Available: {ALL_SECTORS}"
            )
        active_sectors = list(sectors)
    print(f"[CINEI] Sectors    : {active_sectors}")

    # ── Resolve region of interest ────────────────────────────────────
    _lon_min, _lon_max, _lat_min, _lat_max, region_name = get_region_bbox(
        region       = region,
        country_shp  = country_shp,
        lon_min      = lon_min,
        lon_max      = lon_max,
        lat_min      = lat_min,
        lat_max      = lat_max,
        global_domain= global_domain,
    )

    print(f"[CINEI] ── emis_union ──────────────────────────────")
    print(f"[CINEI] Species    : {species}")
    print(f"[CINEI] Month      : {month:02d} ({mon_name})")
    print(f"[CINEI] Year       : {year}")
    print(f"[CINEI] Outer      : {outer_source}")
    print(f"[CINEI] Inner      : {inner_source}")
    print(f"[CINEI] Resolution : {output_res}°")
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

    # ── Read mapper ───────────────────────────────────────────────────
    mapper    = pd.read_csv(mapper_path)
    mapper    = mapper.set_index('MEIC')
    sp_upper  = species.upper()
    meic_keys = [k for k in mapper.index if k.upper() == sp_upper]
    if not meic_keys:
        raise ValueError(
            f"[CINEI] Species '{species}' not found in mapper.\n"
            f"        Available: {list(mapper.index)}"
        )
    meic_spec = meic_keys[0]
    ceds_spec = mapper.loc[meic_spec, 'CEDS']
    par       = mapper.loc[meic_spec, 'partition']
    M         = mapper.loc[meic_spec, 'weight']
    V         = mapper.loc[meic_spec, 'if VOC']

    # ── Build output grid ─────────────────────────────────────────────
    half       = output_res / 2
    lon_arange = np.arange(_lon_min + half, _lon_max, output_res,
                           dtype=np.float32)
    lat_arange = np.arange(_lat_min + half, _lat_max, output_res,
                           dtype=np.float32)
    lon_2d, lat_2d = np.meshgrid(lon_arange, lat_arange)
    area = ll_area(lat_2d, output_res)
    n_lat, n_lon = len(lat_arange), len(lon_arange)

    # ── Read outer (global background) inventory ──────────────────────
    outer_bg = _read_outer(
        outer_source = outer_source,
        outer_dir    = outer_dir,
        ceds_spec    = ceds_spec,
        meic_spec    = meic_spec,
        year         = year,
        mon_id       = mon_id,
        mon_str      = mon_str,
        lon_arange   = lon_arange,
        lat_arange   = lat_arange,
        output_res   = output_res,
        region_name  = region_name,
        _lon_min=_lon_min, _lon_max=_lon_max,
        _lat_min=_lat_min, _lat_max=_lat_max,
    )

    # ── Unit conversion ───────────────────────────────────────────────
    if V == 'Y':
        unit_outer = outer_bg * 0.001 * area * 2678400 * 1000000 * par / M
    else:
        unit_outer = outer_bg * 0.001 * area * 2678400 * 1000000 * par

    # ── Clip outer to outside region (China excl. Taiwan) ────────────
    country    = gpd.read_file(country_shp)
    China_shp  = country[country['CNTRY_NAME'] == 'China']
    province   = gpd.read_file(province_shp)
    Taiwan_shp = province[province['行政区划_c'] == '台湾省']
    mChina     = gpd.overlay(China_shp, Taiwan_shp, how='difference')
    unit_outer.rio.write_crs("epsg:4326", inplace=True)
    outer_clipped = unit_outer.rio.clip(
        mChina.geometry, mChina.crs, drop=False, invert=True)

    # ── Aggregated sectors (waste, shipping, aviation) ────────────────
    if agg_dir is not None:
        print(f"[CINEI] Regridding aggregated sectors...")
        ds_agg   = regrid_aggregation(
            mon_id=mon_id, meic_spec=meic_spec, year=year,
            ceds_dir=outer_dir, htap_dir=agg_dir,
            mapper_path=mapper_path, output_res=output_res,
            lon_min=_lon_min, lon_max=_lon_max,
            lat_min=_lat_min, lat_max=_lat_max,
        )
        allwst   = ds_agg['waste'].values
        alldoshp = ds_agg['shipping'].values
        all_avi  = ds_agg['aviation'].values
        doagr    = ds_agg['agriculture'].values
        # Agriculture: use HTAP full domain — no clipping
        # HTAP agriculture covers both inner and outer domain consistently
        dms_agr  = doagr
    else:
        print(f"[CINEI] ⚠️  agg_dir not provided → "
              f"waste/shipping/aviation set to zero.")
        zeros    = np.zeros((n_lat, n_lon), dtype='float32')
        allwst   = zeros; alldoshp = zeros
        all_avi  = zeros; dms_agr  = zeros

    # ── Read inner (regional) inventory ──────────────────────────────
    act, idt, pwr, rdt, tpt = _read_inner(
        inner_source = inner_source,
        inner_dir    = inner_dir,
        meic_spec    = meic_spec,
        mon_name     = mon_name,
        mon_str      = mon_str,
        month        = month,
        year         = year,
        n_lat        = n_lat,
        n_lon        = n_lon,
        lon_arange   = lon_arange,
        lat_arange   = lat_arange,
        mon_id       = mon_id,
    )

    # ── Merge sectors (only active) ──────────────────────────────────────
    pwr_union = (np.nan_to_num(outer_clipped['energy'],         nan=0) + pwr
               if 'energy'         in active_sectors
               else np.zeros((n_lat, n_lon), dtype='float32'))
    res_union = (np.nan_to_num(outer_clipped['residential'],   nan=0) +
                 np.nan_to_num(outer_clipped['solvents'],      nan=0) + rdt
               if 'residential'    in active_sectors
               else np.zeros((n_lat, n_lon), dtype='float32'))
    idt_union = (np.nan_to_num(outer_clipped['industrial'],     nan=0) + idt
               if 'industry'       in active_sectors
               else np.zeros((n_lat, n_lon), dtype='float32'))
    shp_union = (np.nan_to_num(outer_clipped['ships'],          nan=0) + alldoshp
               if 'shipping'       in active_sectors
               else np.zeros((n_lat, n_lon), dtype='float32'))
    tpt_union = (np.nan_to_num(outer_clipped['transportation'], nan=0) + tpt
               if 'transportation' in active_sectors
               else np.zeros((n_lat, n_lon), dtype='float32'))
    # Agriculture: use HTAP for entire domain (no clipping)
    # MEIC agriculture contains NaN inside China → unreliable
    # HTAP provides consistent coverage for both inner and outer domain
    act_union = (doagr
                 if 'agriculture' in active_sectors
                 else np.zeros((n_lat, n_lon), dtype='float32'))
    swd_union = allwst if 'waste'    in active_sectors else np.zeros((n_lat, n_lon), dtype='float32')
    avi_union = all_avi if 'aviation' in active_sectors else np.zeros((n_lat, n_lon), dtype='float32')
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

    myds.attrs['unit']        = 'million mole/month/grid' if V=='Y' else 'ton/month/grid'
    myds.attrs['resolution']  = f'{output_res}° x {output_res}°'
    myds.attrs['region']      = region_name
    myds.attrs['outer_source']= outer_source
    myds.attrs['inner_source']= inner_source
    myds.attrs['conventions'] = 'NETCDF3_CLASSIC'
    myds.attrs['authors']     = 'Yijuan Zhang, University of Bremen.'
    myds.attrs['title']       = (
        f'CINEI integrated emissions ({region_name}) '
        f'{meic_spec} {year}-{mon_str}')

    # ── Write output ──────────────────────────────────────────────────
    output_spec = mapper.loc[meic_spec, 'output species']
    res_str     = str(output_res).replace('.', 'p')
    output = os.path.join(
        save_dir,
        f'CINEI_{year}_{mon_name}_{output_spec}_'
        f'{res_str}deg_{region_name}.nc')
    myds.to_netcdf(output, format="NETCDF3_CLASSIC")
    print(f"[CINEI] ✅ Saved: {output}")

    # ── Auto-run VOC speciation if requested ──────────────────────────
    if nmvoc_speciation and meic_spec.upper() == 'NMVOC':
        print(f"\n[CINEI] Running NMVOC speciation...")
        _nmvoc_speciation(
            nmvoc_nc_path=output,
            save_dir=save_dir,
            sectors=active_sectors,
        )

    return output


# ── Inventory readers ─────────────────────────────────────────────────────────

def _read_outer(outer_source, outer_dir, ceds_spec, meic_spec,
                year, mon_id, mon_str, lon_arange, lat_arange,
                output_res, region_name,
                _lon_min, _lon_max, _lat_min, _lat_max):
    """Read outer (global background) inventory and return rioxarray."""

    if outer_source == 'CEDS':
        # CEDS file pattern
        fname = (_CEDS_BC_FILE if ceds_spec == 'BC'
                 else _CEDS_PATTERN.format(spec=ceds_spec, year=year))
        path  = os.path.join(outer_dir, fname)
        _check_path(path, f'CEDS file ({fname})')

        ds       = rioxarray.open_rasterio(path, masked=True)
        re_lat   = np.arange(ds.y.values.min(), ds.y.values.max(), output_res)
        re_lon   = np.arange(ds.x.values.min(), ds.x.values.max(), output_res)
        emis_all = ds.interp(y=re_lat, x=re_lon).isel(time=mon_id)

        # Check data covers region
        check_data_coverage(
            float(ds.x.min()), float(ds.x.max()),
            float(ds.y.min()), float(ds.y.max()),
            _lon_min, _lon_max, _lat_min, _lat_max,
            region_name
        )
        return emis_all.sel(x=lon_arange, y=lat_arange, method="nearest")

    elif outer_source == 'EDGAR':
        # EDGAR: one nc per year, dims (time, lat, lon)
        # Pattern: v8.1_FT2022_AP_{spec}_{year}_TOTALS_flx_nc.nc
        import glob
        pattern = os.path.join(outer_dir, f"*{ceds_spec}*{year}*TOTALS*.nc")
        files   = glob.glob(pattern)
        if not files:
            raise FileNotFoundError(
                f"[CINEI] No EDGAR file found for spec={ceds_spec} "
                f"year={year} in {outer_dir}\n"
                f"        Pattern: {pattern}"
            )
        ds  = xr.open_dataset(files[0])
        # Find lat/lon dims
        lat_dim = next(d for d in ds.dims if 'lat' in d.lower())
        lon_dim = next(d for d in ds.dims if 'lon' in d.lower())
        time_dim= next(d for d in ds.dims if d in ('time', 'month'))
        ds_mon  = ds.isel({time_dim: mon_id})
        check_data_coverage(
            float(ds[lon_dim].min()), float(ds[lon_dim].max()),
            float(ds[lat_dim].min()), float(ds[lat_dim].max()),
            _lon_min, _lon_max, _lat_min, _lat_max, region_name
        )
        # Return as rioxarray-compatible
        var = [v for v in ds_mon.data_vars][0]
        return ds_mon[var].sel(
            {lat_dim: lat_arange, lon_dim: lon_arange}, method='nearest')

    elif outer_source == 'HTAP':
        # HTAP: edgar_HTAPv3_{year}_{spec}.nc
        path = os.path.join(
            outer_dir, f"edgar_HTAPv3_{year}_{meic_spec}.nc")
        _check_path(path, 'HTAP outer file')
        ds   = xr.open_dataset(path)
        # Sum all sector variables for background
        time_dim = next(d for d in ds.dims if d in ('time', 'month'))
        ds_mon   = ds.isel({time_dim: mon_id})
        total    = sum(ds_mon[v] for v in ds_mon.data_vars)
        return total.sel(lat=lat_arange, lon=lon_arange, method='nearest')

    elif outer_source == 'user':
        # User-provided: auto-check and standardize
        print(f"[CINEI] Checking user-provided outer data...")
        nc_files = list(Path(outer_dir).glob("*.nc"))
        if not nc_files:
            raise FileNotFoundError(
                f"[CINEI] No NetCDF files found in outer_dir: {outer_dir}"
            )
        # Check each file, standardize if needed
        standardized = []
        for f in nc_files:
            report = check_user_data(str(f))
            if report['status'] != 'ok':
                print(f"[CINEI] Auto-standardizing: {f.name}")
                std_path = standardize_netcdf(str(f))
                standardized.append(std_path)
            else:
                standardized.append(str(f))

        # Load and select month
        ds     = xr.open_dataset(standardized[0])
        ds_mon = ds.isel(month=mon_id)
        # Check coverage
        check_data_coverage(
            float(ds.lon.min()), float(ds.lon.max()),
            float(ds.lat.min()), float(ds.lat.max()),
            _lon_min, _lon_max, _lat_min, _lat_max, region_name
        )
        var = 'sum' if 'sum' in ds_mon else list(ds_mon.data_vars)[0]
        return ds_mon[var].sel(
            lat=lat_arange, lon=lon_arange, method='nearest')

    else:
        raise ValueError(f"[CINEI] Unknown outer_source: {outer_source}")


def _read_inner(inner_source, inner_dir, meic_spec, mon_name,
                mon_str, month, year,
                n_lat, n_lon, lon_arange, lat_arange, mon_id):
    """Read inner (regional) inventory sectors."""

    zeros = np.zeros((n_lat, n_lon), dtype='float32')

    if inner_source == 'MEIC':
        inner_spec     = 'PM10' if meic_spec == 'PMcoarse' else meic_spec
        meic_file_spec = 'VOC' if inner_spec.upper() == 'NMVOC' else inner_spec
        files_in_dir   = os.listdir(inner_dir)

        # Support multiple filename formats:
        # Format A: 2017_01_agriculture_VOC.nc  (zero-padded month)
        # Format B: 2017_1_agriculture_VOC.nc   (plain integer month)
        # Format C: agr_Jan_2017_VOC.nc         (month name)
        pattern_a = f'{year}_{mon_str}_*_{meic_file_spec}.nc'
        pattern_b = f'{year}_{month}_*_{meic_file_spec}.nc'
        pattern_c = f'*_{mon_name}_*_{meic_file_spec}.*'

        if fnmatch.filter(files_in_dir, pattern_a):
            pattern = pattern_a
        elif fnmatch.filter(files_in_dir, pattern_b):
            pattern = pattern_b
        else:
            pattern = pattern_c

        def _load(sector_pattern):
            matches = fnmatch.filter(
                fnmatch.filter(files_in_dir, pattern),
                sector_pattern)
            if not matches:
                print(f"[CINEI] ⚠️  MEIC sector not found: {sector_pattern}"
                      f" → set to zero")
                return zeros.copy()
            fn  = os.path.join(inner_dir, matches[0])
            arr = xr.open_dataset(fn)['z'][:].values
            arr = arr.reshape((n_lat, n_lon))[::-1]
            return np.where(arr > 0.0, arr, 0.0)

        act = _load('*agr*nc')
        idt = _load('*ind*nc')
        pwr = _load('*pow*nc')
        rdt = _load('*res*nc')
        tpt = _load('*tra*nc')
        return act, idt, pwr, rdt, tpt

    elif inner_source == 'user':
        print(f"[CINEI] Checking user-provided inner data...")
        nc_files = list(Path(inner_dir).glob("*.nc"))
        if not nc_files:
            raise FileNotFoundError(
                f"[CINEI] No NetCDF files found in inner_dir: {inner_dir}"
            )
        standardized = []
        for f in nc_files:
            report = check_user_data(str(f))
            if report['status'] != 'ok':
                print(f"[CINEI] Auto-standardizing: {f.name}")
                std_path = standardize_netcdf(str(f))
                standardized.append(std_path)
            else:
                standardized.append(str(f))

        ds     = xr.open_dataset(standardized[0])
        ds_mon = ds.isel(month=mon_id)

        def _get(sector):
            if sector in ds_mon:
                return ds_mon[sector].sel(
                    lat=lat_arange, lon=lon_arange,
                    method='nearest').values
            print(f"[CINEI] ⚠️  Sector '{sector}' not found → zero")
            return zeros.copy()

        return (_get('agriculture'), _get('industry'),
                _get('power'),       _get('residential'),
                _get('transportation'))

    elif inner_source in ('EDGAR', 'HTAP'):
        # For EDGAR/HTAP as inner, load from standardized NetCDF
        import glob
        files = glob.glob(os.path.join(inner_dir, "*.nc"))
        if not files:
            raise FileNotFoundError(
                f"[CINEI] No NetCDF in inner_dir: {inner_dir}")
        ds     = xr.open_dataset(files[0])
        ds_mon = ds.isel(month=mon_id) if 'month' in ds.dims else ds

        def _get(sector):
            if sector in ds_mon:
                return ds_mon[sector].sel(
                    lat=lat_arange, lon=lon_arange,
                    method='nearest').values
            return zeros.copy()

        return (_get('agriculture'), _get('industry'),
                _get('power'),       _get('residential'),
                _get('transportation'))

    else:
        raise ValueError(f"[CINEI] Unknown inner_source: {inner_source}")


def _check_path(path, name):
    """Raise a clear error if a required path does not exist."""
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"[CINEI] Required path not found: '{path}'\n"
            f"  Parameter : {name}")
