"""Shared fixtures for CINEI tests."""
from pathlib import Path

import numpy as np
import pytest
import xarray as xr


@pytest.fixture
def synthetic_nc(tmp_path):
    """
    Write a minimal CINEI-shaped NetCDF and return its path.

    Contents: 12 months × 4 lat × 4 lon, with the 8 standard CINEI sector
    variables plus 'sum'. Dimension order is (month, lat, lon) so the file
    should pass check_user_data with status 'ok'.
    """
    lat = np.array([10.0, 10.25, 10.5, 10.75], dtype=np.float32)
    lon = np.array([110.0, 110.25, 110.5, 110.75], dtype=np.float32)
    month = np.arange(1, 13, dtype=np.int32)

    shape = (12, 4, 4)
    sectors = [
        "agriculture", "industry", "power", "residential",
        "transportation", "shipping", "aviation", "waste", "sum",
    ]

    data_vars = {
        name: (("month", "lat", "lon"),
               np.ones(shape, dtype=np.float32) * (i + 1))
        for i, name in enumerate(sectors)
    }

    ds = xr.Dataset(
        data_vars=data_vars,
        coords={"month": month, "lat": lat, "lon": lon},
        attrs={"units": "ton/grid/month"},
    )

    out = tmp_path / "synthetic_ok.nc"
    ds.to_netcdf(str(out))
    ds.close()
    return out


@pytest.fixture
def synthetic_nc_missing_sectors(tmp_path):
    """
    NetCDF with correct dims but unrecognized sector variables — expected
    to produce status 'warning' from check_user_data.
    """
    lat = np.array([10.0, 10.25], dtype=np.float32)
    lon = np.array([110.0, 110.25], dtype=np.float32)
    month = np.arange(1, 13, dtype=np.int32)
    shape = (12, 2, 2)

    ds = xr.Dataset(
        data_vars={"mystery_var": (("month", "lat", "lon"),
                                   np.zeros(shape, dtype=np.float32))},
        coords={"month": month, "lat": lat, "lon": lon},
    )
    out = tmp_path / "synthetic_bad.nc"
    ds.to_netcdf(str(out))
    ds.close()
    return out
