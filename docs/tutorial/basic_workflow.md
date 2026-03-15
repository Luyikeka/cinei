# Basic Workflow Tutorial

This tutorial shows a complete workflow: download data, integrate inventories,
and visualize the output.

## Step 1: Install CINEI
```bash
pip install cinei
```

## Step 2: Download input data
```python
import cinei

# Download CEDS CO
cinei.download_ceds(
    save_dir='/work/bb1554/data/CEDS',
    species=['CO']
)

# Download MEIC sample data
cinei.download_meic_sample(
    save_dir='/work/bb1554/data/MEIC',
    months=['jan']
)
```

## Step 3: Check MEIC files
```python
result = cinei.check_meic_files(
    meic_dir='/work/bb1554/data/MEIC/MEIC201701_SPECIATED_NETCDF',
    year=2017,
    species=['CO'],
    months=[1]
)
print("Missing:", result['missing'])
```

## Step 4: Run integration
```python
output = cinei.emis_union(
    ceds_dir='/work/bb1554/data/CEDS',
    meic_dir='/work/bb1554/data/MEIC/MEIC201701_SPECIATED_NETCDF',
    save_dir='/work/bb1554/output/cinei',
    spec_ceds='CO',
    spec_meic='CO',
    mon='Jan', mon_id=0, mon_agg='01',
    year='2017',
    mapper_path='/work/bb1554/data/Integrated_mapper.csv',
    country_shp='/work/bb1554/data/shapefiles/country.shp',
    province_shp='/work/bb1554/data/shapefiles/province.shp',
    agg_dir='/work/bb1554/data/agg_sectors'
)
print("Output:", output)
```

## Step 5: Visualize
```python
fig = cinei.plot_emission_map(
    nc_file=output,
    variable='sum',
    title='CO Integrated Emissions — January 2017'
)
fig.savefig('CO_2017_Jan.png', dpi=150, bbox_inches='tight')
```

## Step 6: Grid area calculation
```python
import numpy as np
lat = np.arange(10.125, 60, 0.25)
lon = np.arange(70.125, 150, 0.25)
lon_2d, lat_2d = np.meshgrid(lon, lat)
area = cinei.ll_area(lat_2d, 0.25)
print(f"Grid area shape: {area.shape}")
```
