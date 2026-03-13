#!/usr/bin/env python3

"""
Processing library
"""

from . import logger


def magic(ds):

    """
    Evil-magically makes datasets good. The evil_magic function attempts to
    auto-magically:

    * process the calendar to a gregorian calendar
    * process datetimes reference to the lower bound of the time boundaries
    * process variable names towards CMOR standard
    * process units to SI units
    * sort geographical and projection coordinates from top to bottom and
      left to right

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset.

    Returns:
        :class:`xarray.Dataset`: Magicked dataset
    """

    import pyku.drs as drs
    import pyku.timekit as timekit

    # Process calendar, datetimes, variable names units, georeferencing
    # -----------------------------------------------------------------

    ds = timekit.to_gregorian_calendar(ds)
    ds = drs.to_cmor_varnames(ds)
    ds = drs.to_cmor_units(ds)
    ds = drs.to_cmor_attrs(ds)

    return ds


def inpainting(ds_in, roi=3, method="INPAINT_TELEA"):

    """
    .. warning::

       This function is unmaintained. Please contact a maintainer if you would
       like to keep this function.

    Inpainting data correction

    Arguments:
        ds (:class:`xarray.Dataset`): Input data
        method (str): Defaults to "INPAINT_TELEA". One of{"INPAINT_TELEA",
            "INPAINT_NS"}.
        roi (int): Inpainting radius

    Returns:
        :class:`xarray.Dataset`: The inpainted dataset.

    References:

        * https://docs.opencv.org/3.4/d7/d8b/group__photo__inpaint.html

    Example:

        .. code-block:: ipython

           import pyku, numpy

           # Select some model data and break it
           # -----------------------------------

           broken = pyku.resources.get_test_data('model_data')\\
           .isel(time=[0, 1, 2, 3])
           broken['tas'] = broken['tas'].where(
               (broken['tas']<263) | (broken['tas']>263.5),
               numpy.nan
           )

           # Repair the broken data
           # ----------------------

           repaired = ds.pyku.inpainting(roi=3)

           # Set title and plot
           # ------------------

           broken = broken.assign_attrs({'label': 'Broken'})
           repaired = repaired.assign_attrs({'label': 'Repaired'})

           pyku.analyse.two_maps(
               broken.isel(time=0),
               repaired.isel(time=0),
               var = 'tas',
               crs='EUR-11'
           )
    """

    import textwrap
    import numpy as np
    import copy
    import pyku.meta as meta

    try:
        import cv2
    except ImportError as e:
        raise ImportError(
            "OpenCV (cv2) is required for this function. "
            "Please install it with:\n\n"
            "    pip install opencv-contrib-python\n"
        ) from e

    if method == "INPAINT_TELEA":
        method = cv2.INPAINT_TELEA
    elif method == "INPAINT_NS":
        method = cv2.INPAINT_NS
    else:
        message = textwrap.dedent(
            f"""
            Method {method} not defined. Use either INPAINT_TELEA or INPAINT_NS
            """)
        raise Exception(message)

    # Make a copy of the input dataset
    # --------------------------------

    ds_out = ds_in.copy(deep=True)

    # Loop over variables
    # -------------------

    for varname in meta.get_geodata_varnames(ds_out):

        # Get numpy array and save shape
        # ------------------------------

        in_np = ds_out[varname].values
        in_shape = in_np.shape

        # Reshape numpy array to (-1 x ny x nx)
        # -------------------------------------

        in_np = in_np.reshape(-1, in_shape[-2], in_shape[-1])

        # Make a copy of the numpy array
        # ------------------------------

        out_np = copy.deepcopy(in_np)

        # Get all images of size ny x nx and apply
        # ----------------------------------------

        for idx in range(in_np.shape[0]):

            # Get image
            # ---------

            img = in_np[idx]

            # Get mask of nan values
            # ----------------------

            mask = np.where(np.isnan(img), 1, 0).astype('uint8')

            # Apply inpainting
            # ----------------

            corrected = cv2.inpaint(img, mask, roi, method)
            out_np[idx] = corrected

        # Reshape and copy modified data to the output DataSet
        # ----------------------------------------------------

        out_np = out_np.reshape(in_shape)
        ds_out[varname].values = out_np

    return ds_out


