# Basic Workflow Tutorial

This tutorial shows a complete CINEI workflow: download data, integrate
inventories, verify regridding, visualize results, and run VOC speciation.

---

## Step 1: Install CINEI
```bash
pip install cinei
```

---

## Step 2: Download input data
```python
import cinei

# Download CEDS NMVOC (global background)
cinei.download_ceds(
    save_dir='/work/bb1554/data/CEDS',
    species=['NMVOC']
)

# Download HTAP NMVOC January 2017 (aggregated sectors)
cinei.download_htap_monthly(
    save_dir='/work/bb1554/data/HTAP',
    species=['NMVOC'],
    year=2017,
    month=1,
    keep_annual=True
)

# Download MEIC sample data (regional inner inventory)
cinei.download_meic_sample(
    save_dir='/work/bb1554/data/MEIC',
    months=['jan']
)
```

---

## Step 3: Select region of interest

CINEI provides built-in region presets. Call `list_regions()` to see all:
```python
cinei.list_regions()
```

Output:
```
[CINEI] Built-in region presets:
  Name             Lon min  Lon max  Lat min  Lat max
  -------------------------------------------------------
  China              70.0    150.0     10.0     60.0
  India              65.0    100.0      5.0     40.0
  Ncp               112.0    120.0     35.0     42.0
  Beijing           114.0    118.5     38.5     42.0
  ...
```

Three ways to define your region:
```python
# Option A: built-in name (recommended)
region = 'China'
region = 'Beijing'
region = 'NCP'       # North China Plain
region = 'Germany'

# Option B: manual bounding box
cinei.emis_union(...,
    global_domain = False,
    lon_min = 100.0, lon_max = 130.0,
    lat_min = 20.0,  lat_max = 45.0,
)

# Option C: global domain
cinei.emis_union(..., global_domain=True)
```

---

## Step 4: Run emission integration
```python
output = cinei.emis_union(
    species    = 'NMVOC',   # single species name, auto-mapped
    month      = 1,         # integer 1-12, auto-converts to Jan/01/idx
    year       = 2017,
    outer_dir  = '/work/bb1554/data/CEDS',   # global background
    inner_dir  = '/work/bb1554/data/MEIC',   # regional inventory
    save_dir   = '/work/bb1554/output/cinei',
    agg_dir    = '/work/bb1554/data/HTAP',   # aggregated sectors
    region     = 'China',
    output_res = 0.25,      # 0.05, 0.1, 0.25, or 0.5 degrees
)
```

---

## Step 5: Verify regridding conservation

CINEI automatically prints a conservation check table when regridding
HTAP sectors. This verifies that total emissions are preserved exactly
when converting from 0.1° to the output resolution.
```
[CINEI] ── Regridding Conservation Check ────────────────
[CINEI] Sector          Src total    Dst total    Ratio  Status
[CINEI] ------------------------------------------------------------
[CINEI] aviation           459.56       459.56   1.0000  ✅
[CINEI] waste            86051.38     86051.38   1.0000  ✅
[CINEI] agriculture     260433.30    260433.31   1.0000  ✅
[CINEI] shipping          9474.11      9474.11   1.0000  ✅
[CINEI] ------------------------------------------------------------
[CINEI] Note: ratio=1.0 means total emissions are exactly
[CINEI]       conserved from source to target resolution.
```

### What the conservation ratio means

The **conservative regridding** method sums all 0.1° source grid cells
that fall within each destination grid cell (e.g. 0.25°). This ensures
that total emissions in ton/month are exactly preserved — no artificial
creation or loss of emissions.

| Ratio | Meaning |
|-------|---------|
| `1.0000` | ✅ Perfect conservation — regridding is correct |
| `< 0.99` | ⚠️  Emissions lost — check domain boundaries |
| `> 1.01` | ⚠️  Emissions gained — check for overlapping cells |

!!! note "Shipping note"
    The shipping conservation ratio compares only the HTAP domestic
    shipping component. In the final output, CEDS international shipping
    (outside China) is also added in `emis_union`, so the final shipping
    total will be larger than the HTAP-only source total.

!!! tip "Disable check"
    To suppress the conservation table (e.g. in batch processing):
