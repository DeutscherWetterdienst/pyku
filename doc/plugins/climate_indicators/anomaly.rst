Anomalies
=========

CLIX offers the functionality to calculate **anomalies** of climate indicators using the ``--anomaly`` option and supports two types of anomaly calculations:

* **Absolute (``abs``):** Calculates the absolute differences.
* **Percentage (``perc``):** Calculates the percentage differences.

Calculating Anomalies
~~~~~~~~~~~~~~~~~~~~~

To calculate an anomaly, you must provide **two distinct time periods** using the ``--date_range`` and ``--ref_date_range`` arguments. This is because anomalies are calculated as the difference between a specific period and a reference (climatological) period. The reference period is always averaged to the given frequency and serves as a climatological reference period (refer to the :doc:`Climatology documentation <climatology>`).

To calculate time series anomalies, the following example shows the command to get the monthly anomalies of recent summer days compared to the climatological WMO period of 1961-1990.

**Example: Time Series of Monthly Absolute Anomalies of Summer Days**

This command calculates the monthly absolute anomalies of ``txge25`` (summer days) by comparing the period 2011-2020 against 1961-1990:

.. code:: bash

   clixrun --input /path/to/tas/input/dir/ --date_range 20110101 20201231 --ref_date_range 19610101 19901231 --frequency month --anomaly abs txge25

**Example: Time Series of Percentage Anomalies of Total Precipitation Amount**

This command calculates the yearly percentage anomalies of total precipitation amount, comparing 1991-2020 with the climatological mean of 1961-1990:

.. code:: bash

   clixrun --input /path/to/precip/input/dir/ --date_range 19910101 20201231 --ref_date_range 19610101 19901231 --frequency year --anomaly perc rtot

To calculate anomalies between two climatological periods, use the ``--average`` argument in combination with ``--anomaly``.

**Example: Calculate Seasonal Absolute Anomalies of Days with Precipitation Above 20 mm**

This command calculates the seasonal absolute anomalies of ``rgt20mm`` (days with precipitation above 20 mm) by comparing the period 2071-2100 against 1961-1990, where both periods are averaged before the anomaly calculation:

.. code:: bash

   clixrun --input /path/to/scenario.yaml --date_range 20710101 21001231 --ref_date_range 19610101 19901231 --frequency season --anomaly abs --average rgt20mm

