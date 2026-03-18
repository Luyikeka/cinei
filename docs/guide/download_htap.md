# Downloading Emission Data

CINEI provides built-in download functions for all supported emission inventories.
This page explains each argument and how to use them.

---

## Arguments Reference

All download functions share a consistent set of arguments.
Understanding each argument once lets you use any inventory download function.

---

### `save_dir`
**Required.** Directory where files will be saved.
Created automatically if it does not exist.
```python
save_dir = '/work/b123456/data/HTAP'          # DKRZ
save_dir = '/mnt/hgfs/seafile/testdata/HTAP' # local VM
```

---

### `species`
**Optional.** List of species to download. Case-insensitive.
If `None`, all available species are downloaded.

| Standard | Also accepted |
|----------|--------------|
| `'BC'` | `'bc'` |
| `'CO'` | `'co'` |
| `'NH3'` | `'nh3'` |
| `'NMVOC'` | `'nmvoc'`, `'VOC'`, `'voc'` |
| `'NOx'` | `'nox'`, `'NOX'` |
| `'OC'` | `'oc'` |
| `'PM10'` | `'pm10'` |
| `'PM2.5'` | `'pm2.5'`, `'PM25'`, `'pm25'` |
| `'SO2'` | `'so2'` |
```python
species = ['NOx']                  # single species
species = ['NOx', 'SO2', 'PM2.5'] # multiple species
species = None                     # all species (default)
```

---

### `year` / `years`
**Optional.** Target year(s) as integer or list of integers.
```python
year  = 2017                        # single year
years = [2015, 2016, 2017]          # multiple years
years = list(range(2010, 2018))     # range of years
```

Each inventory has its own temporal coverage:

| Inventory | Coverage |
|-----------|----------|
| CEDS | 1750–2019 |
| HTAP | 2000–2018 |
| EDGAR | 1970–2022 |

---

### `month`
**Required for monthly functions.**
Target month as integer 1–12. Auto-converts to all required formats internally.
```python
month = 1    # January
month = 7    # July
month = 12   # December
```

---

### `resolution`
**Optional (HTAP only).** Spatial resolution of gridded data.
Default: `'05x05'`

| Option | Resolution | File size |
|--------|-----------|-----------|
| `'05x05'` | 0.5° × 0.5° | ~560–840 MB per species |
| `'01x01'` | 0.1° × 0.1° | ~8–13 GB per species |
```python
resolution = '05x05'   # recommended
resolution = '01x01'   # high-res, very large
```

---

### `data_type`
**Optional (HTAP and EDGAR).** Type of emission data.
Default: `'emissions'`

| Option | Unit | Use case |
|--------|------|----------|
| `'emissions'` | Mg/month | total emission amount |
| `'fluxes'` | kg/m²/s | for atmospheric models |
```python
data_type = 'emissions'   # for CINEI integration
data_type = 'fluxes'      # for WRF-Chem or similar
```

---

### `extract`
**Optional.** Automatically unzip after download.
Default: `True`
```python
extract = True    # unzip immediately (recommended)
extract = False   # keep as .zip only
```

---

### `keep_zip` / `keep_tar`
**Optional.** Keep compressed file after extraction.
Default: `False`
```python
keep_zip = False   # delete after extraction (saves disk space)
keep_zip = True    # keep (useful to re-extract later)
```

---

### `keep_annual`
**Optional (monthly functions only).**
Keep the full annual NetCDF after extracting the requested month.
Default: `False`
```python
keep_annual = False  # delete annual file after extracting month
keep_annual = True   # keep annual file (reuse for other months)
```

!!! tip
    Set `keep_annual=True` when extracting multiple months from the same year
    to avoid re-downloading the large zip file each time.

---

## Download by Inventory

### CEDS

