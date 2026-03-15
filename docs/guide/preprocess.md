# Data Preprocessing

If you have your own emission data, CINEI provides tools to check and
standardize it into the required format before integration.

## CINEI Standard Format
```python
import cinei
cinei.show_cinei_standard()
```

| Property | Requirement |
|----------|-------------|
| Format | NetCDF (.nc) |
| Dimensions | `(month, lat, lon)` |
| Month | integer 1–12 |
| Units | ton/grid/month |
| Resolution | flexible (regridded to 0.25° in `emis_union`) |

## Required sector variables

| CINEI variable | CEDS input | MEIC input | HTAP/other |
|----------------|-----------|------------|------------|
| `power` | energy | power | — |
| `residential` | residential + solvents | residential | — |
| `industry` | industrial | industry | — |
| `transportation` | transportation | transportation | — |
| `agriculture` | agriculture | agriculture | — |
| `shipping` | ships | — | shipping |
| `waste` | — | — | waste |
| `aviation` | — | — | aviation |
| `sum` | computed automatically | | |

!!! note
    `sum` does **not** include aviation — consistent with CINEI v1 methodology.

## Step 1: Check your data
```python
import cinei

# Check a NetCDF file
report = cinei.check_user_data('/path/to/my_emission.nc')
print(report['status'])   # 'ok', 'warning', or 'error'
print(report['issues'])
print(report['suggestions'])

# Check a txt/csv file
report = cinei.check_user_data('/path/to/my_emission.txt')
```

## Step 2: Standardize NetCDF
```python
# Auto-standardize (fixes dims and sector names automatically)
out = cinei.standardize_netcdf('/path/to/my_emission.nc')

# With manual sector mapping (when auto-detection fails)
out = cinei.standardize_netcdf(
    '/path/to/my_emission.nc',
    sector_mapping={
        'agr_emis':  'agriculture',
        'ind_emis':  'industry',
        'pow_emis':  'power',
        'res_emis':  'residential',
        'tra_emis':  'transportation',
        'shp_emis':  'shipping',
    }
)
```

!!! tip
    Missing sectors are automatically filled with zeros.
    The `sum` variable is always recomputed from all available sectors.

## Step 3: Convert txt to NetCDF
```python
# Auto-convert (column names auto-detected)
out = cinei.txt_to_netcdf('/path/to/my_emission.txt')

# With manual column mapping
out = cinei.txt_to_netcdf(
    '/path/to/my_emission.txt',
    lat_col='latitude',
    lon_col='longitude',
    month_col='mon',
    sector_cols={
        'agr': 'agriculture',
        'ind': 'industry',
        'pow': 'power',
        'res': 'residential',
        'tra': 'transportation',
    }
)
```

Expected txt format:
```
lat    lon     month  agr     ind     pow     res     tra
10.05  70.05   1      0.12    0.45    0.33    0.21    0.67
10.05  70.05   2      0.11    0.44    0.31    0.20    0.65
...
```

## Accepted sector name aliases

CINEI automatically maps common alternative names:

| CINEI standard | Accepted aliases |
|---------------|-----------------|
| `agriculture` | agr, agri, act, agricultural |
| `industry` | ind, idt, industrial, manufacturing |
| `power` | pwr, ene, energy, electricity |
| `residential` | res, rdt, domestic, household |
| `transportation` | tra, tpt, transport, road, traffic |
| `shipping` | shp, ship, marine |
| `waste` | wst, swd, solid_waste |
| `aviation` | avi, air, aircraft |
| `sum` | total, tot, all, anthro |
