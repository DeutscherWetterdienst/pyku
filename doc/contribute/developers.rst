Developers
==========

This page describes the workflow to contribute to pyku.

Design philosophy
-----------------

pyku functions should take in :class:`xarray.Dataset` and output
:class:`xarray.Datasets`. :class:`xarray.DataArray` should not be used in the
interface, since essential climate metadata would be lost (e.g. the crs
variable).

Alternatively use :class:`geopandas.GeoDataFrame` for the input and outputs
where polyons or point data are needed.

Write independent functions for simplicity, and only use objects where
necessary

Developer installation
----------------------

First, create a new virtual environment and install*pyku:

.. code:: bash

   # Create a new virtual environment
   # --------------------------------

   python3 -m venv yourvenv

   # Activate
   # --------

   source yourvenv/bin/activate

Clone and ``cd`` to the *pyku* directory:

.. code:: bash

   git clone https://gitlab.dwd.de/ku/libraries/pyku/
   cd pyku

.. tip::

   If you installed pyku in development mode on one branch or master, but the
   ``pyproject.toml`` was modified on the other feature branch you are trying
   or want to work on, you will need to run ``pip install --editable .`` again.
   Also, maybe run ``pip uninstall pyku`` first to keep it tidy.

Now pyku can be installed in development mode. All changes made are then
immediately available so that you can debug:

.. code:: bash

   pip install -e .

Reload in jupyter
-----------------

If you are working in jupyter or in ipython, you will likely need to reload the
part of *pyku* that you are working on with ``importlib``:

.. code:: python

   import importlib

   # First import
   # ------------

   import pyku.meta as meta

   # Reload library to test changes on-the-fly
   # -----------------------------------------

   importlib.reload(meta)
   meta.get_frequency(ds, dtype='freqstr')

.. warning::

   How to debug with the xarray data accessor for debuggin is an open question.
   That is it still needs to be clarified how to reload in jupyter if you use:

   .. code:: python

      ds.pyku.get_frequency(dtype='freqstr')

   Instead you will can use for debugging:

   .. code:: python

      importlib.reload(meta)
      meta.get_frequency(ds, dtype='freqstr')

   If you know the solution, dont hesitate to let us know or update this doc.

Doctests
--------

The efficacy of testing is greatly enhanced through the integration of
documentation, which not only elucidates the code's functionality but also
serves as a pivotal testing resource. Leveraging doctests, developers can
seamlessly embed executable code snippets within the documentation, thereby
facilitating both understanding and validation of the software's behavior. This
dual-purpose approach ensures that documentation not only elucidates the
intricacies of the codebase but also serves as a robust testing suite,
enhancing the overall quality and reliability of the software.

Concretely and as an example, the docstring of the function
:func:`pyku.check.check_units` serves as executable code within the
documentation.

.. code:: python

    """
    Check units

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset.

    Returns:
        :class:`pandas.DataFrame`: Dataframe containing checks and issues.

    Example:
        .. ipython::

           In [0]: import xarray, pyku
              ...: ds = pyku.resources.get_test_data('hyras')
              ...: ds.pyku.check_units()
    """

During documentation build, this code is automatically executed, and any errors
encountered will cause the pipeline to fail, signaling issues. This also serves
to automatically generate the function documentation from the docstring:

.. autofunction:: pyku.check.check_units
   :no-index:

Unit testing
------------

Unit testing is set up and configured. You can run unit tests outside the
pipeline with:

.. code:: bash

   python3 -m unittest discover -v -s ./testing -p "*_test.py"

Logging
-------

The logging level for debugging can be set like so:

.. code:: python

   import pyku.resources as resources
   import pyku.geo as geo
   import logging

   logging.getLogger('pyku').setLevel(logging.DEBUG)
   logging.basicConfig(level=logging.WARNING)

   ds = resources.get_test_data('air_temperature')
   geo.sort_georeferencing(ds)

Building the documentation
--------------------------

The documentation is built with sphinx. Go the the ``doc`` directory and you
will have the following options. Mostly all options are usefull depending on
context.

Building the documentation is resource intensive due to the amount of testing
that runs. To work only on part of the documentation, you can specify in
``doc/conf.py`` the ``input_patterns`` variable which consist of the list of
files that will be build. This permits to build only the part of the
documentation you are working on.

.. rubric:: ``make html``

The ``make html`` is very simple and outputs clear errors:

.. code:: bash

   # Build documentation
   # -------------------

   make html

   # Serve the documentation
   # -----------------------

   python -m http.server --directory _build/html/ --bind=$HOSTNAME

You can then access the documentation from your web browser. For example, if my
machine is oflws261, the documentation will be available at
http://oflws261.dwd.de:8000

You can also build a pdf with ``make latexpdf`` or push directly to confluence
if you configured it so and installed the dependencies with ``make
confluence``.

.. rubric:: ``sphinx-build``

The ``sphinx-build`` method is usefull because you can set up multiprocessing
with the ``-j`` option and specify the output directory. However the error
output is hidden due to multiprocessing:

.. code:: bash

   # Build documentation
   # -------------------

   sphinx-build -j 8 ./ _build/html/

   # Serve the documentation
   # -----------------------

   python -m http.server --directory _build/html/ --bind=$HOSTNAME

.. rubric:: ``sphinx-autobuild``

``sphinx-autobuild`` also permits to set up multiprocessing with the ``-j``
option, specify the output directory and changes are tracked in real time as
you make your changes. However again the error output is mostly hidden due to
multiprocessing.

.. code:: bash

   # Build documentation
   # -------------------

   sphinx-autobuild -j 8 ./ _build/html/ --host $HOSTNAME