Global gridded anthropogenic emissions at 0.5°, monthly, 1750–2019.
[DOI: 10.25584/PNNLDataHub/1779095](https://doi.org/10.25584/PNNLDataHub/1779095)
```python
import cinei

cinei.download_ceds(
    save_dir = '/work/b123456/data/CEDS',
    species  = ['NMVOC', 'NOx', 'SO2'],
    keep_tar = False,
)
```

---

### MEIC

China regional emissions at 0.25°, monthly, by sector.
Sample data (2017 Jan & Jul) publicly available on Zenodo.
[DOI: 10.5281/zenodo.15039737](https://doi.org/10.5281/zenodo.15039737)
```python
# Download sample data
cinei.download_meic_sample(
    save_dir = '/work/b123456/data/MEIC',
    months   = ['jan', 'jul'],
)

# Check which files are present
cinei.check_meic_files(
    meic_dir = '/work/b123456/data/MEIC/2017',
    year     = 2017,
    species  = ['NOx', 'SO2'],
)

# Print full dataset registration instructions
cinei.get_meic_info()
```

---

### EDGAR

Global gridded emissions at 0.1°, monthly, 1970–2022.
[edgar.jrc.ec.europa.eu/dataset_ap81](https://edgar.jrc.ec.europa.eu/dataset_ap81)
```python
# Download full year
cinei.download_edgar(
    save_dir  = '/work/b123456/data/EDGAR',
    species   = ['NOx', 'SO2'],
    years     = [2017],
    data_type = 'fluxes',
)

# Download specific month only
cinei.download_edgar_monthly(
    save_dir  = '/work/b123456/data/EDGAR',
    species   = ['NOx'],
    year      = 2017,
    month     = 1,
)
```

---

### HTAP

Global emission mosaic at 0.1° and 0.5°, monthly, 2000–2018.
[DOI: 10.5281/zenodo.7516361](https://doi.org/10.5281/zenodo.7516361)
```python
# Preview file sizes before downloading
cinei.list_htap_files(resolution='05x05', data_type='emissions')

# Download full dataset (all years 2000–2018)
cinei.download_htap(
    save_dir   = '/work/b123456/data/HTAP',
    species    = ['NMVOC', 'NOx', 'SO2'],
    resolution = '05x05',
    data_type  = 'emissions',
    extract    = True,
    keep_zip   = False,
)

# Download one specific month
cinei.download_htap_monthly(
    save_dir    = '/work/b123456/data/HTAP',
    species     = ['NMVOC'],
    year        = 2017,
    month       = 1,
    resolution  = '05x05',
    data_type   = 'emissions',
    keep_annual = True,
)
```

---

## Example: HTAP NMVOC January 2017

Here is a complete step-by-step example using HTAP NMVOC data.

**Step 1 — Preview available files:**
```python
import cinei
cinei.list_htap_files(resolution='05x05', species=['NMVOC'])
```
Output:
```
[CINEI] HTAP v3 — 0.5° x 0.5°  emissions
[CINEI] Species    Filename                                       Size
[CINEI] NMVOC      gridmaps_05x05_emissions_NMVOC.zip            839 MB
```

**Step 2 — Download January 2017:**
```python
cinei.download_htap_monthly(
    save_dir    = '/work/b123456/data/HTAP',
    species     = ['NMVOC'],
    year        = 2017,
    month       = 1,
    resolution  = '05x05',
    data_type   = 'emissions',
    keep_annual = True,   # keep for July download below
)
```

**Step 3 — Reuse annual file to extract another month:**
```python
cinei.download_htap_monthly(
    save_dir    = '/work/b123456/data/HTAP',
    species     = ['NMVOC'],
    year        = 2017,
    month       = 7,
    resolution  = '05x05',
    keep_annual = False,   # now safe to delete
)
```

**Output files:**
```
/work/b123456/data/HTAP/
├── gridmaps_05x05_emissions_NMVOC/
│   └── edgar_HTAPv3_2017_NMVOC.nc     ← annual file (if keep_annual=True)
├── HTAP_v3_NMVOC_05x05_2017_01_Jan_emissions.nc   ← monthly [lat, lon]
└── HTAP_v3_NMVOC_05x05_2017_07_Jul_emissions.nc   ← monthly [lat, lon]
```

---

## Citation
```
Crippa, M. et al.: HTAP_v3 emission mosaic,
https://doi.org/10.5281/zenodo.7516361, 2023.
```