def _computable_varnames(available_varnames, wanted_varnames):

    """
    Given a set of available varnames and a set of wanted varnames, return the
    set of varnames from wanted varnames which can be computed from available
    varnames.

    Arguments:
        available_varnames (set): list of available varnames
        wanted_varnames (set): list of wanted varnames

    Returns:
        set:
            List of wanted varnames which can be computed given the list of
            available varnames
    """

    available_varnames = set(available_varnames)
    wanted_varnames = set(wanted_varnames)
    computable_varnames = set()

    if 'hurs' in wanted_varnames and 'hurs' not in available_varnames and \
       {'ps', 'tas', 'huss'}.issubset(available_varnames):

        computable_varnames.add('hurs')
        available_varnames.add('hurs')

    if 'tdew' in wanted_varnames and 'tdew' not in available_varnames and \
       {'tas', 'hurs'}.issubset(available_varnames):

        computable_varnames.add('tdew')
        available_varnames.add('tdew')

    if 'huss' in wanted_varnames and 'huss' not in available_varnames and \
       {'ps', 'tdew'}.issubset(available_varnames):

        computable_varnames.add('huss')
        available_varnames.add('huss')

    return computable_varnames


def calc(ds):

    """
    Add 'huss', 'hurs' and 'tdew' to dataset if possible

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset.

    Returns:
        :class:`xarray.Dataset`: Dataset with all possible extended variables
            included.

    Examples:

        .. ipython::
           :okwarning:

           In [0]: import pyku
              ...:
              ...: # Open test dataset and select a few time steps
              ...: # ---------------------------------------------
              ...:
              ...: ds = pyku.resources.get_test_data('tas_hurs')
              ...: ds = ds.isel(time=[0,1,2])
              ...:
              ...: # Calculate tdew and show data variables
              ...: # --------------------------------------
              ...:
              ...: ds = ds.pyku.calc()
              ...: ds.data_vars

    """

    # Note that a list is used for wanted_varnames since a set is not ordered.

    import pyku.meta as meta

    available_varnames = meta.get_geodata_varnames(ds)
    wanted_varnames = ['hurs', 'tdew', 'huss']
    tobecomputed_varnames = _computable_varnames(
        available_varnames, wanted_varnames
    )

    for varname in wanted_varnames:

        if varname in ['hurs'] and varname in tobecomputed_varnames:
            ds = calc_hurs(ds)
        if varname in ['tdew'] and varname in tobecomputed_varnames:
            ds = calc_tdew(ds)
        if varname in ['huss'] and varname in tobecomputed_varnames:
            ds = calc_huss(ds)

    return ds


def calc_windspeed(ds):

    """
    Given windspeed components, calculate the windspeed

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset.

    Returns:
        :class:`xarray.Dataset`: The dataset with windspeed included.
    """

    def calculate_norm(da_ua, da_va, varname, attrs={}):

        """
        Calculate norm (e.g. wind speed from Eastward and Northward components)

        Arguments:
            da_ua (xr.DataArray): e.g. the eastwart wind component
            da_va (xr.DataArray): e.g. the northward wind component
            varname (str): variable name in output DataArray
            attrs: Attributes in output DataArray

        Returns:
            xr.DataArray containing the norm (e.g. wind speed)
        """

        import xarray as xr
        import dask.array as dk

        ds = xr.merge([da_ua, da_va])

        # Calculate windspeed
        # -------------------

        ds = ds.assign(norm=dk.sqrt(dk.power(ds[da_ua.name], 2) +
                                    dk.power(ds[da_va.name], 2)))

        # Rename variable
        # ---------------

        ds = ds.rename({'norm': varname})

        # Set attributes
        # --------------

        ds[varname].attrs = attrs

        return ds[varname]

    # Config: var -> (u_component, v_component, standard_name, long_name)
    configs = {
        "windspeed850":
        ("ua850",  "va850", "wind_speed_850",  "Wind Speed at 850 Pa"),
        "windspeed100m":
        ("ua100m", "va100m", "wind_speed_100m", "Wind Speed at 100 m"),
        "sfcWind":
        ("uas",    "vas",    "wind_speed",      "Near-Surface Wind Speed"),
    }

    # Calculate wind speed
    # --------------------

    for out_name, (ua_name, va_name, std_name, long_name) in configs.items():
        if ua_name in ds and va_name in ds and out_name not in ds:
            attrs = dict(ds[ua_name].attrs)  # copy attrs from u-component
            attrs.update({
                "standard_name": std_name,
                "long_name": long_name})
            ds[out_name] = calculate_norm(
                ds[ua_name],
                ds[va_name],
                out_name,
                attrs
            )

    return ds


