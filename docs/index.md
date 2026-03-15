# CINEI — Coupled and Integrated Emission Inventory

[![PyPI version](https://badge.fury.io/py/cinei.svg)](https://badge.fury.io/py/cinei)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.15000795.svg)](https://doi.org/10.5281/zenodo.15000795)

**CINEI** is a Python package for integrating anthropogenic emission inventories for China,
combining global (CEDS) and regional (MEIC) datasets into a unified 0.25° monthly NetCDF product.

## Key Features

- 🔗 **Integrate** CEDS (global 0.5°) + MEIC (China 0.25°) emission inventories
- 📥 **Download** CEDS, HTAP, EDGAR data directly from public repositories
- 🗺️ **Visualize** emission maps with publication-quality matplotlib figures
- 🛠️ **Grid utilities** for latitude-longitude area calculations

## Supported Inventories

| Inventory | Version | Resolution | Coverage |
|-----------|---------|------------|----------|
| CEDS | v_2021_04_21 | 0.5° | Global, 1750–2019 |
| MEIC | v1.4 | 0.25° | China, monthly |
| HTAP | v3 | 0.1° / 0.5° | Global, 2000–2018 |
| EDGAR | v8.1 | 0.1° | Global, 1970–2022 |

## Quick Install
```bash
pip install cinei
```

## Citation
```
Zhang, Y.: CINEI V1.1, https://doi.org/10.5281/zenodo.15000795, 2025.
```
