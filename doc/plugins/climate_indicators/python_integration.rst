CLIX Python Integration
=======================

To integrate CLIX climate indicators into your own Python routines, there are
**two main approaches**:

1. **Using the Python API** via the
   :py:class:`pyku.clix.manager.ClimateIndicator` class  
2. **Calling the CLIX command-line interface (CLI)** directly from within a
   Python script

Both methods allow you to calculate climate indicators programmatically,
depending on whether you prefer an object-oriented API or a simple CLI-style
invocation.

1. Using the Python API
-----------------------

To use the :py:class:`~pyku.indices.clix_manager.ClimateIndicator` class, set
up the input data and optional parameters as shown below.

Here is an example demonstrating how to use the
:py:class:`~pyku.indices.clix_manager.ClimateIndicator` class for calculating
*summer days*:

.. code-block:: python

   import xarray as xr
   from pathlib import Path

   from pyku.clix.manager import ClimateIndicator

   # Define input file(s) and load them
   base_dir = Path('/path/to/hyras/output/tasmax/v6-1/05/')
   tasmax_file_name = 'tasmax_hyras_5_2010_v6-1.nc'
   tasmax_file_path = base_dir / tasmax_file_name

   ds = xr.open_dataset(tasmax_file_path)
   da = ds['tasmax']

   # Define indicator name (e.g., 'txge25' for summer days)
   indicator_name = 'txge25'

   # Define frequency for calculation ('MS' -> monthly, 'YS' -> yearly etc.)
   frequency = 'MS'

   # Define parameters (use an empty dictionary for default indicator setup)
   params = {}

   # Example of using modified parameters/thresholds (uncomment to test)
   # params = {'thresh': '25.6 degC', 'op': '>'}

   # Initialize ClimateIndicator
   clind = ClimateIndicator(indicator_name, frequency, params)

   # Assign required input DataArray(s)
   # xclim indices often expect specific variable names for their arguments.
   # For 'txge25' (summer days), it typically expects a 'tasmax' variable.
   clind.required_args['tasmax'] = da
   print("Required arguments (assigned):", clind.required_args)

   # Show optional arguments (thresholds, operators, etc.)
   print("Optional arguments:", clind.optional_args)

   # Show function name that is used to compute the indicator
   print("Xclim function name:", clind.xclim_func_name)

   # Calculate Indicator
   txge25_result = clind()

   # Save as NetCDF
   output_filename = Path('summer_days.nc')
   txge25_result.to_netcdf(output_filename)
   print(f"Indicator calculated and saved to {output_filename}")

2. Using the CLI within Python code
-----------------------------------

Alternatively, CLIX can be used directly from within a Python program by
calling its **command-line interface (CLI)** entry point. This is useful when
you want to run CLIX as if it were executed from the terminal, but under
programmatic control.

For example, the following snippet performs a calculation of the *mean
temperature* indicator ``tmmean`` on a monthly frequency:

.. code-block:: python

   import pyku.clix.core as clix

   # Define input file (or input directory)
   ifile = 'input_file.nc'

   # Define calculation frequency (e.g., 'month', 'year')
   frequency = 'month'

   # Define the indicator name (e.g., 'tmmean', 'txge25', etc.)
   indicator = 'tmmean'

   # Call CLIX main function with CLI-style arguments
   clix.main(['-ifiles', ifile, '-frequency', frequency, indicator])

This approach internally executes the same routines used by the CLIX
command-line tool, allowing seamless integration with other Python workflows
or batch processing systems.

Summary: When to Use Which Approach
-------------------------------------

**Python API (`ClimateIndicator`)**

* Ideal for fine-grained control over input datasets, variable assignment, and
  parameters.
* Supports direct use of in-memory :py:class:`xarray.DataArray` objects.

**CLI Invocation (`clix.main`)**

* Convenient when running multiple indicators in sequence or integrating with
  scripts that already use CLI-style argument parsing.
* Matches the behavior of the standalone `clix` command-line tool.