def calc_tdew(ds):

    """
    Add dew point temperature to dataset, calculated from 'tas' and 'hurs'

    Arguments:
        ds (:class:`xarray.Dataset`): The input data containing 'tas' and
            'hurs'.

    Returns:
        :class:`xarray.Dataset`: The data with tdew included.

    Examples:

        .. ipython::
           :okwarning:

           In [0]: import pyku
              ...:
              ...: # Open test dataset and select a few time steps
              ...: # ---------------------------------------------
              ...:
              ...: ds = pyku.resources.get_test_data('tas_hurs')
              ...: ds = ds.isel(time=[0,1,2])
              ...:
              ...: # Calculate tdew and show data variables
              ...: # --------------------------------------
              ...:
              ...: ds = ds.pyku.calc_tdew()
              ...: ds.data_vars

    """

    import textwrap
    import metpy
    import metpy.calc
    import xarray as xr
    import pyku.drs as drs
    import pyku.meta as meta

    # Check if variables are in the dataset
    # -------------------------------------

    if 'tdew' in ds.data_vars:
        raise Exception("Variable tdew is already in the dataset")

    if 'tas' not in ds.data_vars or 'hurs' not in ds.data_vars:

        message = textwrap.dedent(
            f"""
            During preprocessing and while trying to calculate 'tdew',
            either 'tas' or 'hurs' is missing. Available variables are
            {ds.data_vars}.
            """
        )

        raise Exception(message)

    tdew = metpy.calc.dewpoint_from_relative_humidity(
        ds['tas'],
        ds['hurs']
    ).rename('tdew')

    # Dequantify and set attributes
    # -----------------------------

    tdew = tdew.metpy.dequantify()

    # Set units
    # ---------

    # The function to_cmor_units only accept xarray.Dataset

    tdew = drs.to_cmor_units(tdew.to_dataset())['tdew']

    # Set name of crs variable
    # ------------------------

    crs_varname = meta.get_crs_varname(ds)

    if crs_varname is not None:
        tdew.attrs['grid_mapping'] = crs_varname

    # Set cell_method
    # ---------------

    tas_cm = ds.tas.attrs.get('cell_methods', None)
    hurs_cm = ds.hurs.attrs.get('cell_methods', None)

    if tas_cm and hurs_cm and (tas_cm == hurs_cm):
        tdew.attrs['cell_methods'] = tas_cm
    else:
        logger.warn(
            "cell_methods not set: attributes either differ or are missing "
            "from input data"
        )

    # Set attributes
    # --------------

    tdew = tdew.assign_attrs({
        'standard_name': 'dew_point',
        'long_name': 'Dew Point Temperature',
        'comment': 'Calculated with pyku',
    })

    ds = xr.merge([ds, tdew])

    # Return
    # ------

    return ds


def calc_hurs(ds):

    """
    Calculate 'hurs' from 'ps', 'tas' and 'huss'

    Arguments:
        ds (:class:`xarray.Dataset`): The Input data containing 'ps', 'tas' and
            'huss'.

    Returns:
        :class:`xarray.Dataset`: The dataset including tdew.

    Examples:

        .. ipython::
           :okwarning:

           In [0]: import pyku
              ...:
              ...: # Open test dataset and select a few time steps
              ...: # ---------------------------------------------
              ...:
              ...: ds = pyku.resources.get_test_data('tas_ps_huss')
              ...: ds = ds.isel(time=[0,1,2])
              ...:
              ...: # Calculate hurs and show data variables
              ...: # --------------------------------------
              ...:
              ...: ds = ds.pyku.calc_hurs()
              ...: ds.data_vars
    """

    import textwrap
    import metpy
    import xarray as xr
    import pyku.drs as drs
    import pyku.meta as meta

    # Check if variables are in the dataset
    # -------------------------------------

    if 'hurs' in ds.data_vars:

        raise Exception("Variable hurs is already in the dataset")

    if 'ps' not in ds.data_vars or \
       'tas' not in ds.data_vars or \
       'huss' not in ds.data_vars:

        message = textwrap.dedent(
            f"""
            During preprocessing and while trying to calculate 'hurs',
            either 'ps', 'tas' or 'huss' is missing. Available variables
            are {ds.data_vars}.
            """)

        raise Exception(message)

    hurs = metpy.calc.relative_humidity_from_specific_humidity(
        ds['ps'], ds['tas'], ds['huss']
    ).rename('hurs')

    # Dequantify and set attributes
    # -----------------------------

    hurs = hurs.metpy.dequantify()

    # Set units
    # ---------

    # to_cmor_units only accepts datasets
    hurs = drs.to_cmor_units(hurs.to_dataset())['hurs']

    # Set name of crs variable
    # ------------------------

    crs_varname = meta.get_crs_varname(ds)

    if crs_varname is not None:
        hurs.attrs['grid_mapping'] = crs_varname

    # Set cell_method
    # ---------------

    ps_cm = ds.ps.attrs.get('cell_methods', None)
    tas_cm = ds.tas.attrs.get('cell_methods', None)
    huss_cm = ds.huss.attrs.get('cell_methods', None)

    if ps_cm and tas_cm and huss_cm and (ps_cm == tas_cm == huss_cm):
        hurs.attrs['cell_methods'] = ps_cm
    else:
        logger.warn(
            "cell_methods not set: attributes either differ or are missing "
            "from input data"
        )

    # Set attributes
    # --------------

    hurs = hurs.assign_attrs({
        'standard_name': "relative_humidity",
        'long_name': "Near-Surface Relative Humidity",
        'comment': 'Calculated with pyku/metpy',
    })

    # Merge hurs to dataset
    # ---------------------

    ds = xr.merge([ds, hurs])

    return ds


