# Quick Start

## Check available download functions
```python
import cinei

# List available CEDS species
cinei.list_ceds_species()

# List available EDGAR species
cinei.list_edgar_species()

# List HTAP files
cinei.list_htap_files(resolution='05x05')
```

## Download emission data
```python
# Download CEDS CO data
cinei.download_ceds(
    save_dir='/work/b123456/data/CEDS',
    species=['CO']
)

# Download EDGAR NOx for 2017
cinei.download_edgar(
    save_dir='/work/b123456/data/EDGAR',
    species=['NOx'],
    years=[2017]
)

# Download HTAP SO2 monthly for July 2017
cinei.download_htap_monthly(
    save_dir='/work/b123456/data/HTAP',
    species=['SO2'],
    year=2017,
    month=7
)
```

## Run emission integration
```python
output = cinei.emis_union(
    ceds_dir='/work/b123456/data/CEDS',
    meic_dir='/work/b123456/data/MEIC/2017',
    save_dir='/work/b123456/output/cinei',
    spec_ceds='NOx',
    spec_meic='NOx',
    mon='Jan', mon_id=0, mon_agg='01',
    year='2017',
    mapper_path='/work/b123456/data/Integrated_mapper.csv',
    country_shp='/work/b123456/data/shapefiles/country.shp',
    province_shp='/work/b123456/data/shapefiles/province.shp',
    agg_dir='/work/b123456/data/agg_sectors'
)
```
