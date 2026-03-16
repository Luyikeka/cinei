"""Utility functions for the CINEI package."""
import numpy as np

def ll_area(lat, res):
    """
    Calculate grid cell area based on latitude and resolution.
    
    Parameters
    ----------
    lat : ndarray
        Latitude values in degrees
    res : float
        Resolution in degrees
        
    Returns
    -------
    ndarray
        Grid cell areas in square kilometers
    """
    Re = 6371.392  # Earth radius in km
    X = Re * np.cos(lat * (np.pi/180)) * (np.pi/180) * res
    Y = Re * (np.pi/180) * res
    return X * Y  # Bug fix: added return statement


import importlib.resources as pkg_resources
from pathlib import Path


def get_data_path(filename):
    """
    Get the full path to a bundled data file in cinei/data/.

    Parameters
    ----------
    filename : str
        Name of the data file, e.g. 'Integrated_mapper.csv',
        'country.shp', '分省.shp'

    Returns
    -------
    str
        Absolute path to the data file.

    Examples
    --------
    >>> import cinei
    >>> mapper_path = cinei.get_data_path('Integrated_mapper.csv')
    >>> country_shp = cinei.get_data_path('country.shp')
    >>> province_shp = cinei.get_data_path('分省.shp')
    """
    data_dir = Path(__file__).parent / "data"
    file_path = data_dir / filename
    if not file_path.exists():
        available = [f.name for f in data_dir.iterdir()
                     if not f.name.startswith('_')]
        raise FileNotFoundError(
            f"[CINEI] Bundled data file not found: '{filename}'\n"
            f"        Available files: {available}"
        )
    return str(file_path)


# ── Bundled data shortcuts ────────────────────────────────────────────────────
def get_mapper_path():
    """Return path to bundled Integrated_mapper.csv."""
    return get_data_path('Integrated_mapper.csv')

def get_country_shp():
    """Return path to bundled country.shp."""
    return get_data_path('country.shp')

def get_province_shp():
    """Return path to bundled 分省.shp."""
    return get_data_path('分省.shp')