def calc_huss(ds):

    """
    Calculate 'huss' from 'ps' and 'tdew'

    Arguments:
        ds (:class:`xarray.Dataset`): The Input data containing 'ps' and
            'tdew'.

    Returns:
        :class:`xarray.Dataset`: The dataset including tdew.
    """

    import textwrap
    import metpy
    import metpy.calc
    import xarray as xr
    import pyku.drs as drs
    import pyku.meta as meta

    # Check if variables are in the dataset
    # -------------------------------------

    if 'huss' in ds.data_vars:

        raise Exception("Variable hurs is already in the dataset")

    if 'ps' not in ds.data_vars or 'tdew' not in ds.data_vars:

        message = textwrap.dedent(
            f"""
            While trying to calculate 'huss', either 'ps' or 'tdew' is missing.
            Available variables are {ds.data_vars}.
            """)
        raise Exception(message)

    huss = metpy.calc.specific_humidity_from_dewpoint(
            ds['ps'], ds['tdew']
    ).rename('huss')

    # Dequantify and set attributes
    # -----------------------------

    huss = huss.metpy.dequantify()

    # Set units
    # ---------

    huss = drs.to_cmor_units(huss.to_dataset())['huss']

    # Set name of crs variable
    # ------------------------

    crs_varname = meta.get_crs_varname(ds)

    if crs_varname is not None:
        huss.attrs['grid_mapping'] = crs_varname

    # Set cell_method
    # ---------------

    ps_cm = ds.ps.attrs.get('cell_methods', None)
    tdew_cm = ds.tdew.attrs.get('cell_methods', None)

    if ps_cm and tdew_cm and (ps_cm == tdew_cm):
        huss.attrs['cell_methods'] = ps_cm
    else:
        logger.warn(
            "cell_methods not set: attributes either differ or are missing "
            "from input data"
        )

    # Set attributes
    # --------------

    huss = huss.assign_attrs({
        'standard_name': "specific_humidity",
        'long_name': "Near-Surface Specific Humidity",
        'comment': 'Calculated with pyku/metpy',
    })

    # Merge to dataset
    # ----------------

    ds = xr.merge([ds, huss])

    return ds


