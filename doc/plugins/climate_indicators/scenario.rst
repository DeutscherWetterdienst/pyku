Climate Scenarios
=================

Working with climate projection data, especially when combining historical and
projection experiments, can often be complex. To streamline data selection and
avoid manual preprocessing steps, CLIX allows you to select files based on Data
Reference Syntax (DRS) elements defined in a YAML configuration file, using the
``--input`` argument.

Defining Input with a YAML File
-------------------------------

Within the YAML file, you must first specify a ``root_directory`` where your
simulation data is stored. Following this, you set a DRS standard (supported
standards can be listed with ``pyku.drs.list_drs_standards``). Finally, you
define various DRS facets and their values to select one or multiple
experiments or variables.

Facets can be specified as direct ``key: value`` pairs or as ``key: [list, of,
values]``.

.. note::
   If a facet is not explicitly provided in the YAML file, it defaults to a
   wildcard character (e.g., ``version: "*"``). This is useful when multiple
   versions need to be considered.

Below is an example YAML configuration for selecting regional climate
projection data from the CMIP5 era:

.. literalinclude:: config_CORDEX-CMIP5.yaml
   :language: yaml

In this example, a single model is selected across two RCP scenarios. All
specified facets are evaluated against the `cordex` standard. The selected
NetCDF files are then loaded into a dataframe and merged into a single time
series, beginning with the historical simulation files and extending with the
RCP8.5 scenario files.

Applying Climate Indicators to Climate Scenarios
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To produce a single time series for a full simulation run (combining historical
and scenario data) and apply a climate indicator, use the CLIX command with
your YAML configuration:

.. code:: bash

    clixrun --input config_CORDEX-CMIP5.yaml --frequency year txge25

This command will result in a yearly time series of summer days (``txge25``).

Calculating Climate Change Response
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Combining input files specified via a YAML configuration with the ``--anomaly``
argument is powerful for computing the change in a climate indicator between
two distinct time periods.

The following example demonstrates how to compute the change in the diurnal
temperature range using the CORDEX-CMIP6 standard and its facets:

.. literalinclude:: config_CORDEX-CMIP6.yaml
   :language: yaml

.. code:: bash

    clixrun --input config_CORDEX-CMIP6.yaml --frequency season \
    --ref_date_range 19710101 20001231 --date_range 20710101 21001231 \
    --anomaly abs dtr

This command will output the absolute change of the diurnal temperature range
for the end of the century (2071-2100) compared to the reference period of
1971-2000.

.. tip::
   To determine the necessary facet names for standards not explicitly shown in
   the examples, use the ``pyku.drs.get_facets_from_file_parent`` and
   ``pyku.drs.get_facets_from_file_stem`` functions. These functions require a
   sample file that adheres to a standard listed in
   ``pyku.drs.list_drs_standards``.
