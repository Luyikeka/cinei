# Basic Workflow Tutorial

This tutorial shows a complete workflow: download data, integrate inventories,
visualize the output, and optionally run VOC speciation.

## Step 1: Install CINEI
```bash
pip install cinei
```

## Step 2: Download input data
```python
import cinei

# Download CEDS NMVOC
cinei.download_ceds(
    save_dir='/work/bb1554/data/CEDS',
    species=['NMVOC']
)

# Download HTAP NMVOC January 2017
cinei.download_htap_monthly(
    save_dir='/work/bb1554/data/HTAP',
    species=['NMVOC'],
    year=2017,
    month=1,
    keep_annual=True
)

# Download MEIC sample data
cinei.download_meic_sample(
    save_dir='/work/bb1554/data/MEIC',
    months=['jan']
)
```

## Step 3: Check MEIC files
```python
result = cinei.check_meic_files(
    meic_dir='/work/bb1554/data/MEIC',
    year=2017,
    species=['NMVOC'],
    months=[1]
)
print("Missing:", result['missing'])
```

## Step 4: Run integration
```python
output = cinei.emis_union(
    species  = 'NMVOC',
    month    = 1,
    year     = 2017,
    outer_dir= '/work/bb1554/data/CEDS',
    inner_dir= '/work/bb1554/data/MEIC',
    save_dir = '/work/bb1554/output/cinei',
    agg_dir  = '/work/bb1554/data/HTAP',
    region   = 'China',
    output_res = 0.25,
)
print("Output:", output)
```

During integration, CINEI automatically prints a **conservation check table**
to verify that regridding preserves total emissions:
```
[CINEI] ── Regridding Conservation Check ────────────────
[CINEI] Sector          Src total    Dst total    Ratio  Status
[CINEI] -----------------------------------------------------------
[CINEI] aviation           459.56       459.56   1.0000  ✅
[CINEI] waste            86051.38     86051.38   1.0000  ✅
[CINEI] agriculture     260433.30    260433.31   1.0000  ✅
[CINEI] shipping          9474.11      9474.11   1.0000  ✅  (CEDS ships added separately)
```

!!! tip
    A ratio of 1.0000 confirms that total emissions are exactly conserved
    during regridding from 0.1° to 0.25°. Any ratio deviating from 1.0
    indicates a regridding issue that should be investigated.

## Step 5: Visualize all sectors
```python
fig = cinei.cinei_plot(
    output,
    log_scale  = True,
    save_path  = '/work/bb1554/output/cinei/CINEI_2017_Jan_NMVOC_sectors.png'
)
```

This generates a 3×3 panel showing all 8 sectors and the total sum,
each with their emission totals in the title.

## Step 5b: NMVOC speciation *(optional)*

!!! note
    This step is **not required** for standard CINEI integration.
    Run speciation only if your atmospheric model (e.g. WRF-Chem)
    requires individual VOC lumped species (e.g. MOZART mechanism).
```python
# Disaggregate total NMVOC into lumped model species
speciated_files = cinei.nmvoc_speciation(
    nmvoc_nc_path = output,
    save_dir      = '/work/bb1554/output/cinei/voc_speciated/',
)

print(f"Generated {len(speciated_files)} speciated files")
# One NetCDF per lumped species (e.g. BIGALK, BIGENE, CH2O, ...)
```

Each output file contains the same 8 sector variables as the NMVOC file,
but for a single lumped VOC species. The files are named:
```
CINEI_2017_Jan_BIGALK_0p25deg_China.nc
CINEI_2017_Jan_BIGENE_0p25deg_China.nc
CINEI_2017_Jan_CH2O_0p25deg_China.nc
...
```

!!! tip
    Use `sectors` argument to speciate only specific sectors:
```python
    cinei.nmvoc_speciation(
        nmvoc_nc_path = output,
        save_dir      = '/work/bb1554/output/voc_speciated/',
        sectors       = ['energy', 'transportation', 'industry']
    )
```

## Step 6: Grid area calculation
```python
import numpy as np

lat = np.arange(10.125, 60, 0.25)
lon = np.arange(70.125, 150, 0.25)
lon_2d, lat_2d = np.meshgrid(lon, lat)
area = cinei.ll_area(lat_2d, 0.25)
print(f"Grid area shape: {area.shape}")
print(f"Area range: {area.min():.1f} – {area.max():.1f} km²")
```

## Full example (minimal)
```python
import cinei

# One-liner integration with all defaults
output = cinei.emis_union(
    species   = 'NMVOC',
    month     = 1,
    year      = 2017,
    outer_dir = '/work/bb1554/data/CEDS',
    inner_dir = '/work/bb1554/data/MEIC',
    save_dir  = '/work/bb1554/output',
    agg_dir   = '/work/bb1554/data/HTAP',
    region    = 'China',
)

# Plot all sectors
cinei.cinei_plot(output, save_path='/work/bb1554/output/sectors.png')
```