def calc_degreeday(ds, period=None, data_frequency=None, complete=False):

    """
    Add degree day to dataset, calculated from 'tas'

    Arguments:
        ds (:class:`xarray.Dataset`): The input data containing 'tas'.
        period (str):
            (Optional) Period, e.g. ``7D`` or ``1W``. For a full list, see
            https://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html#offset-aliases
            If '7D' is given, the degree-days are calculated over 7 days. If
            '1W' is given, the degree-days are calculated for each calender
            week.
        data_frequency (str):
            (Optional) data frequency: e.g. ``7D`` or ``1W``. For a full list,
            see https://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html#offset-aliases
            If not given explicitely, the data frequency is extracted from
            the data itself by looking at the time bounds, or calculated from
            the time labels.
        complete:
            (Optional) Use only complete data over the input period. For
            example, if ``period`` is 7 days and the data contains 16 days,
            only the first 14 days will be taken into account and the last 2
            days are discared.

    Returns:
        :class:`xarray.Dataset`: The dataset with degreeday included.
    """  # noqa

    import xarray as xr
    import warnings
    import textwrap
    import numpy as np
    import pyku.mask as mask
    import pyku.compute as compute

    # Keep data attributes over operations
    # ------------------------------------

    xr.set_options(keep_attrs=True)

    # Check units and convert if necessary
    # ------------------------------------

    if ds['tas'].attrs.get('units') is None:
        raise Exception('tas has not units in attributes')

    if 'celsius' not in [ds['tas'].attrs.get('units').lower()]:
        message = textwrap.dedent(
            """
            tas not in Celsius, checking if units ist Kelvins for conversion.
            """)
        warnings.warn(message)

        # Temperature
        # -----------

        if ds['tas'].attrs['units'].lower() in \
           ['K'.lower(), 'Kelvin'.lower(), 'Kelvins'.lower()]:
            ds['tas'] = ds['tas']-273.15
            ds['tas'].attrs['units'] = "Celsius"

        else:
            message = f"Unit not Kelvins, but {ds['tas'].attrs['units']}"
            raise Exception(message)

    # Get data mask
    # -------------

    da_mask = mask.get_mask(ds)

    # Define function and apply to dataset
    # ------------------------------------

    ds.load()

    # Copy dataset, calculate degreeday from tas, and rename
    # ------------------------------------------------------

    ds_out = ds.copy(deep=True)
    ds_out['tas'] = xr.apply_ufunc(
        lambda x: np.where(x < 15, 20-x, 0),
        ds['tas']
    )
    ds_out = ds_out.rename({'tas': 'gt'})

    # Set attributes
    # --------------

    ds_out['gt'].attrs = ds['tas'].attrs

    ds_out['gt'].attrs['units'] = 'K.d'
    ds_out['gt'].attrs['long_name'] = 'degree day'
    ds_out['gt'].attrs['standard_name'] = 'degree_day'

    if period is not None:

        # Resample
        # --------

        ds_out = compute.resample_datetimes(
            ds_out,
            how='sum',
            frequency=period,
            data_frequency=data_frequency,
            complete=complete
        )

        # Reset cell method after resampling
        # ----------------------------------

        ds_out['gt'].attrs['cell_methods'] = "time: sum"

    # Set data mask
    # -------------

    ds_out['gt'] = ds_out['gt'].where(da_mask == 0)

    return ds_out


