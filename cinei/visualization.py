"""Visualization tools for CINEI emission data."""
import matplotlib.pyplot as plt
import matplotlib.colors as colors
import xarray as xr
import numpy as np


def plot_emission_map(file_path, variable='sum', cmap='viridis',
                     figsize=(12, 8), title=None, save_path=None):
    """
    Plot a single emission variable from a CINEI NetCDF file.

    Parameters
    ----------
    file_path : str
        Path to the NetCDF file.
    variable : str, optional
        Variable to plot. Default: 'sum'.
    cmap : str, optional
        Matplotlib colormap. Default: 'viridis'.
    figsize : tuple, optional
        Figure size. Default: (12, 8).
    title : str, optional
        Plot title. Auto-generated if None.
    save_path : str, optional
        Path to save figure. If None, figure is displayed.

    Returns
    -------
    matplotlib.figure.Figure

    Examples
    --------
    >>> import cinei
    >>> fig = cinei.plot_emission_map(
    ...     '/data/output/CINEI_2017_Jan_NMVOC_0p25deg_China.nc',
    ...     variable='sum'
    ... )
    """
    ds = xr.open_dataset(file_path)

    if variable not in ds.data_vars:
        raise ValueError(
            f"[CINEI] Variable '{variable}' not found.\n"
            f"        Available: {list(ds.data_vars)}"
        )

    if title is None:
        title = f"Emission map: {variable} — {file_path.split('/')[-1]}"

    fig, ax = plt.subplots(figsize=figsize)

    data = ds[variable].values.copy()
    data = np.ma.masked_where(data <= 0, data)

    im   = ax.pcolormesh(ds.lon, ds.lat, data, cmap=cmap, shading='auto')
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label(ds.attrs.get('unit', 'Emission'))

    ax.set_xlabel('Longitude')
    ax.set_ylabel('Latitude')
    ax.set_title(title)
    ax.grid(True, linestyle='--', alpha=0.5)

    lon_range = ds.lon.values
    lat_range = ds.lat.values
    ax.set_xlim(lon_range.min(), lon_range.max())
    ax.set_ylim(lat_range.min(), lat_range.max())

    plt.tight_layout()

    if save_path is not None:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"[CINEI] Plot saved: {save_path}")

    ds.close()
    return fig


