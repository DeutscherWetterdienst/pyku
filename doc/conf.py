project = 'pyku'
copyright = '2026, Deutscher Wetterdienst'
author = 'KU'

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

ipython_warning_is_error = False

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

# For testing only
# ----------------

include_patterns = [
    "index.rst",
    "api.rst",
    "analyse.rst"
]
