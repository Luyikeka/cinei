# CEDS Data Download

**CEDS v_2021_04_21** — Community Emissions Data System  
Global gridded anthropogenic emissions at 0.5°, monthly, 1750–2019.

**Source:** [PNNL DataHub](https://doi.org/10.25584/PNNLDataHub/1779095)

## Available species

| Species | Description |
|---------|-------------|
| SO2 | Sulfur dioxide |
| NOx | Nitrogen oxides |
| CO | Carbon monoxide |
| BC | Black carbon |
| OC | Organic carbon |
| NH3 | Ammonia |
| NMVOC | Non-methane VOCs |
| CO2 | Carbon dioxide |
| CH4 | Methane |
| N2O | Nitrous oxide |
| PM2.5 | Fine particles |
| PM10 | Coarse particles |

## Download
```python
import cinei

# Download CO only (recommended for testing)
cinei.download_ceds(
    save_dir='/work/b123456/data/CEDS',
    species=['CO']
)

# Download multiple species
cinei.download_ceds(
    save_dir='/work/b123456/data/CEDS',
    species=['CO', 'NOx', 'SO2']
)

# Download all species (warning: large file ~200 GB)
cinei.download_ceds(save_dir='/work/b123456/data/CEDS')
```

!!! note
    Species names are case-insensitive: `'NOx'`, `'nox'`, `'NOX'` all work.

!!! tip
    Download supports **resume** — if interrupted, re-run the same command
    to continue from where it stopped.
