# HTAP Data Download

**HTAP v3** — Hemispheric Transport of Air Pollution emission mosaic  
Global gridded emissions at 0.1° and 0.5°, monthly, 2000–2018.

**Source:** [Zenodo 10.5281/zenodo.7516361](https://doi.org/10.5281/zenodo.7516361)

## Available species

BC, CO, NH3, NMVOC, NOx, OC, PM10, PM2.5, SO2

## Download full species (all years)
```python
import cinei

# List available files and sizes
cinei.list_htap_files(resolution='05x05', data_type='emissions')

# Download NOx and SO2 at 0.5° (recommended)
cinei.download_htap(
    save_dir='/work/bb1554/data/HTAP',
    species=['NOx', 'SO2'],
    resolution='05x05',
    data_type='emissions'
)
```

## Download specific month
```python
# Download SO2 for July 2017
cinei.download_htap_monthly(
    save_dir='/work/bb1554/data/HTAP',
    species=['SO2'],
    year=2017,
    month=7,
    keep_annual=True   # keep extracted nc for reuse
)
```

!!! warning
    Each species zip file is 500 MB–13 GB. Use `resolution='05x05'` to save space.

!!! tip
    Use `keep_annual=True` if you need multiple months from the same year —
    avoids re-downloading the large zip file.

## Output filename format
```
HTAP_v3_{species}_{resolution}_{year}_{month:02d}_{month_name}_{data_type}.nc
```

Example: `HTAP_v3_SO2_05x05_2017_07_Jul_emissions.nc`
