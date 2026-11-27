#!/usr/bin/env python3
"""Deprecated compatibility wrappers for :mod:`pyku.core.colourscales`."""

import warnings
from typing import Any

from matplotlib import colors as mcolors
from matplotlib.colors import Colormap

from pyku.core import colourscales as _colourscales

_LEGACY_KINDS = {
    "original": "listed",
    "linear": "linear_segmented",
    "segmented": "from_levels",
}


def _warn_deprecated(api_name: str, replacement: str) -> None:
    warnings.warn(
        f"pyku.colormaps.{api_name} is deprecated and will be removed in a "
        f"future version. Use {replacement} instead.",
        DeprecationWarning,
        stacklevel=3,
    )


def _legacy_kind_options(
    kind: str,
    nbins: int | None,
) -> tuple[str, dict[str, Any]]:
    canonical_kind = _LEGACY_KINDS.get(kind, kind)
    options: dict[str, Any] = {}

    if kind == "segmented":
        if nbins is None:
            raise ValueError("nbins must be specified when kind='segmented'.")
        options.update(
            domain=(0.0, 1.0),
            nbins=nbins,
            extend="neither",
        )
    elif nbins is not None:
        options["nbins"] = nbins

    return canonical_kind, options


def _legacy_segmented_cmap(
    name: str,
    nbins: int | None,
) -> Colormap:
    if nbins is None:
        raise ValueError("nbins must be specified when kind='segmented'.")

    import numpy as np

    cmap = _colourscales.get_cmap(name, kind="linear_segmented")
    if isinstance(cmap, mcolors.ListedColormap):
        return cmap
    colors = cmap(np.linspace(0.0, 1.0, nbins))
    return mcolors.ListedColormap(colors, name=name)


def get_colormaps_names() -> list[str]:
    """Return colormap names.

    Deprecated
    ----------
    Use :func:`pyku.core.colourscales.get_cmap_names` instead.
    """
    _warn_deprecated(
        "get_colormaps_names",
        "pyku.core.colourscales.get_cmap_names",
    )
    return _colourscales.get_cmap_names()


def get_cmap_colors(
    name: str,
    kind: str = "original",
    nbins: int | None = None,
    encoding: str = "hex",
) -> list[Any]:
    """Return colors for a colormap.

    Deprecated
    ----------
    Use :func:`pyku.core.colourscales.get_cmap_colors` instead.

    Parameters
    ----------
    name : str
        Colormap name.
    kind : str, default "original"
        Legacy colormap kind.
    nbins : int, optional
        Number of bins for ``kind="segmented"``.
    encoding : str, default "hex"
        Color encoding, either ``"hex"`` or ``"rgb"``.

    Returns
    -------
    list
        Colors in the requested encoding.
    """
    _warn_deprecated(
        "get_cmap_colors",
        "pyku.core.colourscales.get_cmap_colors",
    )
    if kind == "segmented":
        cmap = _legacy_segmented_cmap(name, nbins)
        if encoding == "rgb":
            return list(cmap.colors)
        if encoding == "hex":
            return [mcolors.to_hex(color) for color in cmap.colors]
        raise ValueError(f"encoding should be 'hex' or 'rgb', not {encoding}")

    canonical_kind, options = _legacy_kind_options(kind, nbins)
    return _colourscales.get_cmap_colors(
        name,
        kind=canonical_kind,
        encoding=encoding,
        **options,
    )


def get_cmap(
    name: str,
    kind: str = "original",
    nbins: int | None = None,
) -> Colormap:
    """Return a colormap.

    Deprecated
    ----------
    Use :func:`pyku.core.colourscales.get_cmap` instead.

    Parameters
    ----------
    name : str
        Colormap name.
    kind : str, default "original"
        Legacy colormap kind.
    nbins : int, optional
        Number of bins for ``kind="segmented"``.

    Returns
    -------
    matplotlib.colors.Colormap
        The constructed colormap.
    """
    _warn_deprecated("get_cmap", "pyku.core.colourscales.get_cmap")
    if kind == "segmented":
        return _legacy_segmented_cmap(name, nbins)

    canonical_kind, options = _legacy_kind_options(kind, nbins)
    return _colourscales.get_cmap(name, kind=canonical_kind, **options)


def plot_colormaps(
    kind: str = "linear",
    nbins: int | None = None,
) -> None:
    """Plot all configured colormaps.

    Deprecated
    ----------
    Use :func:`pyku.core.colourscales.get_cmap` to build colormaps directly.

    Parameters
    ----------
    kind : str, default "linear"
        Legacy colormap kind.
    nbins : int, optional
        Number of bins for ``kind="segmented"``.
    """
    import matplotlib.pyplot as plt
    import numpy as np

    _warn_deprecated("plot_colormaps", "pyku.core.colourscales")
    gradient = np.linspace(0, 1, 256)
    gradient = np.vstack((gradient, gradient))
    canonical_kind, options = _legacy_kind_options(kind, nbins)
    if kind == "segmented":
        cmaps = {
            name: _legacy_segmented_cmap(name, nbins)
            for name in _colourscales.get_cmap_names()
        }
    else:
        cmaps = {
            name: _colourscales.get_cmap(
                name,
                kind=canonical_kind,
                **options,
            )
            for name in _colourscales.get_cmap_names()
        }

    plt.rcParams["savefig.bbox"] = "tight"
    nrows = len(cmaps)
    figure_height = 0.35 + 0.15 + (nrows + (nrows - 1) * 0.1) * 0.22
    _, axes = plt.subplots(nrows=nrows + 1, figsize=(6.4, figure_height))
    plt.subplots_adjust(
        top=1 - 0.35 / figure_height,
        bottom=0.15 / figure_height,
        left=0.2,
        right=0.99,
    )
    axes[0].set_title("DWD colormaps", fontsize=14)

    for axis, (name, cmap) in zip(axes, cmaps.items(), strict=False):
        axis.imshow(gradient, aspect="auto", cmap=cmap)
        axis.text(
            -0.01,
            0.5,
            name,
            va="center",
            ha="right",
            fontsize=10,
            transform=axis.transAxes,
        )

    for axis in axes:
        axis.set_axis_off()
