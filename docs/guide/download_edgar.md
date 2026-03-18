# EDGAR Data Download

**EDGAR v8.1** — Emissions Database for Global Atmospheric Research  
Global gridded emissions at 0.1°, monthly, 1970–2022.

**Source:** [edgar.jrc.ec.europa.eu/dataset_ap81](https://edgar.jrc.ec.europa.eu/dataset_ap81)

## Available species

BC, CO, NH3, NMVOC, NOx, OC, PM10, PM2.5, SO2

## Download by year
```python
import cinei

# List available species
cinei.list_edgar_species()

# Download NOx and SO2 for 2017
cinei.download_edgar(
    save_dir='/work/b123456/data/EDGAR',
    species=['NOx', 'SO2'],
    years=[2017]
)

# Download multiple years
cinei.download_edgar(
    save_dir='/work/b123456/data/EDGAR',
    species=['NOx'],
    years=list(range(2013, 2021))
)
```

## Download specific month
```python
# Download NOx for January 2017 only
cinei.download_edgar_monthly(
    save_dir='/work/b123456/data/EDGAR',
    species=['NOx'],
    year=2017,
    month=1
)
```

!!! note
    EDGAR annual files are ~15 MB per species/year — much smaller than HTAP.
    `download_edgar_monthly()` downloads the annual file and extracts the
    requested month as a `[lat, lon]` NetCDF.

## Output filename format
```
EDGAR_v8.1_{species}_{year}_{month:02d}_{month_name}_{data_type}.nc
```

Example: `EDGAR_v8.1_NOx_2017_01_Jan_fluxes.nc`
