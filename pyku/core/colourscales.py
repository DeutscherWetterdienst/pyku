#!/usr/bin/env python3
"""
Reference implementation of DWD color maps.
"""

import logging
from dataclasses import dataclass
from typing import Any, NamedTuple

from matplotlib import colors as mcolors

from pyku.core import PYKU_RESOURCES

logger = logging.getLogger(__name__)

_VALID_KINDS = ("auto", "listed", "linear_segmented", "from_levels")
_VALID_EXTENDS = ("neither", "min", "max", "both")

# Colormaps that must always use kind='listed'
_FORCE_LISTED_SUBSTRINGS = (
    "_anp_abs",
    "_anp_ano",
    "_nnp",
    "HZ_abs",
    "HZ_ano",
    "WHZ_abs",
    "WHZ_ano",
    "KV_skill",
)

# Colormaps that log a warning when an even number of bins is used
_WARN_EVEN_BINS_SUBSTRINGS = (
    "_ano",
    "pressure_abs",
)


# MATPLOTLIB_KIND_NAMES = {
#  'auto': 'configured default from metadata',
#  'listed': 'matplotlib.colors.ListedColormap',
#  'linear_segmented': 'matplotlib.colors.LinearSegmentedColormap.from_list',
#  'from_levels': 'matplotlib.colors.from_levels_and_colors (+ BoundaryNorm)',
# }


def validate_kind(
    kind: str,
) -> str:
    """Validate and return a canonical colormap kind."""
    if kind not in _VALID_KINDS:
        supported = ", ".join(_VALID_KINDS)
        raise ValueError(
            f"kind '{kind}' not implemented. Supported names: {supported}"
        )
    return kind


def _resolve_cmap_name(name):
    """pyku cmap naming should be possible with or without the 'pyku.'
    prefix."""
    if name.startswith("pyku."):
        return name[5:]
    return name


def _to_rgb_colors(hex_colors):
    import matplotlib.colors as mcolors

    return [mcolors.hex2color(color) for color in hex_colors]


def _duplicate_single_color(rgb_colors):
    if len(rgb_colors) == 1:
        return [rgb_colors[0], rgb_colors[0]]
    return rgb_colors


def _compute_boundaries(params):
    """Compute bin boundaries from resolved colormap parameters."""
    import numpy as np

    if params.boundaries is not None:
        return np.array(params.boundaries, dtype=np.float64)

    vmin, vmax = params.domain
    skew = params.skew
    step = params.step
    split_index = params.split_index
    nbins = params.nbins

    if step is not None:
        if skew is not None and (vmin < skew < vmax) and split_index is None:
            origin = skew - (step / 2.0)
            k_min = int(np.floor((vmin - origin) / step))
            k_max = int(np.ceil((vmax - origin) / step))
            raw = origin + np.arange(k_min, k_max + 1) * step
            inner = raw[(raw > vmin + 1e-9) & (raw < vmax - 1e-9)]
            boundaries = np.concatenate([[vmin], inner, [vmax]])
        elif skew is not None and (vmin < skew < vmax):
            lower = np.arange(vmin, skew + step * 0.5, step)
            lower = lower[lower <= skew + 1e-9]
            if not np.isclose(lower[-1], skew):
                lower = np.append(lower, skew)
            upper = np.arange(skew + step, vmax + step * 0.5, step)
            upper = upper[upper <= vmax + 1e-9]
            if len(upper) == 0 or not np.isclose(upper[-1], vmax):
                upper = np.append(upper, vmax)
            boundaries = np.concatenate([lower, upper])
        else:
            boundaries = np.arange(vmin, vmax + step * 0.5, step)
            boundaries = boundaries[boundaries <= vmax + 1e-9]
            if not np.isclose(boundaries[-1], vmax):
                boundaries = np.append(boundaries, vmax)
    elif skew is not None and (vmin < skew < vmax):
        n_lower = round(nbins * (skew - vmin) / (vmax - vmin))
        n_lower = min(max(1, n_lower), nbins - 1)
        n_upper = nbins - n_lower
        boundaries = np.concatenate(
            [
                np.linspace(vmin, skew, n_lower + 1),
                np.linspace(skew, vmax, n_upper + 1)[1:],
            ]
        )
    else:
        boundaries = np.linspace(vmin, vmax, nbins + 1)

    return boundaries


