from setuptools import setup, find_packages

long_description = open("README.md").read()

setup(
    name="cinei",
    version="2.1.0",
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
        "rasterio",
    ],
    python_requires=">=3.7",
    author="Yijuan Zhang",
    author_email="your@email.com",
    description=(
        "Coupled and Integrated Emission Inventory (CINEI): "
        "integrating anthropogenic emission inventories toward "
        "complete sectoral coverage, finer spatial resolution, "
        "and consistent NMVOC speciation for atmospheric chemistry, "
        "climate and multi-disciplinary applications."
    ),
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Luyikeka/cinei",
    project_urls={
        "Documentation": "https://luyikeka.github.io/cinei/",
        "Source Code":   "https://github.com/Luyikeka/cinei",
        "Bug Tracker":   "https://github.com/Luyikeka/cinei/issues",
        "PyPI":          "https://pypi.org/project/cinei/",
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Atmospheric Science",
        "Topic :: Scientific/Engineering :: GIS",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    keywords=[
        "emission inventory", "atmospheric chemistry",
        "NMVOC speciation", "CEDS", "MEIC", "HTAP", "EDGAR",
        "WRF-Chem", "ICON", "CMIP", "KM-scale climate modeling",
        "climate modeling", "air quality",
        "China emissions", "anthropogenic emissions",
    ],
)