def calc_globalwarminglevels(ds, GWL_levels=None, ref_period=None, navg=30,
                             GWL_temp_offset=0., cellarea=None):

    """
    Calculate  Global Warming Level central,
    start and end years, calculated from 'tas'

    Arguments:
        ds (:class:`xarray.Dataset`):
            Input data containing 'tas' spanning reference and future time
            period
        GWL_levels (list):
            List of Global Warming Levels e.g.: [1.5, 2.0, 4.0]
        ref_period (list):
            Start and end year of reference (pre-industrial) period
        navg (int):
            (Optional) Length of GWL period (n-year averaging) Default value
            set to 30 years
        GWL_temp_offset (float):
            (Optional) Temperature offset for GWL calculation accounting for
            observational warming until given reference period
        cellarea (:class:`xarray.DataArray`):
            (Optional) Array containing areas of grid cells for setting up the
            corresponding weights

    Returns:
        :class:`pandas.DataFrame`:
            Dataframe of global warming levels and their corresponding start,
            central and end years

    References:
        https://github.com/mathause/Chapter-11/blob/main/code/warming_levels.py

    Examples:

        .. ipython::
           :okwarning:

           In [0]: %%time
              ...: import pyku
              ...: ds = pyku.resources.get_test_data(
              ...:     'CCCma_CanESM2_Amon_world'
              ...: )
              ...: ds.pyku.calc_globalwarminglevels(
              ...:    GWL_levels = [1.5, 2, 3, 4],
              ...:    ref_period = [1850,1900]
              ...: )

        .. ipython::
           :okwarning:

           In [0]: %%time
              ...: ds.pyku.calc_globalwarminglevels(
              ...:    GWL_levels=[1.5, 2, 3, 4],
              ...:    ref_period=[1850,1900],
              ...:    navg=20
              ...: )
    """

    import numpy as np
    import pandas as pd
    import pyku.meta as meta

    # Deal with exceptions
    # --------------------

    if GWL_levels is None:
        raise Exception("GWL levels are not set")

    if ref_period is None:
        raise Exception("Reference period is not set")

    if not isinstance(navg, int) or navg < 1:
        raise ValueError("navg must be a positive integer, got {navg}")

    if not isinstance(GWL_temp_offset, (int, float)):
        message = """\
GWL_temp_offset must be a float, got {GWL_temp_offset}!
"""
        raise ValueError(message)

    if 'tas' not in meta.get_geodata_varnames(ds):
        raise Exception("Variable 'tas' is not a variable in the dataset")

    # Check GWL values
    # ----------------

    for val in GWL_levels:
        if not isinstance(val, (int, float)):
            raise Exception("Not all entries of GWL_levels are numeric!")

    GWL_levels = [float(val) for val in GWL_levels]

    # Check reference period
    # ----------------------

    for year in ref_period:
        try:
            year = int(year)
            continue
        except ValueError:
            raise Exception("Given start and/or end year of " +
                            "reference period is not an integer!")

    # Get correct names of geographic latitude and longitude
    # ------------------------------------------------------

    latlon_name = meta.get_geographic_latlon_varnames(ds)

    # Set correct area weighting
    # --------------------------

    if cellarea is None:
        weights = np.cos(np.deg2rad(ds[latlon_name[0]]))
    else:
        weights = cellarea

    weights.name = "weights"

    tas = ds['tas']

    # Calculate temperature within reference period
    # ---------------------------------------------

    seltime = slice(str(ref_period[0])+'-01-01',
                    str(ref_period[1])+'-12-30')

    tas_ref_period = tas.sel(time=seltime).weighted(weights).mean()

    # compute anomalies
    # -----------------

    anomalies = tas.weighted(weights).mean(dim=latlon_name) - tas_ref_period

    # set
    if navg % 2 != 0:  # odd
        beg_offset = end_offset = (navg - 1) // 2
    else:  # even
        beg_offset = navg // 2
        end_offset = navg // 2 - 1

    fac = 1  # factor
    if ds.attrs.get('frequency') not in ['day', 'mon', 'year']:
        raise Exception("The function only works if frequency  is set " +
                        "as a global attribute. User shall ensure " +
                        "the data frequency matches.")

    if ds.attrs['frequency'] == 'mon':
        fac = 12

    if ds.attrs['frequency'] == 'day':
        fac = 365
        logger.warn("Detected data frequency is 'day', " +
                    "assuming a 365-day calendar on the underlying data.")

    # Calculate temperature anomalies
    # -------------------------------

    anomalies = anomalies.rolling(time=navg*fac,
                                  center=True).mean(dim=latlon_name)

    # Find years warmer than 'warming_level'
    # --------------------------------------

    GWL_years = {}

    # Think about adding the global model simulation to dict...
    # use global attributes of CMIP5/6 experiments to identify simulation

    # CMIP6: [source_ID]_[parent_variant_label]_[experiment_id]
    # CMIP5:

    for warming_level in GWL_levels:

        sel = anomalies - warming_level > 0.0

        # If no warmer year is found, return None
        # ---------------------------------------

        if not sel.any():
            GWL_years[warming_level] = [None, None, None]
            continue

        # Find index of central year
        # --------------------------

        idx = sel.argmax().values
        central_year = int(anomalies.isel(time=idx).time.dt.year.values)
        beg = int(central_year - beg_offset)
        end = int(central_year + end_offset)
        GWL_years[warming_level] = [beg, central_year, end]

    df_GWL = pd.DataFrame(data=GWL_years)

    return df_GWL


def calc_ssim(mean_ref, mean_model, variance_ref, variance_model,
              covariance, c1=1e-8, c2=1e-8):

    """
    Calculate Structural Similarity Index Measure

    Arguments:
        mean_ref (float): mean for reference values
        mean_model (float): mean for sample values
        variance_ref (float): variance for reference values
        variance_model (float): variance for sample values
        covariance (float): covariance for reference and sample values
        c1 (float): constant 1
        c2 (float): constant 2

    Returns:
        SSIM (float): Structural Similarity Index Measure

    References: Wang et al. 2004 (DOI: 10.1109/tip.2003.819861)
        with modifications c1 and c2 in default 1e-8 as suggested by
        Baker et al. 2022 (abs/2202.02616) to give the equal weight to the
        luminance and contrast components of SSIM and modification of
        Dalelane et al. (modref)
    """

    import numpy as np

    SSIM = (
            (2*mean_ref*mean_model+c1)*(2*covariance+c2)
        ) / (
            (np.square(mean_ref)+np.square(mean_model)+c1) *
            (variance_ref+variance_model+c2)
        )  # noqa

    return SSIM


