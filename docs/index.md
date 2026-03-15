# CINEI — Coupled and Integrated Emission Inventory

[![PyPI version](https://badge.fury.io/py/cinei.svg)](https://badge.fury.io/py/cinei)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.15000795.svg)](https://doi.org/10.5281/zenodo.15000795)
[![Documentation](https://img.shields.io/badge/docs-luyikeka.github.io/cinei-blueviolet)](https://luyikeka.github.io/cinei/)

**CINEI** is a Python package for integrating anthropogenic emission inventories,
combining global (e.g. CEDS) and regional (e.g. MEIC for China) datasets into a
unified temporal and spatial resolution NetCDF product.

## Quick Install
```bash
pip install cinei
```

## Key Functions

- 📥 **Download** CEDS, MEIC, HTAP, EDGAR data directly from public repositories
- 🔗 **Integrate** global and regional emission inventories into unified NetCDF
- 🛠️ **Preprocess** user-provided data into CINEI-compatible format
- 🗺️ **Visualize** emission maps with publication-quality matplotlib figures
- 📐 **Grid utilities** for latitude-longitude area calculations

## Supported Inventories

| Inventory | Version | Resolution | Coverage |
|-----------|---------|------------|----------|
| CEDS | v_2021_04_21 | 0.5° | Global, 1750–2019 |
| MEIC | v1.4 | 0.25° | China, monthly |
| HTAP | v3 | 0.1° / 0.5° | Global, 2000–2018 |
| EDGAR | v8.1 | 0.1° | Global, 1970–2022 |

## Citation
```
Zhang, Y.: CINEI V1.1, https://doi.org/10.5281/zenodo.15000795, 2025.
```