def _normalize_anchor_split(name, rgb_colors, split_index):
    """Split anchor colors into lower and upper segments.

    The explicit split index is treated as a pivot between the lower and upper
    color groups. If it is invalid, the split falls back to the midpoint.
    """
    import numpy as np

    n_colors = len(rgb_colors)
    valid_split_index = False

    if split_index is not None:
        if not isinstance(split_index, (int, np.integer)):
            logger.warning(
                "For colormap %s, split_index=%s is invalid. Expected an "
                "integer split position. Falling back to midpoint split.",
                name,
                split_index,
            )
        else:
            split_index = int(split_index)
            if not (1 <= split_index < n_colors):
                logger.warning(
                    "For colormap %s, split_index=%s must be inside [1, %s]. "
                    "Falling back to midpoint split.",
                    name,
                    split_index,
                    n_colors - 1,
                )
            else:
                valid_split_index = True

    if valid_split_index:
        return rgb_colors[:split_index], rgb_colors[split_index:], True

    midpoint = n_colors // 2
    if n_colors % 2 == 1:
        return rgb_colors[: midpoint + 1], rgb_colors[midpoint:], False
    return rgb_colors[:midpoint], rgb_colors[midpoint:], False


def _build_segmented_pair(name, rgb_colors, params):
    """Build the ``(cmap, norm)`` pair used by segmented colormaps."""
    import matplotlib.colors as mcolors
    import numpy as np

    if params.domain is None:
        raise ValueError(
            f"get_norm: colormap '{name}' requires a domain. "
            "Pass domain=[vmin, vmax] or set it in the colormap defaults."
        )
    if params.nbins is None:
        raise ValueError(
            f"get_norm: colormap '{name}' requires nbins or step. "
            "Pass nbins=N (or step=S) or set it in the colormap defaults."
        )

    boundaries = _compute_boundaries(params)
    n_bins = len(boundaries) - 1

    rgb_colors = _duplicate_single_color(rgb_colors)
    split_index = params.split_index
    skew = params.skew
    domain = params.domain

    lower_rgb, upper_rgb, valid_split_index = _normalize_anchor_split(
        name, rgb_colors, split_index
    )

    if len(lower_rgb) == 1:
        lower_rgb = [lower_rgb[0], lower_rgb[0]]
    if len(upper_rgb) == 1:
        upper_rgb = [upper_rgb[0], upper_rgb[0]]

    if domain is not None and skew is not None and domain[0] < skew < domain[1]:
        n_lower = int(np.sum(np.asarray(boundaries[:-1]) < skew - 1e-9))
        n_lower = min(max(1, n_lower), n_bins - 1)
        n_upper = n_bins - n_lower
        segmented_colors = _interpolate_segmented_colors(lower_rgb, n_lower)
        segmented_colors += _interpolate_segmented_colors(upper_rgb, n_upper)
    elif valid_split_index:
        n_lower = round(
            n_bins * len(lower_rgb) / (len(lower_rgb) + len(upper_rgb))
        )
        if n_bins > 1:
            n_lower = min(max(1, n_lower), n_bins - 1)
        n_upper = n_bins - n_lower
        segmented_colors = _interpolate_segmented_colors(lower_rgb, n_lower)
        segmented_colors += _interpolate_segmented_colors(upper_rgb, n_upper)
    else:
        if skew is not None and domain is None:
            logger.warning(
                "For colormap %s, skew is set but domain is missing. "
                "Falling back to uniform interpolation.",
                name,
            )
        segmented_colors = _interpolate_segmented_colors(rgb_colors, n_bins)

    extend = params.extend
    if extend in ("min", "both"):
        segmented_colors = [segmented_colors[0]] + list(segmented_colors)
    if extend in ("max", "both"):
        segmented_colors = list(segmented_colors) + [segmented_colors[-1]]

    cmap, norm = mcolors.from_levels_and_colors(
        boundaries, segmented_colors, extend=extend
    )

    if params.center is not None:
        norm = CenterOutBoundaryNorm(
            boundaries=boundaries,
            ncolors=cmap.N,
            center=params.center,
            clip=getattr(norm, "clip", False),
        )

    return cmap, norm