```python
    # Pass check_conservation=False to regrid_aggregation
    # via the regridding module directly
    from cinei.regridding import regrid_aggregation
    ds = regrid_aggregation(..., check_conservation=False)
```

---

## Step 6: Visualize results

### Plot all sectors at once
```python
fig = cinei.cinei_plot(
    output,
    log_scale = True,       # log scale recommended for emission maps
    cmap      = 'YlOrRd',   # colormap
    save_path = '/work/bb1554/output/CINEI_2017_Jan_NMVOC_sectors.png'
)
```

This generates a 3×3 panel showing all 8 emission sectors plus total sum,
with the total emission for each sector in the subplot title.

![CINEI sector plot](../assets/CINEI_2017_Jan_NMVOC_final.png)

### Plot a single variable
```python
fig = cinei.plot_emission_map(
    file_path = output,
    variable  = 'sum',
    cmap      = 'hot_r',
    title     = 'CINEI NMVOC Total — January 2017',
    save_path = '/work/bb1554/output/CINEI_2017_Jan_NMVOC_sum.png'
)
```

### Plot options

| Argument | Options | Default |
|----------|---------|---------|
| `log_scale` | `True`, `False` | `True` |
| `cmap` | any matplotlib colormap | `'YlOrRd'` |
| `sectors` | list of sector names | all sectors |
| `vmax_percentile` | 1–100 | `99` |

---

## Step 7: VOC speciation (NMVOC only)

For NMVOC runs, disaggregate total NMVOC into lumped model species
(MOZART mechanism):
```python
# Run speciation on NMVOC output
outputs = cinei.nmvoc_speciation(
    nmvoc_nc_path = output,
    save_dir      = '/work/bb1554/output/voc_speciated/',
)
```

Output — one NetCDF per lumped species (18 species total):
```
CINEI_2017_Jan_BENZENE_0p25deg_China.nc
CINEI_2017_Jan_BIGALK_0p25deg_China.nc
CINEI_2017_Jan_C2H4_0p25deg_China.nc
CINEI_2017_Jan_TOLUENE_0p25deg_China.nc
... (18 files total)
```

Speciate only selected sectors:
```python
cinei.nmvoc_speciation(
    nmvoc_nc_path = output,
    save_dir      = '/work/bb1554/output/voc_speciated/',
    sectors       = ['energy', 'transportation', 'industry']
)
```

Or trigger automatically inside `emis_union`:
```python
cinei.emis_union(
    species            = 'NMVOC',
    ...
    nmvoc_speciation   = True,   # auto-run after integration
)
```

---

## Bundled data files

CINEI includes essential data files bundled with the package — no
separate download required.

| File | Description | Used for |
|------|-------------|---------|
| `Integrated_mapper.csv` | Species name mapping & unit conversion | `emis_union()` |
| `country.shp` + `.dbf/.prj/.shx` | World country boundaries | China/region clipping |
| `分省.shp` + related files | China province boundaries | Taiwan exclusion |
| `all_species_fraction.csv` | VOC speciation fractions by sector | `nmvoc_speciation()` |
| `mapping species to lumps.csv` | MOZART lumped species mapping | `nmvoc_speciation()` |

These files are automatically used as defaults — you do not need to
specify their paths unless you want to use custom versions:
```python
# Default — uses bundled files automatically
cinei.emis_union(species='SO2', ...)

# Custom mapper — override bundled default
cinei.emis_union(
    species      = 'SO2',
    mapper_path  = '/my/custom/mapper.csv',
    country_shp  = '/my/custom/country.shp',
    province_shp = '/my/custom/province.shp',
    ...
)

# Access bundled file paths directly
print(cinei.get_mapper_path())
print(cinei.get_country_shp())
print(cinei.get_province_shp())
print(cinei.get_data_path('all_species_fraction.csv'))
```

### Get bundled files from GitHub

All bundled data files are available in the CINEI GitHub repository:
```
https://github.com/Luyikeka/cinei/tree/main/cinei/data/
```

To download individually:
```bash
# Clone the repository
git clone https://github.com/Luyikeka/cinei.git

# Data files are in:
ls cinei/cinei/data/
```

Or install via pip to get all bundled files automatically:
```bash
pip install cinei
python -c "import cinei; print(cinei.get_mapper_path())"
```
