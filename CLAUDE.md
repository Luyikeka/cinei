# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**CINEI** (Coupled and Integrated Emission Inventory) — Python package on PyPI as `cinei`. Merges a global "outer" inventory (CEDS / EDGAR / HTAP / user) with a regional "inner" inventory (MEIC / EDGAR / HTAP / user) into a unified NetCDF at a chosen resolution, for atmospheric chemistry and climate studies. Docs: https://luyikeka.github.io/cinei/

## Architecture

User-facing workflow is a three-stage pipeline, all re-exported at package level via `cinei/__init__.py`:

1. **Download** (`download.py`) — `download_ceds`, `download_meic_sample`, `download_htap[_monthly]`, `download_edgar[_monthly]` fetch raw gridded NetCDFs.
2. **Integrate** (`core.py`) — `emis_union()` is the main entry point. It loads per `outer_source`/`inner_source`, harmonizes species via `data/Integrated_mapper.csv`, converts units (VOCs handled specially), regrids outer → target resolution, clips with shapefiles in `data/`, combines inner-over-outer sector-by-sector, and writes NetCDF. Eight standard sectors: `energy, residential, industry, agriculture, transportation, waste, shipping, aviation`.
3. **Post-process** — `cinei_plot()` / `plot_emission_map()` (`visualization.py`); `nmvoc_speciation()` (`voc_speciation.py`) disaggregates NMVOC into lumped mechanism species.

Supporting modules: `regions.py` (named bbox presets like `'China'`, `'NCP'`), `regridding.py` (`SUPPORTED_RESOLUTIONS = 0.05, 0.1, 0.25, 0.5`), `preprocess.py` (validate/convert user NetCDFs to CINEI-standard so they can be passed as `*_source='user'`), `utils.py` (grid-cell area + bundled-data path helpers).

## Bundled data (`cinei/data/`)

Always resolve via `get_data_path`, `get_mapper_path`, `get_country_shp`, `get_province_shp` from `utils.py` — **never hardcode paths**, since they need to work after `pip install`. Chinese filenames like `分省.shp` (province) are intentional; preserve them. `package_data` in `setup.py` controls what ships in the wheel — update it when adding new data files.

## Development commands

```bash
pip install -e .                   # dev install
python setup.py sdist bdist_wheel  # build for PyPI
mkdocs serve                       # preview docs at localhost:8000
mkdocs build                       # static site → ./site/
```

No test suite, linter, or CI is configured. `site/` is generated — don't edit it.

## Gotchas

- Public API is re-exported in `__init__.py`. New user-facing functions must be added to both the imports **and** `__all__`.
- `SUPPORTED_OUTER` / `SUPPORTED_INNER` are asymmetric: CEDS is outer-only, MEIC is inner-only, EDGAR/HTAP/user work either side.
- `_parse_month()` in `core.py` deliberately accepts int, `'01'`, `'1'`, `'Jan'`, `'January'` — don't "simplify" it.
- Version lives in `cinei/__version__.py`; `setup.py` has a separate `version=`. Keep them in sync on release.
- `VOC_species_nc.py` is legacy — use `voc_speciation.nmvoc_speciation`.