@dataclass(frozen=True)
class ColormapConfig:
    """Immutable view on one colormap configuration entry."""

    name: str
    raw: dict[str, Any]

    @classmethod
    def from_mapping(
        cls,
        name: str,
        mapping: dict[str, Any],
    ) -> "ColormapConfig":
        return cls(name=name, raw=dict(mapping))

    @property
    def defaults(self):
        return dict(self.raw.get("defaults", {}))

    @property
    def colours_hex(self):
        return tuple(self.raw.get("colours_hex", ()))

    @property
    def labels(self):
        return self.raw.get("labels")

    @property
    def names(self):
        return self.raw.get("names")

    def get(self, key, default=None):
        return self.raw.get(key, default)

    def get_default(self, key, default=None):
        return self.defaults.get(key, default)

    def effective_kind(self, requested_kind="auto"):
        requested_kind = validate_kind(requested_kind)
        if requested_kind == "auto":
            configured_kind = self.raw.get(
                "kind", self.defaults.get("kind", "listed")
            )
            return validate_kind(configured_kind)
        return requested_kind

    def cmap(self, kind="auto", **kwargs):
        return ColormapBuilder(self, kind=kind, **kwargs).build_cmap()

    def norm(self, **kwargs):
        return ColormapBuilder(self, kind="from_levels", **kwargs).build_norm()

    def resolve_params(
        self,
        requested_kind: str = "auto",
        **kwargs: Any,
    ) -> "ResolvedParams":
        """Resolve runtime parameters for this colormap."""
        requested_kind = validate_kind(requested_kind)
        defaults = self.defaults
        domain = kwargs.get("domain", defaults.get("domain"))
        skew = kwargs.get("skew", defaults.get("skew"))
        split_index = kwargs.get("split_index", defaults.get("split_index"))
        nbins = kwargs.get("nbins", defaults.get("nbins"))
        step = kwargs.get("step", defaults.get("step"))
        if "nbins" in kwargs and "step" not in kwargs:
            step = None
        extend = validate_extend(
            kwargs.get("extend", defaults.get("extend", "neither"))
        )

        # Explicit boundaries kwarg always wins.
        # A YAML-default boundaries is only used when the caller has not
        # supplied any of step/nbins/boundaries themselves, so that passing
        # e.g. step=1.0 still overrides the default boundaries.
        caller_supplied_bounds = "boundaries" in kwargs
        caller_supplied_step = "step" in kwargs or "nbins" in kwargs
        if caller_supplied_bounds:
            boundaries = kwargs["boundaries"]
        elif caller_supplied_step:
            boundaries = None
        else:
            boundaries = defaults.get("boundaries")

        if boundaries is not None:
            # Explicit boundaries override all step/nbins/skew logic.
            # domain is derived from the boundary edges if not supplied.
            if domain is None:
                domain = [boundaries[0], boundaries[-1]]
            nbins = len(boundaries) - 1
            step = None
            skew = None
        elif domain is not None:
            nbins, skew = _resolve_nbins(
                domain, nbins=nbins, step=step, skew=skew
            )

        kind = self.effective_kind(requested_kind)

        return ResolvedParams(
            kind=kind,
            domain=domain,
            skew=skew,
            nbins=nbins,
            step=step,
            split_index=split_index,
            extend=extend,
            boundaries=boundaries,
            center=kwargs.get("center", defaults.get("center")),
        )


