project = 'pyku'
copyright = '2026, Deutscher Wetterdienst'
author = 'KU'

# Supress warnings
# ----------------

# RuntimeWarning: You are using an unsupported version of pandoc (2.0.6).
# Your version must be at least (2.9.2) but less than (4.0.0).

import warnings

warnings.filterwarnings(
    "ignore", 
    category=RuntimeWarning, 
    message="You are using an unsupported version of pandoc"
)

# Suppress UserWarnings (e.g., automated data downloads) during doc generation
warnings.filterwarnings("ignore", category=UserWarning)

# Extensions
# ----------

extensions = [
    'matplotlib.sphinxext.mathmpl',
    'matplotlib.sphinxext.plot_directive',
    'sphinx.ext.viewcode',
    'sphinx.ext.doctest',
    'sphinx.ext.intersphinx',
    'sphinx.ext.napoleon',
    'sphinx.ext.autodoc',
    'sphinx.ext.todo',
    'sphinxcontrib.programoutput',
    'IPython.sphinxext.ipython_directive',
    'IPython.sphinxext.ipython_console_highlighting',
    'sphinx_togglebutton',
    'nbsphinx',
    'sphinx_gallery.load_style',
]

# Build links to external documentation
# -------------------------------------

primary_domain = 'py'

intersphinx_mapping = {
    'xarray': ('https://docs.xarray.dev/en/stable/', None),
    'geopandas': ('https://geopandas.org/en/stable/', None),
    'pandas': ('https://pandas.pydata.org/pandas-docs/stable/', None),
    'numpy': ('https://numpy.org/doc/stable/', None),
    'pyresample': ('https://pyresample.readthedocs.io/en/stable/', None),
    'cartopy': ('https://cartopy.readthedocs.io/latest/', None),
    'matplotlib': ('https://matplotlib.org/stable/', None),
}

ipython_warning_is_error = True

sphinx_ipython_plot = "inline"
templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

html_theme = 'sphinx_book_theme'
html_static_path = ['_static', 'savefig']

nbsphinx_kernel_name = 'python3'

html_favicon = '_static/pyku_logo.jpg'

html_theme_options = {
    "navigation_with_keys": True,
    "logo": {
        "text": "PYKU",
        "sizes": "32x32",
        "image_light": "_static/pyku_logo.jpg",
        "image_dark": "_static/pyku_logo.jpg",
    }

}

todo_include_todos = True

nbsphinx_thumbnails = {
     'plugins/climate_indicators/clix': '_static/pyku_indicators.jpg',
     'tutorials/colormaps': '_static/pyku_colors.jpg',
     'tutorials/polygons': '_static/pyku_polygons.jpg',
     'tutorials/geographic_projections': '_static/pyku_mercator.jpg',
     'tutorials/downscaling_svd': '_static/pyku_downscaled.jpg',
     'tutorials/starter': '_static/pyku_bike.jpg',
     'tutorials/named_ensembles': '_static/pyku_together.jpg',
     'tutorials/CMORization': '_static/pyku_bored.jpg',
     'tutorials/opendap': '_static/pyku_network.jpg',
     'tutorials/distributed_computing': '_static/pyku_distributed.jpg',
     'tutorials/customize_plots': '_static/pyku_customize.jpg',
}

# Strip type hints from the function header and keep them in the parameter
# descriptions
autodoc_typehints = "description"

# Show short type names (e.g., 'Dataset' instead of
# 'xarray.core.dataset.Dataset')
python_use_unqualified_type_names = True

# Optional: Simplify default values if they are lengthy
autodoc_typehints_format = "short"

# For testing only
# ----------------

# include_patterns = [
#     "index.rst",
#     "api.rst",
#     "visualisation/index.rst",
#     "visualisation/bias.rst",
#     "visualisation/distributions.rst",
#     "visualisation/error_maps.rst",
#     "visualisation/helpers.rst",
#     "visualisation/index.rst",
#     "visualisation/map_plotting.rst",
#     "visualisation/mean.rst",
#     "visualisation/regional.rst",
#     "visualisation/statistical_maps.rst",
#     "visualisation/time_series.rst",
#     "visualisation/variability.rst",
#     "tutorials/index.rst",
#     "tutorials/customize_plots.ipynb",
#     "tutorials/geographic_projections.ipynb",
# ]