def cinei_plot(file_path, log_scale=True, cmap='YlOrRd',
               figsize=(18, 14), save_path=None,
               sectors=None, vmin=None, vmax_percentile=99):
    """
    Plot all emission sectors and total sum from a CINEI NetCDF file.

    Generates a 3×3 panel figure showing all 8 sectors plus total sum.
    Uses log scale by default for better visualization of emission patterns.

    Parameters
    ----------
    file_path : str
        Path to the CINEI output NetCDF file.
    log_scale : bool, optional
        Use logarithmic color scale. Default: True.
        Set False for linear scale.
    cmap : str, optional
        Matplotlib colormap. Default: 'YlOrRd'.
        Other good options: 'hot_r', 'plasma', 'magma'.
    figsize : tuple, optional
        Figure size in inches. Default: (18, 14).
    save_path : str, optional
        Path to save the figure (e.g. 'output.png').
        If None, figure is displayed interactively.
    sectors : list of str, optional
        Specific sectors to plot. Default: all available sectors.
        e.g. ['energy', 'transportation', 'sum']
    vmin : float, optional
        Minimum value for color scale. Default: 1 (log) or 0 (linear).
    vmax_percentile : int, optional
        Percentile for maximum color scale value. Default: 99.
        Useful to avoid outliers dominating the colorbar.

    Returns
    -------
    matplotlib.figure.Figure

    Examples
    --------
    >>> import cinei

    >>> # Plot all sectors with default settings
    >>> fig = cinei.cinei_plot(
    ...     '/data/output/CINEI_2017_Jan_NMVOC_0p25deg_China.nc'
    ... )

    >>> # Save to file with linear scale
    >>> fig = cinei.cinei_plot(
    ...     '/data/output/CINEI_2017_Jan_NMVOC_0p25deg_China.nc',
    ...     log_scale=False,
    ...     save_path='/data/output/CINEI_2017_Jan_NMVOC_sectors.png'
    ... )

    >>> # Plot specific sectors only
    >>> fig = cinei.cinei_plot(
    ...     '/data/output/CINEI_2017_Jan_NMVOC_0p25deg_China.nc',
    ...     sectors=['energy', 'transportation', 'industry', 'sum']
    ... )
    """
    ds = xr.open_dataset(file_path)

    # ── Determine sectors to plot ─────────────────────────────────────
    default_order = ['energy', 'residential', 'industry',
                     'agriculture', 'transportation', 'waste',
                     'shipping', 'aviation', 'sum']

    if sectors is None:
        plot_vars = [v for v in default_order if v in ds.data_vars]
        # Add any extra variables not in default order
        for v in ds.data_vars:
            if v not in plot_vars:
                plot_vars.append(v)
    else:
        invalid = [s for s in sectors if s not in ds.data_vars]
        if invalid:
            raise ValueError(
                f"[CINEI] Variables not found: {invalid}\n"
                f"        Available: {list(ds.data_vars)}"
            )
        plot_vars = sectors

    n_vars = len(plot_vars)
    n_cols = 3
    n_rows = int(np.ceil(n_vars / n_cols))

    # ── Build title from file attributes ─────────────────────────────
    title = ds.attrs.get('title', file_path.split('/')[-1])
    unit  = ds.attrs.get('unit', 'ton/month/grid')

    fig, axes = plt.subplots(n_rows, n_cols,
                             figsize=figsize,
                             constrained_layout=True)
    axes = np.array(axes).flatten()

    lon = ds.lon.values
    lat = ds.lat.values

    for idx, var in enumerate(plot_vars):
        ax   = axes[idx]
        data = ds[var].values.copy()
        data[data <= 0] = np.nan

        if np.all(np.isnan(data)):
            ax.set_title(f"{var}\n(all zero)", fontsize=11)
            ax.set_facecolor('#f0f0f0')
            ax.set_xlim(lon.min(), lon.max())
            ax.set_ylim(lat.min(), lat.max())
            ax.grid(True, linestyle='--', alpha=0.3)
            continue

        # ── Color scale ───────────────────────────────────────────────
        vmax = np.nanpercentile(data, vmax_percentile)
        if log_scale:
            _vmin = vmin if vmin is not None else 1.0
            _vmin = max(_vmin, np.nanmin(data[data > 0]))
            norm  = colors.LogNorm(vmin=_vmin, vmax=max(vmax, _vmin * 10))
        else:
            _vmin = vmin if vmin is not None else 0.0
            norm  = colors.Normalize(vmin=_vmin, vmax=vmax)

        # ── Plot ──────────────────────────────────────────────────────
        im = ax.pcolormesh(lon, lat, data,
                           norm=norm, cmap=cmap, shading='auto')

        cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        cbar.set_label(unit, fontsize=8)

        # ── Sector title with total ───────────────────────────────────
        total = np.nansum(ds[var].values)
        ax.set_title(
            f"{var}\n(total: {total:,.0f} {unit.split('/')[0]})",
            fontsize=10, fontweight='bold' if var == 'sum' else 'normal'
        )

        ax.set_xlim(lon.min(), lon.max())
        ax.set_ylim(lat.min(), lat.max())
        ax.set_xlabel('Lon', fontsize=8)
        ax.set_ylabel('Lat', fontsize=8)
        ax.tick_params(labelsize=7)
        ax.grid(True, linestyle='--', alpha=0.25, color='white')

    # ── Hide unused subplots ──────────────────────────────────────────
    for idx in range(len(plot_vars), len(axes)):
        axes[idx].set_visible(False)

    # ── Overall title ─────────────────────────────────────────────────
    scale_str = 'log scale' if log_scale else 'linear scale'
    fig.suptitle(f"{title}\n({scale_str})",
                 fontsize=13, fontweight='bold', y=1.01)

    # ── Save or show ──────────────────────────────────────────────────
    if save_path is not None:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"[CINEI] ✅ Plot saved: {save_path}")
    
    ds.close()
    return fig