def _get_config(name: str, scale: str = "default") -> ColormapConfig:
    """Get ColormapConfig for name."""
    name = _resolve_cmap_name(name)
    raw = dict(PYKU_RESOURCES.get_value("base_colours", name))
    scales = PYKU_RESOURCES.get_value("colour_scales", name, default={})
    if scale != "default" and (
        not isinstance(scales, dict) or scale not in scales
    ):
        available = (
            sorted(key for key in scales if key != "default")
            if isinstance(scales, dict)
            else []
        )
        scale_names = ", ".join(["default", *available])
        raise ValueError(
            f"Unknown scale '{scale}' for colormap '{name}'. "
            f"Available scales: {scale_names}"
        )
    raw_scale = scales.get(scale, {}) if isinstance(scales, dict) else {}
    if raw_scale:
        raw["defaults"] = dict(raw_scale)
    return ColormapConfig.from_mapping(name, raw)


def _get_scale_names(
    name: str,
) -> tuple[str, ...]:
    """Return all configured scale names for a colormap."""
    name = _resolve_cmap_name(name)
    scales = PYKU_RESOURCES.get_value("colour_scales", name, default={})
    if not isinstance(scales, dict):
        return ()
    return tuple(scale for scale in scales.keys() if scale != "default")


def _registry_name(name, scale):
    """Build the public registry name for a colormap/scale pair."""
    if scale == "default":
        return name
    return f"{name}_{scale}"


def _build_registry_entry(name: str, scale: str) -> dict[str, Any]:
    """Build one registry entry, keeping cmap registration unconditional."""
    config = _get_config(name, scale=scale)
    builder = ColormapBuilder(config, kind="auto")
    params = builder.resolve_params()
    if params.domain is None:
        cmap = builder.build_cmap()
        norm = None
    else:
        cmap, norm = _build_colormap_pair(builder, params)
    return {"cmap": cmap, "norm": norm}


def get_cmap_names() -> list[str]:
    """Return the names of all available colormaps.

    Examples
    --------
    .. ipython::
       :okwarning:

       In [1]: from pyku.core.colourscales import get_cmap_names
          ...: names = get_cmap_names()
          ...: len(names), names[:5]
    """
    return sorted(PYKU_RESOURCES.get_keys("base_colours"))


def get_cmap_scale_names(
    name: str,
) -> list[str]:
    """Return explicitly configured named scales for a colormap.

    The implicit ``default`` scale is available to lookups but is not listed.
    Colormaps without additional named scales return an empty list.

    Parameters
    ----------
    name : str
        Colormap name, with or without the ``pyku.`` prefix.

    Returns
    -------
    list of str
        Explicitly configured scale names, such as ``yearly`` and ``monthly``.

    Examples
    --------
    .. ipython::

       In [1]: from pyku.core.colourscales import get_cmap_scale_names
          ...: get_cmap_scale_names("temp_ano")
    """
    name = _resolve_cmap_name(name)
    scales = PYKU_RESOURCES.get_value("colour_scales", name, default={})
    if not isinstance(scales, dict):
        return []
    return sorted(scale for scale in scales if scale != "default")


def get_cmap_colors(
    name: str,
    kind: str = "listed",
    encoding: str = "hex",
    scale: str = "default",
    resolution: int = 256,
    **kwargs: Any,
) -> list[Any]:
    """Return colormap colors in hex or RGB encoding.

    Continuous colormaps are sampled evenly at ``resolution`` points.
    Use :func:`get_colormap` when a matching colormap and normalization are
    needed for plotting; use this function to inspect or export color values.

    Parameters
    ----------
    name : str
        Colormap name.
    kind : str, default "listed"
        Colormap construction kind.
    encoding : {"hex", "rgb"}, default "hex"
        Color encoding to return.
    scale : str, default "default"
        Named scale configuration.
    resolution : int, default 256
        Number of colors sampled when the colormap has no discrete colors.
    **kwargs : Any
        Options passed to :func:`get_cmap`.

    Returns
    -------
    list
        Colors in the requested encoding.

    Raises
    ------
    ValueError
        If ``resolution`` is not positive or ``encoding`` is unsupported.

    Examples
    --------
    .. ipython::

       In [1]: from pyku.core.colourscales import get_cmap_colors
          ...: get_cmap_colors(
          ...:     "temp_abs", kind="linear_segmented", resolution=5
          ...: )
    """
    import matplotlib.colors as mcolors
    import numpy as np

    if resolution < 1:
        raise ValueError("resolution must be a positive integer")

    kind = validate_kind(kind)
    cmap = get_cmap(name, kind=kind, scale=scale, **kwargs)
    cmap_colors = getattr(cmap, "colors", None)
    if cmap_colors is None:
        cmap_colors = cmap(np.linspace(0.0, 1.0, resolution))[:, :3]
    else:
        cmap_colors = [tuple(color[:3]) for color in cmap_colors]

    if encoding == "rgb":
        return list(cmap_colors)
    if encoding == "hex":
        return [mcolors.to_hex(rgb) for rgb in cmap_colors]

    raise ValueError(f"encoding should be 'rgb' or 'hex', not {encoding}")


