#!/usr/bin/env python3

"""
Reference implementation of DWD color maps
"""

# Load metadata at module initialization
# --------------------------------------

import importlib
import yaml
from . import logger

# Load metadata at module initialization
# --------------------------------------

base_colours_file = importlib.resources.files(
    'pyku.etc') / 'base_colours.yaml'


with open(base_colours_file) as f:
    base_colours = yaml.safe_load(f)


def get_colormaps_names():

    """
    Get the name of all available colormaps

    Returns:
        List[str]: List of the names of all available colormaps

    Example:

        .. ipython::
           :okwarning:

           In [0]: import pyku.colormaps as colormaps
              ...: colormaps.get_colormaps_names()
    """

    return list(base_colours.keys())


def get_cmap_colors(name, kind='original', nbins=None, encoding='hex'):

    """
    Get cmap colors

    Arguments:
        name (str): name of the colormap
        kind (str): Defaults to linear. One of {`original`, `segmented`}
        nbins (int): Number of bins for segmented color maps
        encoding (str): Encoding. Default to 'hex'. One of {'hex', 'rgb'}

    Returns:
        List: If encoding is 'rgb', return a list of red, green and blue
            tuples. If encoding is 'rgb', return a list of hex.

    Example:

        .. ipython::
           :okwarning:

           In [0]: import pyku.colormaps as colormaps
              ...: colormaps.get_cmap_colors(
              ...:     'temp_ano',
              ...:     kind='segmented',
              ...:     nbins=10,
              ...:     encoding='hex'
              ...:  )
    """

    import matplotlib.colors as mcolors

    if encoding in ['rgb']:
        return get_cmap(name, kind=kind, nbins=nbins).colors

    elif encoding in ['hex']:
        rgb_tuples = get_cmap(name, kind=kind, nbins=nbins).colors
        hex_colors = [mcolors.to_hex(rgb) for rgb in rgb_tuples]
        return hex_colors

    else:
        message = f"encoding should be 'rgb' or 'hex', not {encoding}"
        raise Exception(message)


def get_cmap(name, kind='original', nbins=None):

    """
    Get cmap

    Arguments:
        name (str): name of the colormap
        kind (str): Defaults to linear. One of {`original`, `linear`,
            `segmented`}
        nbins (int): Number of bins for segmented color maps

    Returns:
        :class:`matplotlib.colors.Colormap`: The colormap.

    Example:

        .. ipython::
           :okwarning:

           In [0]: import pyku.colormaps as colormaps
              ...: cmap = colormaps.get_cmap('temp_ano')
    """

    import numpy as np
    import matplotlib.pyplot as plt
    import matplotlib.colors as mcolors

    # Check inputs, send warnings and raise Exceptions
    # ------------------------------------------------

    if kind not in ['original', 'linear', 'segmented']:
        message = (
            f"kind {kind} not implemented. kind should be one of 'original'",
            "'linear', or 'segmented'"
        )
        raise Exception(message)

    if nbins is not None and kind in ['linear', 'original']:
        message = f"Option nbins is ignored when used with kind='{kind}'"
        logger.warn(message)

    if nbins is None and kind in ['segmented']:
        message = f"Option nbins shall passed when using kin='{kind}'"
        raise Exception(message)

    if name not in get_colormaps_names():
        message = (
            f"color map {name} not defined. "
            f"Available colormaps are {get_colormaps_names()}"
        )
        raise Exception(message)

    # Special cases
    # -------------

    if '_anp_abs' in name and kind not in ['original']:
        logger.info(f"{name} always has kind='original', forcing.")
        kind = 'original'

    if '_anp_ano' in name and kind not in ['original']:
        logger.info(f"{name} always has kind='original', forcing.")
        kind = 'original'

    if '_nnp' in name and '_nnp_cat' not in name and kind not in ['original']:
        logger.info(f"{name} always has kind='original', forcing.")
        kind = 'original'

    if '_nnp_cat' in name and kind not in ['original']:
        logger.info(f"{name} always has kind='original', forcing.")
        kind = 'original'

    if name in ['HZ_abs', 'HZ_ano', 'WHZ_abs', 'WHZ_ano']:
        logger.info(f"{name} always has kind='original', forcing.")
        kind = 'original'

    if '_ano' in name and kind in ['segmented'] and (nbins % 2 == 0):
        logger.info(
            f"Using an even number of bins with colormap {name}. "
            "Please check if this is correct before supressing this warning."
        )

    if name in ['pressure_abs'] and kind in ['segmented'] and (nbins % 2 == 0):
        logger.info(
            f"Using an even number of bins with colormap {name}. "
            "Please check if this is correct before supressing this warning."
        )

    if name in ['KV_skill'] and kind not in ['original']:
        logger.info(f"{name} always has kind='original', forcing.")
        kind = 'original'

    # Get colors defined in configuration both as hex and convert to RGB
    # ------------------------------------------------------------------

    hex_colors = base_colours.get(name).get('colours_hex')
    rgb_colors = [mcolors.hex2color(color) for color in hex_colors]

    # Get linear colormap
    # -------------------

    if kind in ['linear']:

        # Edge case
        # ---------

        # Some color maps contain only one color (e.g., bar chart with absolute
        # values). When trying to create a linear color map, this single color
        # needs to be duplicated.

        if len(rgb_colors) == 1:
            rgb_colors = [rgb_colors[0], rgb_colors[0]]

        cmap = mcolors.LinearSegmentedColormap.from_list(name, rgb_colors)

    # Get segmented colormap directly from configuration
    # --------------------------------------------------

    elif kind in ['original']:
        cmap = mcolors.ListedColormap(rgb_colors)

    # Get re-segmented colormap
    # -------------------------

    elif kind in ['segmented']:

        # Edge case
        # ---------

        # Some color maps contain only one color (e.g., bar chart with absolute
        # values). When trying to create a segmented color map, this single
        # color needs to be duplicated.

        if len(rgb_colors) == 1:
            rgb_colors = [rgb_colors[0], rgb_colors[0]]

        # Create a linear colormap from the original colors
        # -------------------------------------------------

        # A linear colormap is created in order to be able to split it
        # with the right number of bins

        cmap = mcolors.LinearSegmentedColormap.from_list(name, rgb_colors)

        # Create bins for the colormap
        # ----------------------------

        bounds = np.linspace(0, 1, nbins)

        # Create a colormap with specified bins
        # -------------------------------------

        norm = plt.Normalize(vmin=0, vmax=1)

        segmented_colors = [cmap(norm(value)) for value in bounds]

        cmap = plt.cm.colors.ListedColormap(segmented_colors)

    return cmap


