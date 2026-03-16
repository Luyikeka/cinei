"""
VOC speciation utilities for CINEI.

Disaggregates total NMVOC emissions into lumped model species
(e.g. MOZART/SAPRC99) using sector-specific speciation profiles.

Bundled data files used (cinei/data/):
- all_species_fraction.csv       : VOC species fractions by sector
- mapping species to lumps.csv   : mapping to model lumped species
"""

import numpy as np
import xarray as xr
import pandas as pd
from pathlib import Path
from .utils import get_data_path


# ── Sector → column index range in all_species_fraction.csv ──────────────────
SECTOR_SAMPLE_RANGE = {
    "transportation": (0,  22),
    "aviation":       (0,  22),
    "shipping":       (0,  22),
    "energy":         (23, 24),
    "agriculture":    (25, 28),
    "waste":          (25, 28),
    "residential":    (29, 85),
    "industry":       (29, 85),
}


def nmvoc_speciation(nmvoc_nc_path, save_dir,
                     species_fraction_csv=None,
                     mapping_csv=None,
                     sectors=None):
    """
    Disaggregate total NMVOC emissions into lumped model species.

    Parameters
    ----------
    nmvoc_nc_path : str
        Path to integrated NMVOC NetCDF (output of emis_union).
        Must contain sector variables (energy, residential, etc.).
        Dimensions: (lat, lon).
    save_dir : str
        Directory to save speciated output files (one per lumped species).
    species_fraction_csv : str, optional
        Path to all_species_fraction.csv.
        Default: bundled cinei/data/all_species_fraction.csv.
    mapping_csv : str, optional
        Path to 'mapping species to lumps.csv'.
        Default: bundled 'cinei/data/mapping species to lumps.csv'.
    sectors : list of str, optional
        Sectors to include. Default: all 8 sectors.
        Available: energy, residential, industry, agriculture,
                   transportation, waste, shipping, aviation.

    Returns
    -------
    list of str
        Paths to output NetCDF files (one per lumped VOC species).

    Examples
    --------
    >>> import cinei
    >>> nmvoc_file = '/data/output/CINEI_2017_Jan_NMVOC_0p25deg_China.nc'

    >>> # Full speciation (all sectors, all lumps)
    >>> outputs = cinei.nmvoc_speciation(
    ...     nmvoc_nc_path=nmvoc_file,
    ...     save_dir='/data/output/voc_speciated/'
    ... )

    >>> # Only specific sectors
    >>> outputs = cinei.nmvoc_speciation(
    ...     nmvoc_nc_path=nmvoc_file,
    ...     save_dir='/data/output/voc_speciated/',
    ...     sectors=['energy', 'transportation', 'industry']
    ... )
    """
    nmvoc_nc_path = Path(nmvoc_nc_path)
    save_dir      = Path(save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)

    # ── Bundled data ───────────────────────────────────────────────────
    if species_fraction_csv is None:
        species_fraction_csv = get_data_path('all_species_fraction.csv')
    if mapping_csv is None:
        mapping_csv = get_data_path('mapping species to lumps.csv')

    # ── Validate input ─────────────────────────────────────────────────
    if not nmvoc_nc_path.exists():
        raise FileNotFoundError(
            f"[CINEI] NMVOC file not found: {nmvoc_nc_path}"
        )

    # ── Load NMVOC emissions ───────────────────────────────────────────
    emis_ds    = xr.open_dataset(str(nmvoc_nc_path))
    lon_arange = emis_ds.lon.values
    lat_arange = emis_ds.lat.values
    n_lat      = len(lat_arange)
    n_lon      = len(lon_arange)

    # Auto-detect resolution
    res = round(float(lon_arange[1] - lon_arange[0]), 4) if len(lon_arange) > 1 else 0.25
    res_str = str(res).replace('.', 'p')

    # ── Validate sectors ───────────────────────────────────────────────
    if sectors is None:
        sectors = list(SECTOR_SAMPLE_RANGE.keys())
    else:
        invalid = [s for s in sectors if s not in SECTOR_SAMPLE_RANGE]
        if invalid:
            raise ValueError(
                f"[CINEI] Invalid sectors: {invalid}\n"
                f"        Available: {list(SECTOR_SAMPLE_RANGE.keys())}"
            )

    # Check sectors exist in file
    missing = [s for s in sectors if s not in emis_ds.data_vars]
    if missing:
        print(f"[CINEI] ⚠️  Sectors missing in NMVOC file: {missing} → skipped")
        sectors = [s for s in sectors if s in emis_ds.data_vars]

    if not sectors:
        raise ValueError(
            f"[CINEI] No valid sectors found in {nmvoc_nc_path.name}\n"
            f"        Available vars: {list(emis_ds.data_vars)}"
        )

    print(f"[CINEI] NMVOC Speciation")
    print(f"[CINEI] Input   : {nmvoc_nc_path.name}")
    print(f"[CINEI] Grid    : {n_lat} × {n_lon}  res={res}°")
    print(f"[CINEI] Sectors : {sectors}")
    print()

    # ── Load speciation profiles ───────────────────────────────────────
    df_frac = pd.read_csv(species_fraction_csv).set_index('SPECIE NAME')
    mapping = pd.read_csv(mapping_csv, sep=';')

    df78 = df_frac.iloc[0:78, :].copy()
    df78['lumps'] = mapping['mapping to modelling species[2]'].values.tolist()
    df_lp = df78.groupby('lumps').sum()

    n_lumps = df_lp.shape[0]
    print(f"[CINEI] Lumped species : {n_lumps}")
    print(f"[CINEI] First 5       : {df_lp.index.tolist()[:5]}")
    print()

    # ── Speciation loop ────────────────────────────────────────────────
    outputs = []
    for lp_idx, lp in enumerate(df_lp.index):

        voc_emis = xr.Dataset(
            coords={'lon': lon_arange, 'lat': lat_arange}
        )

        for sec in sectors:
            sm_start, sm_end = SECTOR_SAMPLE_RANGE[sec]
            df_sec = df_lp.iloc[:, sm_start:sm_end].copy()
            df_sec.replace(np.nan, 0, inplace=True)

            # Sum subsector contributions
            n_subsec = df_sec.shape[1]
            emis_subsectors = np.zeros((n_subsec, n_lat, n_lon), dtype='float32')
            for i in range(n_subsec):
                frac = float(df_sec.iloc[lp_idx, i])
                emis_subsectors[i] = emis_ds[sec].values * frac * 0.01

            voc_emis[sec] = (('lat', 'lon'), emis_subsectors.sum(axis=0))

        # ── Save one nc per lumped species ─────────────────────────────
        src_stem = nmvoc_nc_path.stem
        out_name = f"{src_stem.replace('NMVOC', lp)}.nc"
        out_path = save_dir / out_name

        voc_emis.attrs['lump_species'] = lp
        voc_emis.attrs['source_file']  = nmvoc_nc_path.name
        voc_emis.attrs['unit']         = 'ton/month/grid'
        voc_emis.to_netcdf(str(out_path), format="NETCDF3_CLASSIC")

        print(f"[CINEI]   ✅ {lp:<15} → {out_name}")
        outputs.append(str(out_path))

    print(f"\n[CINEI] ✅ Done! {len(outputs)} files saved to {save_dir}")
    emis_ds.close()
    return outputs
