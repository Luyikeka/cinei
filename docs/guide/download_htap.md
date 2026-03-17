# HTAP Data Download

**HTAP v3** — Hemispheric Transport of Air Pollution emission mosaic
Global gridded emissions, monthly, 2000–2018, 9 species, 16 sectors.

**Source:** [Zenodo 10.5281/zenodo.7516361](https://doi.org/10.5281/zenodo.7516361)

---

## Function: `download_htap()`

Downloads the full HTAP dataset (all years 2000–2018) for selected species.
```python
import cinei

cinei.download_htap(
    save_dir  = '/work/bb1554/data/HTAP',
    species   = ['NOx', 'SO2'],
    resolution= '05x05',
    data_type = 'emissions',
    extract   = True,
    keep_zip  = False,
)
```

### Arguments

#### `save_dir` *(required)*
Directory where downloaded files will be saved.
```python
save_dir = '/work/bb1554/data/HTAP'   # DKRZ
save_dir = '/mnt/hgfs/seafile/testdata/HTAP'  # local VM
```
The directory is created automatically if it does not exist.

---

#### `species` *(optional)*
List of species to download. **Case-insensitive** — all variants below are accepted.
Default: all 9 species.

| Standard name | Also accepted |
|--------------|---------------|
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
# Single species
species = ['NOx']

# Multiple species
species = ['NOx', 'SO2', 'PM2.5']

# All species (default)
species = None
```

!!! tip
    Use `cinei.list_htap_files()` to see file sizes before downloading.

---

#### `resolution` *(optional)*
Spatial resolution of the downloaded gridded data.
Default: `'05x05'`

| Option | Resolution | File size per species |
|--------|-----------|----------------------|
| `'05x05'` | 0.5° × 0.5° | ~560–840 MB |
| `'01x01'` | 0.1° × 0.1° | ~8–13 GB |
```python
resolution = '05x05'   # recommended — smaller files
resolution = '01x01'   # high resolution — very large!
```

!!! warning
    `'01x01'` files are 8–13 GB per species. Only download if you specifically
    need 0.1° resolution. For most applications, `'05x05'` is sufficient.

---

#### `data_type` *(optional)*
Type of emission data to download.
Default: `'emissions'`

| Option | Unit | Use case |
|--------|------|----------|
| `'emissions'` | Mg/month | total emission amount |
| `'fluxes'` | kg/m²/s | emission flux density |
```python
data_type = 'emissions'   # Mg/month — for CINEI integration
data_type = 'fluxes'      # kg/m²/s — for atmospheric models
```

---

#### `extract` *(optional)*
Whether to automatically unzip the downloaded file.
Default: `True`
```python
extract = True    # unzip immediately after download (recommended)
extract = False   # keep as .zip only
```

---

#### `keep_zip` *(optional)*
Whether to keep the `.zip` file after extraction.
Default: `False`
```python
keep_zip = False   # delete zip after extraction (saves disk space)
keep_zip = True    # keep zip (useful if you need to re-extract)
```

---

## Function: `download_htap_monthly()`

Downloads HTAP data and extracts a **specific month** as a standalone
`[lat, lon]` NetCDF file. More efficient than downloading the full dataset
when you only need one month.
```python
import cinei

cinei.download_htap_monthly(
    save_dir   = '/work/bb1554/data/HTAP',
    species    = ['SO2', 'NOx'],
    year       = 2017,
    month      = 1,
    resolution = '05x05',
    data_type  = 'emissions',
    keep_annual= False,
)
```

### Arguments

#### `save_dir` *(required)*
Same as `download_htap()`.

---

#### `species` *(required)*
Same species options as `download_htap()`. Must be provided explicitly.
```python
species = ['SO2']           # single
species = ['SO2', 'NOx']    # multiple
```

---

#### `year` *(required)*
Target year as integer.
**Coverage: 2000–2018**
```python
year = 2017   # ✅
year = 2019   # ❌ raises ValueError — outside coverage
```

---

#### `month` *(required)*
Target month as integer 1–12.
```python
month = 1    # January
month = 7    # July
month = 12   # December
```

---

#### `resolution` *(optional)*
Same as `download_htap()`. Default: `'05x05'`.

---

#### `data_type` *(optional)*
Same as `download_htap()`. Default: `'emissions'`.

---

#### `keep_annual` *(optional)*
Whether to keep the extracted annual NetCDF file after saving the monthly file.
Default: `False`
```python
keep_annual = False  # delete annual nc after extracting month (saves space)
keep_annual = True   # keep annual nc (useful to extract multiple months
                     # without re-downloading the large zip)
```

!!! tip
    If you need multiple months from the same year, set `keep_annual=True`
    on the first call. Subsequent calls will skip the download entirely:
```python
    # First call — downloads zip and extracts annual nc
    cinei.download_htap_monthly(..., year=2017, month=1, keep_annual=True)

    # Second call — reuses existing annual nc, no download needed
    cinei.download_htap_monthly(..., year=2017, month=7, keep_annual=True)
```

---

## Helper: `list_htap_files()`

Preview available files and sizes before downloading.
```python
import cinei

# Default: 0.5° emissions
cinei.list_htap_files()

# Specific resolution and type
cinei.list_htap_files(resolution='01x01', data_type='fluxes')

# Filter by species
cinei.list_htap_files(species=['NOx', 'SO2'])
```

Output example:
```
[CINEI] HTAP v3 — 0.5° x 0.5°  emissions
[CINEI] Species    Filename                                            Size
[CINEI] -----------------------------------------------------------------
[CINEI] NOx        gridmaps_05x05_emissions_NOx.zip                  681 MB
[CINEI] SO2        gridmaps_05x05_emissions_SO2.zip                  556 MB
```

---

## Output file naming
```
# download_htap() → directory per species
gridmaps_05x05_emissions_NOx/
    edgar_HTAPv3_2000_NOx.nc
    edgar_HTAPv3_2001_NOx.nc
    ...
    edgar_HTAPv3_2018_NOx.nc

# download_htap_monthly() → single monthly file
HTAP_v3_SO2_05x05_2017_01_Jan_emissions.nc
```

---

## Citation
```
Crippa, M. et al.: HTAP_v3 emission mosaic,
https://doi.org/10.5281/zenodo.7516361, 2023.
```