def _resolve_nbins(
    domain: tuple[float, float] | list[float],
    nbins: int | None = None,
    step: float | None = None,
    skew: float | None = None,
) -> tuple[int | None, float | None]:
    """Resolve bin count while preserving the exact skew pivot."""
    if step is None:
        return nbins, skew

    vmin, vmax = domain
    computed = round((vmax - vmin) / step)
    if nbins is not None and nbins != computed:
        logger.warning(
            "Both nbins=%s and step=%s given for domain [%s, %s]; "
            "step takes precedence -> nbins=%s",
            nbins,
            step,
            vmin,
            vmax,
            computed,
        )
    nbins = computed
    return nbins, skew


def validate_extend(extend):
    if extend not in _VALID_EXTENDS:
        supported = ", ".join(_VALID_EXTENDS)
        raise ValueError(
            f"extend '{extend}' is not valid. Supported values: {supported}"
        )
    return extend


class ResolvedParams(NamedTuple):
    kind: str
    domain: object
    skew: object
    nbins: object
    step: object
    split_index: object
    extend: str
    boundaries: object
    center: object


class ColormapBuilder:
    """Build colormaps and norms from one configuration entry."""

    def __init__(self, config, kind="auto", **kwargs):
        self.config = config
        self.requested_kind = validate_kind(kind)
        self.kwargs = dict(kwargs)

    @property
    def name(self):
        return self.config.name

    def resolve_params(self):
        params = self.config.resolve_params(self.requested_kind, **self.kwargs)
        # Apply builder-specific kind overrides
        kind = self._apply_kind_overrides(params.kind)
        # Return with updated kind
        return ResolvedParams(
            kind=kind,
            domain=params.domain,
            skew=params.skew,
            nbins=params.nbins,
            step=params.step,
            split_index=params.split_index,
            center=params.center,
            extend=params.extend,
            boundaries=params.boundaries,
        )

    def _compute_boundaries(self, params):
        return _compute_boundaries(params)

    def build_pair(self):
        """Build the matched ``(cmap, norm)`` pair for from-level colormaps."""
        params = self.resolve_params()
        return _build_segmented_pair(
            self.name, _to_rgb_colors(self.config.colours_hex), params
        )

    def build_segmented(self):
        """Backward-compatible alias for the segmented pair builder."""
        return self.build_pair()

    def build_norm(self):
        return self.build_pair()[1]

    def build_cmap(self):
        import matplotlib.colors as mcolors

        params = self.resolve_params()
        kind = params.kind

        if "nbins" in self.kwargs and kind in ("linear_segmented", "listed"):
            logger.warning(
                "Option nbins is ignored when used with kind='%s'", kind
            )

        rgb_colors = _to_rgb_colors(self.config.colours_hex)

        if kind == "linear_segmented":
            return mcolors.LinearSegmentedColormap.from_list(
                self.name, _duplicate_single_color(rgb_colors)
            )

        if kind == "listed":
            return mcolors.ListedColormap(rgb_colors)

        return self.build_pair()[0]

    def _apply_kind_overrides(self, kind):
        name = self.name
        if any(p in name for p in _FORCE_LISTED_SUBSTRINGS):
            if kind != "listed":
                logger.info("%s always has kind='listed', forcing.", name)
            kind = "listed"

        if (
            kind == "from_levels"
            and "nbins" in self.kwargs
            and self.kwargs["nbins"] % 2 == 0
            and (any(p in name for p in _WARN_EVEN_BINS_SUBSTRINGS))
        ):
            logger.info(
                "Using an even number of bins with colormap %s. "
                "Please check if this is correct before suppressing"
                " this warning.",
                name,
            )

        return kind


