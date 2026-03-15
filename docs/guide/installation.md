# Installation

## Requirements

- Python ≥ 3.7
- Dependencies: numpy, pandas, xarray, rioxarray, geopandas, matplotlib, requests, tqdm

## Install from PyPI
```bash
pip install cinei
```

## Install latest from GitHub
```bash
pip install git+https://github.com/Luyikeka/claude_cinei.git
```

## Verify installation
```python
import cinei
print(cinei.__version__)
```

## HPC environments (e.g. DKRZ Levante)
```bash
pip install cinei --user
```

Or in a Jupyter notebook:
```python
import sys
!{sys.executable} -m pip install cinei --user
```

!!! note
    After installing in a Jupyter notebook, restart the kernel before importing.
