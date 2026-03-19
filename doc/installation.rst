Installation
============

.. warning::

   Pyku is not yet on PyPI, but we're working on it.

To install pyku, ensure your system is properly configured. The following
non-python dependencies are necessary:

* `geos <https://libgeos.org/>`_
* `proj <https://proj.org/>`_
* `hdf5 <https://www.hdfgroup.org/solutions/hdf5/>`_
* `netcdf <https://www.unidata.ucar.edu/software/netcdf/>`_
* `udunits <https://www.unidata.ucar.edu/software/udunits/>`_

To build the documentation, you will additionally need `pandoc
<https://pandoc.org/>`_.

Once these prerequisites are met, you can install the latest release of pyku.

.. using the command ``pip install``.
..
.. .. code:: bash
..
..    # Install the latest stable pyku release
..    # --------------------------------------
..
..    pip install pyku
..
..    # Install extra dependencies to build documentation
..    # -------------------------------------------------
..
..    pip install pyku[documentation]

.. Upgrade
.. -------
..
.. This command installs or updates to the latest version.
..
.. .. code:: bash
..
..    pip install pyku --upgrade

.. Pin version
.. -----------
..
.. By specifying an exact version, it can also be used to downgrade pyku:
..
.. .. code:: bash
..
..    pip install pyku==v1.0.0

.. Optional packages
.. -----------------
..
.. To install the necessary packages for building the documentation, including all
.. Sphinx dependencies and Jupyter, use this setup. These packages will be
.. installed automatically, making it an excellent starting point.
..
.. .. code:: bash
..
..    pip install pyku[documentation]
..
.. Bindings to CDO should generally be avoided within the scope of pyku. However,
.. there is one exception: a function required for derotating wind components in
.. rotated model data. This functionality is isolated from the rest of the code
.. and can be installed using:
..
.. .. code:: bash
..
..    pip install pyku[cdo_bindings]

from master
-----------

To install the current master from the repository:

.. code:: bash

   pip install "pyku @ git+https://github.com/DeutscherWetterdienst/pyku"

To install the dependencies to build the documentation:

.. code:: bash

   pip install "pyku[documentation] @ git+https://github.com/DeutscherWetterdienst/pyku"

pin version
-----------

To pin a version:

.. code:: bash

   pip install "pyku @ git+https://github.com/DeutscherWetterdienst/pyku@v1.0.0"

from source
-----------

To install from source, clone the repository and run:

.. code:: bash

   pip install .

To install from source with the dependencies to build the documentation

.. code:: bash

   pip install ".[documentation]"

for development
---------------

To install in development mode:

.. code:: bash

   pip install -e .

To install in development mode with the dependencies to build the
documentation:

.. code:: bash

   pip install -e ".[documentation]"

Compiled dependencies
---------------------

The following dependencies are not installed automatically with *pyku* because
additional non-Python dependencies are required.

.. rubric:: python-SBCK

Download and install the required eigen dependency:

.. code:: bash

   wget https://gitlab.com/libeigen/eigen/-/archive/3.4.0/eigen-3.4.0.tar.gz
   mkdir build
   cd build
   cmake ../ -DCMAKE_INSTALL_PREFIX=/path/to/eigen-3.4.0/install
   export PKG_CONFIG_PATH=$PKG_CONFIG_PATH:/path/to/eigen-3.4.0/install/share/pkgconfig

Install the SBCK library from source:

.. code:: bash

   git clone https://github.com/yrobink/SBCK-python.git
   CPPFLAGS='-I/path/to/eigen-3.4.0/install/include' pip install SBCK

.. rubric:: Conservative resampling

There were issues with multiprocessing when using conservative resampling
within pyku. To resolve this, disable multiprocessing in the ESMF library and
allow pyku to manage multiprocessing as described below:

.. code:: bash

   # Clone repository
   # ----------------

   git clone https://github.com/esmf-org/esmf

   # Export path to esmf directory
   # -----------------------------

   export ESMF_DIR=/path/to/esmf/

   # Build
   # -----

   export ESMF_OPENACC='OFF'
   export ESMF_OPENMP='OFF'
   export ESMF_PTHREADS='OFF'
   export ESMF_PIO='OFF'
   git checkout v8.6.1
   make
   make install

   # Set that environment variable
   # -----------------------------

   export ESMFMKFILE=/path/to/esmf/DEFAULTINSTALLDIR/lib/libO/Linux.gfortran.64.mpiuni.default/esmf.mk

.. code:: bash

   pip uninstall esmpy  # If applicable
   cd esmf/src/addon/esmpy
   make install

.. code:: bash

   pip uninstall xESMF  # If applicable
   pip install xESMF