def _build_colormap_pair(
    builder: ColormapBuilder,
    params: "ResolvedParams",
) -> tuple[Any, Any]:
    """Build a colormap and a norm with matching color-bin semantics."""
    import matplotlib.colors as mcolors

    if params.kind == "from_levels":
        return builder.build_pair()

    cmap = builder.build_cmap()
    if params.domain is None:
        raise ValueError(
            f"Colormap '{builder.name}' requires a domain to build a norm."
        )

    if params.kind == "linear_segmented":
        norm = mcolors.Normalize(*params.domain)
        extremes = {}
        if params.extend in ("min", "both"):
            extremes["under"] = cmap(0.0)
        if params.extend in ("max", "both"):
            extremes["over"] = cmap(1.0)
        if extremes:
            cmap = cmap.with_extremes(**extremes)
        cmap.colorbar_extend = params.extend
        return cmap, norm

    boundaries = _compute_boundaries(params)
    n_bins = len(boundaries) - 1
    if n_bins != cmap.N:
        raise ValueError(
            f"Colormap '{builder.name}' has {cmap.N} listed colors but "
            f"its scale defines {n_bins} bins. Use kind='from_levels' or "
            "provide matching boundaries."
        )

    if params.center is None:
        norm = mcolors.BoundaryNorm(boundaries, cmap.N)
    else:
        norm = CenterOutBoundaryNorm(
            boundaries,
            cmap.N,
            center=params.center,
        )

    extremes = {}
    if params.extend in ("min", "both"):
        extremes["under"] = cmap(0.0)
    if params.extend in ("max", "both"):
        extremes["over"] = cmap(1.0)
    if extremes:
        cmap = cmap.with_extremes(**extremes)
    cmap.colorbar_extend = params.extend
    return cmap, norm


def get_norm(
    name: str,
    scale: str = "default",
    **kwargs: Any,
) -> mcolors.Normalize:
    """Return the normalization selected by a colormap configuration.

    Use this function when a normalization is needed separately, for example
    when the colormap is already available. Use :func:`get_colormap` when
    possible to obtain a colormap and its matching normalization together.
    Depending on the configured kind, this returns either a ``BoundaryNorm``
    or a continuous ``Normalize``.

    Parameters
    ----------
    name : str
        Colormap name, with or without the ``pyku.`` prefix.
    scale : str, default "default"
        Configuration scale. Named scales must be listed by
        :func:`get_cmap_scale_names`.
    **kwargs : Any
        Runtime overrides such as ``domain``, ``boundaries``, ``nbins``,
        ``step``, ``skew``, ``center``, and ``extend``. Explicit ``step``
        takes precedence over ``nbins`` when both are supplied. Explicit
        boundaries take precedence over other bin options.

    Returns
    -------
    matplotlib.colors.Normalize
        The normalization configured for the selected colormap kind.

    Raises
    ------
    ValueError
        If the name or scale is unknown, required domain or bin information
        is missing, or the selected kind cannot build a matched pair.

    Examples
    --------
    .. ipython::

       In [1]: from pyku.core.colourscales import get_norm
          ...: yearly_norm = get_norm("temp_ano", scale="yearly")
          ...: yearly_norm.boundaries[[0, -1]]
    """
    name = _resolve_cmap_name(name)
    config = _get_config(name, scale=scale)
    builder = ColormapBuilder(config, kind="auto", **kwargs)
    params = builder.resolve_params()
    return _build_colormap_pair(builder, params)[1]


