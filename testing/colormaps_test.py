import matplotlib.colors as mcolors
import numpy as np
import pytest

from pyku import colormaps as legacy_colormaps
from pyku.core import PYKU_RESOURCES
from pyku.core.colourscales import get_cmap


def test_legacy_colormap_api_warns_and_uses_core_builder() -> None:
    with pytest.warns(DeprecationWarning, match="pyku.colormaps.get_cmap"):
        legacy_cmap = legacy_colormaps.get_cmap("temp_abs", kind="linear")

    core_cmap = get_cmap("temp_abs", kind="linear_segmented")

    assert isinstance(legacy_cmap, mcolors.LinearSegmentedColormap)
    np.testing.assert_allclose(
        legacy_cmap(np.linspace(0.0, 1.0, 11)),
        core_cmap(np.linspace(0.0, 1.0, 11)),
    )


def test_legacy_segmented_colors_preserve_matplotlib_sampling() -> None:
    with pytest.warns(DeprecationWarning):
        colors = legacy_colormaps.get_cmap_colors(
            "temp_abs",
            kind="segmented",
            nbins=2,
        )

    assert colors == ["#30123b", "#7a0402"]


def test_legacy_segmented_plot_uses_legacy_sampling() -> None:
    import matplotlib.pyplot as plt

    existing_figures = set(plt.get_fignums())
    try:
        with pytest.warns(DeprecationWarning):
            legacy_colormaps.plot_colormaps(kind="segmented", nbins=2)

        new_figures = set(plt.get_fignums()) - existing_figures
        assert len(new_figures) == 1
        figure = plt.figure(new_figures.pop())
        temp_abs_axis = next(
            axis
            for axis in figure.axes
            if any(text.get_text() == "temp_abs" for text in axis.texts)
        )
        cmap = temp_abs_axis.images[0].get_cmap()

        assert [mcolors.to_hex(color) for color in cmap.colors] == [
            "#30123b",
            "#7a0402",
        ]
    finally:
        for figure_number in set(plt.get_fignums()) - existing_figures:
            plt.close(figure_number)


def test_legacy_colormap_names_warn_and_delegate() -> None:
    with pytest.warns(
        DeprecationWarning,
        match="pyku.colormaps.get_colormaps_names",
    ):
        legacy_names = legacy_colormaps.get_colormaps_names()

    assert legacy_names == sorted(PYKU_RESOURCES.get_keys("base_colours"))
