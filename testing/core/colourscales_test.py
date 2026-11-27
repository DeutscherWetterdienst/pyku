from copy import deepcopy

import matplotlib as mpl
import matplotlib.colors as mcolors
import numpy as np
import pytest

from pyku.core import colourscales
from pyku.core.colourscales import (
    PYKU_COLORMAPS,
    get_cmap,
    get_cmap_colors,
    get_cmap_scale_names,
    get_colormap,
    get_norm,
    register_all,
)
from pyku.core.resource_provider import PykuResourceProvider


def test_temp_abs_uses_zero_as_the_color_pivot() -> None:
    cmap, norm = get_colormap("temp_abs")

    assert norm(-0.01) < norm(0)
    assert mcolors.to_hex(cmap(norm(0))) == "#fff9cf"


def test_temp_abs_keeps_zero_pivot_with_non_dividing_step() -> None:
    cmap, norm = get_colormap("temp_abs", step=3)

    assert 0 in norm.boundaries
    assert mcolors.to_hex(cmap(norm(-0.01))) == "#cfdafe"
    assert mcolors.to_hex(cmap(norm(0))) == "#fff9cf"


@pytest.mark.parametrize(
    ("scale", "domain"),
    [
        ("default", (-4.5, 4.5)),
        ("yearly", (-7, 7)),
        ("monthly", (-12, 12)),
    ],
)
def test_temp_ano_scales_build_matching_cmap_norm_pairs(
    scale: str,
    domain: tuple[float, float],
) -> None:
    cmap, norm = get_colormap("temp_ano", scale=scale)

    assert (norm.boundaries[0], norm.boundaries[-1]) == domain
    assert norm.Ncmap == cmap.N
    assert cmap.colorbar_extend == "both"


def test_listed_pair_preserves_extensions_and_rejects_mismatched_bins() -> None:
    cmap, norm = get_colormap("temp_anp_ano")

    assert cmap.N == norm.Ncmap == 2
    assert cmap.colorbar_extend == "both"
    assert norm([-2, 0, 2]).tolist() == [-1, 1, 2]

    with pytest.raises(ValueError, match=r"14 listed colors.*27 bins"):
        get_colormap("temp_abs", kind="listed")


def test_explicit_nbins_overrides_configured_step() -> None:
    _, norm = get_colormap("temp_abs", nbins=5)

    assert len(norm.boundaries) == 6


def test_unknown_core_kind_aliases_are_rejected() -> None:
    for kind in ("original", "linear", "segmented"):
        with pytest.raises(ValueError, match="Supported names"):
            get_cmap("temp_abs", kind=kind)


def test_scale_names_list_only_configured_named_scales() -> None:
    assert get_cmap_scale_names("temp_ano") == ["monthly", "yearly"]
    assert get_cmap_scale_names("wind_abs") == []


def test_named_scale_lookups_do_not_mutate_fresh_resource_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resources = PykuResourceProvider()
    resources.clear_cache()
    monkeypatch.setattr(colourscales, "PYKU_RESOURCES", resources)

    palette_before = deepcopy(resources.get_value("base_colours", "temp_ano"))
    scales_before = deepcopy(resources.get_value("colour_scales", "temp_ano"))

    with pytest.raises(ValueError, match="Unknown scale 'yerly'"):
        get_cmap("temp_ano", scale="yerly")

    for scale in ("yearly", "monthly", "default"):
        get_colormap("temp_ano", scale=scale)

    assert resources.get_value("base_colours", "temp_ano") == palette_before
    assert resources.get_value("colour_scales", "temp_ano") == scales_before


def test_linear_segmented_colors_are_sampled_at_requested_resolution() -> None:
    colors = get_cmap_colors(
        "temp_abs",
        kind="linear_segmented",
        encoding="rgb",
        resolution=7,
    )

    assert len(colors) == 7
    assert all(len(color) == 3 for color in colors)


def test_colormap_registry_contains_cmap_norm_pairs() -> None:
    assert PYKU_COLORMAPS
    assert all("cmap" in entry for entry in PYKU_COLORMAPS.values())

    entry = PYKU_COLORMAPS["temp_anp_ano"]
    cmap, norm = entry["cmap"], entry["norm"]
    assert cmap.N == norm.Ncmap
    assert cmap.colorbar_extend == "both"


def test_get_norm_matches_named_scale_and_runtime_overrides() -> None:
    norm = get_norm("temp_ano", scale="yearly", step=2)
    _, paired_norm = get_colormap("temp_ano", scale="yearly", step=2)

    assert isinstance(norm, mcolors.BoundaryNorm)
    np.testing.assert_array_equal(norm.boundaries, paired_norm.boundaries)
    assert norm.boundaries[0] == -7
    assert norm.boundaries[-1] == 7


def test_register_all_registers_default_and_named_scales() -> None:
    prefix = "pyku_colourscales_test."
    registry_names = (
        f"{prefix}temp_ano",
        f"{prefix}temp_ano_yearly",
    )
    registered_names = [f"{prefix}{name}" for name in PYKU_COLORMAPS]
    try:
        register_all(prefix=prefix)

        assert all(name in mpl.colormaps for name in registry_names)
        np.testing.assert_allclose(
            mpl.colormaps[registry_names[0]](np.linspace(0, 1, 11)),
            PYKU_COLORMAPS["temp_ano"]["cmap"](np.linspace(0, 1, 11)),
        )
        np.testing.assert_allclose(
            mpl.colormaps[registry_names[1]](np.linspace(0, 1, 11)),
            PYKU_COLORMAPS["temp_ano_yearly"]["cmap"](np.linspace(0, 1, 11)),
        )

    finally:
        for name in registered_names:
            if name in mpl.colormaps:
                mpl.colormaps.unregister(name)
