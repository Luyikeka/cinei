# CINEI — Coupled and Integrated Emission Inventory

[![PyPI version](https://badge.fury.io/py/cinei.svg)](https://badge.fury.io/py/cinei)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.15000795.svg)](https://doi.org/10.5281/zenodo.15000795)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Documentation](https://img.shields.io/badge/docs-luyikeka.github.io/cinei-blue)](https://luyikeka.github.io/cinei/)

📖 **Full documentation: [https://luyikeka.github.io/cinei/](https://luyikeka.github.io/cinei/)**

---

## Overview

**CINEI** is a Python package for integrating anthropogenic emission inventories for China, combining global (CEDS) and regional (MEIC) datasets into a unified temporal and spatial resolution NetCDF product.

## Installation
```bash
pip install cinei
```

## Quick Start
```python
import cinei

# Download CEDS CO data
cinei.download_ceds(save_dir='/data/CEDS', species=['CO'])

# Download EDGAR NOx for 2017
cinei.download_edgar(save_dir='/data/EDGAR', species=['NOx'], years=[2017])

# Run emission integration
cinei.emis_union(
    ceds_dir='/data/CEDS',
    meic_dir='/data/MEIC/2017',
    save_dir='/data/output',
    spec_ceds='NOx', spec_meic='NOx',
    mon='Jan', mon_id=0, mon_agg='01', year='2017',
    mapper_path='/data/Integrated_mapper.csv',
    country_shp='/data/shapefiles/country.shp',
    province_shp='/data/shapefiles/province.shp',
    agg_dir='/data/agg_sectors'
)
```

## Documentation

Full documentation including installation guide, API reference, data download guide,
and tutorials is available at:

**[https://luyikeka.github.io/cinei/](https://luyikeka.github.io/cinei/)**

## Citation
```
Zhang, Y.: CINEI V1.1, https://doi.org/10.5281/zenodo.15000795, 2025.
```

## License

MIT License