def plot_colormaps(kind='linear', nbins=None):

    """
    Plot all available colormaps

    Arguments:
        kind (str): Defaults to linear. One of {`original`, `linear`,
            `segmented`}
        nbins (int): Number of bins for segmented color maps

    Example:

        .. ipython::
           :okwarning:

           @savefig plot_colormaps.png width=5in
           In [0]: import pyku.colormaps as colormaps
              ...:
              ...: colormaps.plot_colormaps(kind='original')
    """

    import matplotlib.pyplot as plt
    import numpy as np

    # Set tight parameter when saving figures
    # ---------------------------------------

    plt.rcParams['savefig.bbox'] = 'tight'

    # Check inputs, send warnings and raise Exceptions
    # ------------------------------------------------

    if kind not in ['original', 'linear', 'segmented']:
        message = f"\
kind {kind} not implemented. kind should be one of 'original', 'linear', or \
'segmented'"

    if nbins is not None and kind in ['linear', 'original']:
        message = f"Option nbins is ignored when used with type={type}"
        logger.warn(message)

    if nbins is None and kind in ['segmented']:
        message = f"Option nbins shall passed when using type={type}"
        raise Exception(message)

    gradient = np.linspace(0, 1, 256)
    gradient = np.vstack((gradient, gradient))

    def plot_color_gradients(cmaps_dict):

        # Create figure and adjust figure height to number of colormaps
        # -------------------------------------------------------------

        nrows = len(cmaps_dict.keys())
        figh = 0.35 + 0.15 + (nrows + (nrows - 1) * 0.1) * 0.22
        fig, axs = plt.subplots(nrows=nrows + 1, figsize=(6.4, figh))
        fig.subplots_adjust(top=1 - 0.35 / figh, bottom=0.15 / figh,
                            left=0.2, right=0.99)
        axs[0].set_title('DWD colormaps', fontsize=14)

        for ax, (name, cmap) in zip(axs, cmaps_dict.items()):
            ax.imshow(gradient, aspect='auto', cmap=cmap)
            ax.text(-0.01, 0.5, name, va='center', ha='right', fontsize=10,
                    transform=ax.transAxes)

        # Turn off *all* ticks & spines, not just the ones with colormaps
        # ---------------------------------------------------------------

        for ax in axs:
            ax.set_axis_off()

    cmaps_dict = {
        name: get_cmap(name, kind=kind, nbins=nbins)
        for name in get_colormaps_names()
    }

    plot_color_gradients(cmaps_dict)