def get_cmap(
    name: str,
    kind: str = "auto",
    scale: str = "default",
    **kwargs: Any,
) -> mcolors.Colormap:
    """Return a colormap object for a name and construction kind.

    Use this when only a colormap is needed or when pairing it with a
    separately selected norm. Use :func:`get_colormap` to obtain both objects
    from the same configuration and ensure that their boundaries and color
    bins match.

    Parameters
    ----------
    name : str
        Colormap name, with or without the ``pyku.`` prefix.
    kind : {"auto", "listed", "linear_segmented", "from_levels"},
        default "auto"
        ``"auto"`` uses the kind configured for the selected scale.
    scale : str, default "default"
        Configuration scale. Named scales are available through
        :func:`get_cmap_scale_names`.
    **kwargs : Any
        Runtime configuration overrides, including domain and bin options.

    Returns
    -------
    matplotlib.colors.Colormap
        The constructed colormap.

    Raises
    ------
    ValueError
        If the name, scale, or kind is unknown or invalid.

    Examples
    --------
    .. ipython::
       :okwarning:

       @savefig pyku_get_cmap.png scale=70
       In [1]: import matplotlib.pyplot as plt
          ...: import numpy as np
          ...: from pyku.core.colourscales import get_cmap
          ...: cmap = get_cmap("temp_ano", scale="yearly")
          ...: fig, ax = plt.subplots(figsize=(6, 1))
          ...: gradient = np.linspace(0.0, 1.0, 256)[None, :]
          ...: ax.imshow(
          ...:     gradient,
          ...:     aspect="auto",
          ...:     cmap=cmap,
          ...:     interpolation="nearest",
          ...: )
          ...: ax.set_axis_off()
       In [2]: plt.close(fig)
    """
    name = _resolve_cmap_name(name)
    if name not in get_cmap_names():
        raise ValueError(
            f"color map {name} not defined. "
            f"Available colormaps are {get_cmap_names()}"
        )

    kind = validate_kind(kind)
    config = _get_config(name, scale=scale)
    return ColormapBuilder(config, kind=kind, **kwargs).build_cmap()


def get_colormap(
    name: str,
    kind: str = "auto",
    scale: str = "default",
    **kwargs: Any,
) -> tuple[mcolors.Colormap, mcolors.Normalize]:
    """Return a colormap and its matching normalization.

    This is the recommended entry point when plotting a configured scale:
    the returned objects share the same kind, domain, bin boundaries, and
    extension behavior. ``kind="auto"`` uses the kind configured for the
    selected scale, and ``scale="default"`` selects the default scale.
    Other named scales can be discovered with
    :func:`get_cmap_scale_names`.

    Runtime ``domain``, ``boundaries``, ``nbins``, ``step``, ``skew``,
    ``center``, and ``extend`` options override the corresponding configured
    values. Explicit boundaries override other bin options; otherwise an
    explicit ``step`` or ``nbins`` replaces configured bin settings. If both
    ``step`` and ``nbins`` are supplied, ``step`` takes precedence. If the
    selected scale has no domain, supply ``domain``; explicit ``boundaries``
    can provide the domain through their endpoints.

    Parameters
    ----------
    name : str
        Colormap name, with or without the ``pyku.`` prefix.
    kind : {"auto", "listed", "linear_segmented", "from_levels"},
        default "auto"
        Construction kind. ``"auto"`` follows the selected configuration.
    scale : str, default "default"
        Named configuration scale, such as ``"yearly"`` or ``"monthly"``.
    **kwargs : Any
        Runtime configuration overrides. A domain must be configured or
        supplied unless explicit boundaries provide the endpoints.

    Returns
    -------
    tuple of (matplotlib.colors.Colormap, matplotlib.colors.Normalize)
        The colormap and matching normalization.

    Raises
    ------
    ValueError
        If the name, scale, or kind is invalid; required domain or bin
        information is missing; or a listed colormap's number of colors does
        not match its configured number of bins.

    Examples
    --------
    .. ipython::

       @savefig pyku_colormap_pair.png scale=70
       In [1]: import matplotlib.pyplot as plt
          ...: from pyku.core.colourscales import get_colormap
          ...: cmap, norm = get_colormap("temp_ano", scale="yearly")
          ...: fig, ax = plt.subplots()
          ...: mesh = ax.pcolormesh(
          ...:     [[-2, 0], [1, 3]], cmap=cmap, norm=norm
          ...: )
          ...: fig.colorbar(mesh, label="Temperature anomaly (°C)")
       In [2]: plt.close(fig)

       @savefig pyku_colormap_one_map.png scale=70
       In [3]: import pyku
          ...: from pyku.visualisation import one_map
          ...: temperature = (
          ...:     pyku.resources.get_test_data("small_tas_dataset")
          ...:     .isel(time=0)
          ...:     .compute()
          ...: )
          ...: cmap, norm = get_colormap("temp_abs")
          ...: one_map(
          ...:     temperature,
          ...:     var="tas",
          ...:     cmap=cmap,
          ...:     norm=norm,
          ...: )
       In [4]: plt.close("all")
    """
    name = _resolve_cmap_name(name)
    if name not in get_cmap_names():
        raise ValueError(
            f"color map {name} not defined. "
            f"Available colormaps are {get_cmap_names()}"
        )

    config = _get_config(name, scale=scale)
    builder = ColormapBuilder(config, kind=kind, **kwargs)
    params = builder.resolve_params()
    return _build_colormap_pair(builder, params)