def persistent_processing(
    func, files=None, tmpdir=None, identifier='pyku', persist=False,
    engine=None, unify_chunks=True, chunks={'time': -1}, extension='nc'
  ):

    """
    Apply a function to a list of files, save the results in a temporary
    directory, and return the names of the processed files.

    This function enables efficient data processing by applying a user-defined
    function to each file in the input list. The processed files are stored in
    a temporary directory, and their paths are returned. It optimizes memory
    usage by chunking large datasets and processing them in smaller, manageable
    segments, especially useful for computationally expensive tasks or
    multiprocessing.

    If the frequency cannot be inferred and the dataset size is large, an
    hourly frequency is assumed, and files are split into one-year segments.
    For smaller datasets, the original dataset is returned without
    modifications.

    Key Benefits:
    * Optimized for large datasets and heavy computations.
    * Supports multiprocessing with chunked data.
    * Simplifies debugging by breaking down large files into smaller chunks.

    Arguments:
        func (function): A function that accepts and returns an
            :class:`xarray.Dataset`.
        files (list): A list of input data files to process.
        tmpdir (str): Path to the temporary directory for processed files.
        unify_chunks (bool): If True, synchronizes chunking across all dataset
            variables to prevent computation overhead and alignment errors.
            Note: This may increase initial memory usage and task graph
            complexity if the data are not chunked properly.
        chunks (dict): Specifies dimension-to-size mapping for data
            partitioning. Defaults to unchunked (single chunk) along the time
            dimension.
        identifier (str, optional): A string identifier to include in processed
            file names (default: 'pyku').
        extension (str, optional): Format for the output files, either nc or
            zarr

    Returns:
        list: A list of paths to the processed files.

    Examples:

        .. ipython::
           :okwarning:

           In [0]: import xarray as xr
              ...: import pyku
              ...: import tempfile
              ...: import pyku.resources
              ...: import pyku.compute
              ...:
              ...: # Define list of files
              ...: # --------------------
              ...:
              ...: files = pyku.resources.get_test_data("monthly_hyras_files")
              ...:
              ...: # Create a temporary directory
              ...: # ----------------------------
              ...:
              ...: # Alternatively, define your own directory where data
              ...: # should be located. Here since this jupyter notebook
              ...: # runs automatically, I merely intend to use the cleanup
              ...: # function the the tempfile library.
              ...:
              ...: temp_dir = tempfile.TemporaryDirectory()
              ...:
              ...: # Show the temporary directory name
              ...: # ---------------------------------
              ...:
              ...: print("Temporary directory:", temp_dir.name)
              ...:
              ...: # Get Polygon for Germany
              ...: # -----------------------
              ...:
              ...: germany_polygon = pyku.resources.get_geodataframe('germany')
              ...:
              ...: # Define a preprocessing function
              ...: # -------------------------------
              ...:
              ...: def preprocessing(ds):
              ...:     ds = ds.pyku.project('HYR-LAEA-5')
              ...:     ds = ds.pyku.apply_mask(germany_polygon)
              ...:     return ds
              ...:
              ...: # Semi-permanently preprocess the files
              ...: # -------------------------------------
              ...:
              ...: preprocessed_files = pyku.compute.persistent_processing(
              ...:     func=preprocessing,
              ...:     files=files,
              ...:     tmpdir=temp_dir.name,
              ...:     identifier='my-pre-processed-data',
              ...: )
              ...:
              ...: # Print list of preprocessed files
              ...: # --------------------------------
              ...:
              ...: print(preprocessed_files)
              ...:
              ...: # Cleanup the temporary directory
              ...: # -------------------------------
              ...:
              ...: temp_dir.cleanup()
    """

    import pathlib
    import hashlib
    import os
    import xarray as xr
    import pyku.timekit as timekit
    import dask
    import glob
    from dask import delayed
    from pathlib import Path
    from dask.distributed import default_client
    import gc

    # Deal with exceptions
    # --------------------

    if tmpdir is None:
        raise Exception("tmpdir is not set")

    if identifier is None:
        raise Exception("identifier is not set")

    if files is None:
        raise Exception("files is None")

    if persist is True:
        logger.warning("Parameter 'persist' is deprecated and has no effects")

    # If Dask client already created in parent code, use it
    # -----------------------------------------------------

    try:
        client = default_client()

    except ValueError:
        logger.info("Not using multiprocessing")

    def identify_files():

        """
        Identify three categories of files: Files that have been processed
        ('processed_files'), files pending preprocessing (unprocessed_files),
        and the files produced by preprocessing (produced_files). Note that
        "files that have been processed" and "files produced by preprocessing"
        are not necessarily identical, as large files will be divided into
        smaller packets during preprocessing in order to fit in memory.

        Returns:

            Tupe(str, str, str): produced_files, unprocessed_files,
            processed_files
        """

        # Prepare list of output produced files
        # -------------------------------------

        produced_files = []

        # Prepare list of files which have not been processed yet
        # -------------------------------------------------------

        unprocessed_files = []

        # Prepare list for files which have been processed already
        # --------------------------------------------------------

        processed_files = []

        # Loop over all files to be processed
        # -----------------------------------

        for unprocessed_file in files:

            # Calculate the checksum of the file
            # ----------------------------------

            checksum = hashlib.md5(
                open(unprocessed_file, 'rb').read(2000)
            ).hexdigest()

            suffix = extension
            stem = pathlib.Path(unprocessed_file).stem

            # Determine the names of the files already produced
            # -------------------------------------------------

            existing_processed_files = glob.glob(
                os.path.join(
                    tmpdir,
                    f"{stem}-{identifier}-{checksum}-????????.{suffix}"
                )
            )

            # Add to list of produced output files
            # ------------------------------------

            produced_files.extend(existing_processed_files)

            # Append list of files already processed, or still to be processed
            # ----------------------------------------------------------------

            if len(existing_processed_files) == 0:
                unprocessed_files.append(unprocessed_file)
            else:
                processed_files.append(unprocessed_file)

        return produced_files, unprocessed_files, processed_files

    produced_files, unprocessed_files, processed_files = identify_files()

    # Define parallelized function to process files
    # ---------------------------------------------

    @delayed
    def delayed_process_file(unprocessed_file):
        process_file(unprocessed_file)

    def process_file(unprocessed_file):

        """
        Perform processing.

        Arguments:
            unprocessed_files (List[str]): List of unprocessed files.
        """

        import pyku.magic as magic

        # Open file
        # ---------

        unprocessed_dataset = xr.open_dataset(
            unprocessed_file,
            engine=engine
        )

        # Split in packets based on datetimes and apply processing function
        # -----------------------------------------------------------------

        for splinter_idx, splinter in enumerate(
            timekit.split_by_datetimes(unprocessed_dataset)
        ):

            processed_data = func(splinter)

            checksum = hashlib.md5(
                open(unprocessed_file, 'rb').read(2000)
            ).hexdigest()

            stem = pathlib.Path(unprocessed_file).stem

            # Determine file name
            # -------------------

            written_file = Path(tmpdir) / Path(
                f"{stem}-{identifier}-{checksum}-{splinter_idx:08d}"
                f".{extension}"
            )

            # Unify chunks and unchunk
            # ------------------------

            if 'time' not in processed_data.dims:
                logger.warn(
                    "The 'time' dimension is missing. This function is "
                    "specifically designed for datasets with a temporal "
                    "component."
                )

            if unify_chunks is True:
                processed_data = processed_data.unify_chunks()

            processed_data = processed_data.chunk(chunks=chunks)

            # Write to disk
            # -------------

            if extension in ['zarr']:
                magic.to_zarr(
                    processed_data,
                    written_file,
                )
            elif extension in ['nc']:
                magic.to_netcdf(
                    processed_data,
                    written_file,
                )
            else:
                raise ValueError(
                    f"Unsupported extension '{extension}': Output must be "
                    "either 'nc' or 'zarr'."
                )
            processed_data.close()
            del processed_data
            gc.collect()

        # End function
        # ------------

        unprocessed_dataset.close()
        del unprocessed_dataset
        gc.collect()

        return

    # If no dask client is available, process the files
    # -------------------------------------------------

    if 'client' not in locals():

        for file in unprocessed_files:
            process_file(file)

    # Otherwise process the files using the dask client
    # -------------------------------------------------

    else:
        # List of delayed computations
        # ----------------------------

        delayed_results = [
            delayed_process_file(file) for file in unprocessed_files
        ]

        # Retrieve the actual result
        # --------------------------

        dummy_results = client.gather(delayed_results)

        # Collect
        # -------

        _ = [result for result in dummy_results]

        # Compute delayed results using dask
        # ----------------------------------

        _ = dask.compute(*delayed_results)

    # After processing has run on all files, identify the files
    # ---------------------------------------------------------

    produced_files, unprocessed_files, processed_files = identify_files()

    # Return list of preprocessed files if all were processed already
    # ---------------------------------------------------------------

    return produced_files
