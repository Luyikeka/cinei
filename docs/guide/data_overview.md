# Data Download Overview

CINEI provides built-in download functions for all supported emission inventories.

## Summary

| Inventory | Function | Source | Access |
|-----------|----------|--------|--------|
| CEDS | `download_ceds()` | PNNL DataHub | Open |
| MEIC | `download_meic_sample()` | Zenodo | Open (sample) |
| HTAP | `download_htap()` / `download_htap_monthly()` | Zenodo | Open |
| EDGAR | `download_edgar()` / `download_edgar_monthly()` | JRC FTP | Open |

## Recommended directory structure
```
/work/b123456/data/
├── CEDS/                  # CEDS NetCDF files
├── MEIC/
│   └── 2017/              # MEIC monthly files by year
├── HTAP/                  # HTAP extracted files
├── EDGAR/                 # EDGAR extracted files
├── shapefiles/            # Country and province shapefiles
└── Integrated_mapper.csv  # Species mapper file
```

!!! warning
    HTAP files are large (500 MB–13 GB per species). Use `resolution='05x05'`
    and download only the species you need.