def _interpolate_segmented_colors(anchor_colors, n_bins):
    """Interpolate colors in float space and quantize once to RGB-8."""
    import numpy as np

    if n_bins <= 0:
        return []

    anchors = np.asarray(anchor_colors, dtype=np.float64)
    n_anchors = len(anchors)

    if n_anchors == 1:
        interpolated = np.repeat(anchors, n_bins, axis=0)
    else:
        t_values = np.linspace(0, 1, n_bins) if n_bins > 1 else np.array([1.0])
        anchor_positions = np.linspace(0, 1, n_anchors)
        interpolated = np.column_stack(
            [
                np.interp(t_values, anchor_positions, anchors[:, idx])
                for idx in range(3)
            ]
        )

    rgb_255 = np.floor(interpolated * 255.0)
    rgb_255 = np.clip(rgb_255, 0, 255).astype(np.uint8)
    return [(r / 255.0, g / 255.0, b / 255.0) for r, g, b in rgb_255]


def register_all(
    prefix: str = "pyku.",
    force: bool = False,
) -> None:
    """Register all configured pyku colormaps with Matplotlib.

    Parameters
    ----------
    prefix : str, default "pyku."
        Prefix added to each registered colormap name.
    force : bool, default False
        Replace a registry entry if its name is already registered.

    Examples
    --------
    .. ipython::
       :okwarning:

       In [1]: import matplotlib as mpl
          ...: from pyku.core.colourscales import register_all
          ...: register_all(prefix="docs.", force=True)
          ...: "docs.temp_ano" in mpl.colormaps
    """
    import matplotlib as mpl

    for registered_name, entry in PYKU_COLORMAPS.items():
        cmap = entry["cmap"]
        # cmap = mcolors.ListedColormap(rgb_colors, name=registered_name)
        mpl.colormaps.register(
            cmap, name=f"{prefix}{registered_name}", force=force
        )


class CenterOutBoundaryNorm(mcolors.BoundaryNorm):
    """
    Discrete diverging normalization with reflection-symmetric boundary
    semantics around zero.

    Positive classes use [lower, upper).
    Their reflected negative classes therefore use (lower, upper].

    For example:
        [0.5, 1.0)  <->  (-1.0, -0.5]

    This ensures that equal-magnitude boundary values, such as -0.5 and
    +0.5, are assigned to corresponding distance classes.
    """

    def __init__(self, boundaries, ncolors, center=0.0, **kwargs):
        super().__init__(boundaries, ncolors, **kwargs)
        self.center = center

    def __call__(self, value, clip=None):
        import numpy as np

        value = np.ma.asarray(value)

        data = np.asarray(value.data, dtype=float)
        shifted = np.where(
            data < self.center,
            np.nextafter(data, -np.inf),
            data,
        )

        shifted = np.ma.array(shifted, mask=np.ma.getmaskarray(value))
        return super().__call__(shifted, clip=clip)


PYKU_COLORMAPS = {
    _registry_name(name, scale): _build_registry_entry(name, scale)
    for name in get_cmap_names()
    for scale in ("default", *_get_scale_names(name))
}
