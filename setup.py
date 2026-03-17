from setuptools import setup, find_packages
from cinei.__version__ import __version__

setup(
    name="cinei",
    version=__version__,
    packages=find_packages(),
    package_data={
        "cinei": [
            "data/*.csv",
            "data/*.shp",
            "data/*.dbf",
            "data/*.shx",
            "data/*.prj",
            "data/*.sbn",
            "data/*.sbx",
            "data/*.xml",
        ]
    },
    include_package_data=True,
    install_requires=[
        "numpy",
        "pandas",
        "xarray",
        "rioxarray",
        "geopandas",
        "matplotlib",
        "requests",
        "tqdm",
        "scipy",
    ],
    python_requires=">=3.7",
    author="Yijuan Zhang",
    author_email="yijuancham@gmail.com",
    description="Coupled and Integrated Emission Inventory (CINEI)",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/Luyikeka/cinei",
)
