# MEIC Data Download

**MEIC v1.4** — Multi-resolution Emission Inventory for China  
Regional gridded emissions at 0.25°, monthly, by sector.

## Sample data (public)

A sample dataset for 2017 (January and July) is publicly available on Zenodo:

**Source:** [Zenodo 10.5281/zenodo.15039737](https://doi.org/10.5281/zenodo.15039737)
```python
import cinei

# Download both sample months
cinei.download_meic_sample(
    save_dir='/work/b123456/data/MEIC',
    months=['jan', 'jul']
)

# Download January only
cinei.download_meic_sample(
    save_dir='/work/b123456/data/MEIC',
    months=['jan']
)
```

## Full dataset (registration required)
```python
# Print registration instructions
cinei.get_meic_info()
```

Visit: [http://meicmodel.org.cn/?page_id=1772&lang=en](http://meicmodel.org.cn/?page_id=1772&lang=en)

## Expected filename format
```
{year}_{month:02d}_{sector}_{species}.nc
```

Example: `2017_01_agriculture_NOx.nc`

## Check your files
```python
# List expected filenames
cinei.list_meic_filenames(2017, species=['NOx', 'SO2'], months=[1, 7])

# Check which files are present/missing
result = cinei.check_meic_files(
    meic_dir='/work/b123456/data/MEIC/2017',
    year=2017,
    species=['NOx', 'SO2']
)
print(result['missing'])
```
