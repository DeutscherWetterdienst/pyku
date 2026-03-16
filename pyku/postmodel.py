#!/usr/bin/env python3

"""
pyku functions to post-process models
"""


def derotate(ds):

    # {{{

    """
    Derotate wind components

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset.
        uname (str): U component.
        vname (str): V component.
    Returns:
        :class:`xarray.Dataset`: The dataset with derotated wind components.
    """

    import xarray as xr
    import warnings
    import os

    # Search variables to be derotated
    # --------------------------------

    uvars = []
    vvars = []

    for var in ds.pyku.get_geodata_varnames():

        standard_name = ds[var].attrs.get('standard_name')

        if standard_name in ['grid_eastward_wind']:
            uvars.append(var)

        if standard_name in ['grid_northward_wind']:
            vvars.append(var)

    # If no variables need derotation, return
    # ---------------------------------------

    if len(uvars) < 1 and len(vvars) < 1:
        return ds

    # Ensure only one variable for grid_eastwar_wind and grid_northward_wind
    # ----------------------------------------------------------------------

    if len(uvars) > 1:
        message = """\
Found multiple variables ({uvars}) with standard_name==grid_eastward_wind. This
is not supported"""
        raise Exception(message)

    if len(vvars) > 1:
        message = """\
Found multiple variables ({vvars}) with standard_name==grid_northward_wind.
This is not supported"""
        raise Exception(message)

    # Only one variable is present in each list. Set uname and vname
    # --------------------------------------------------------------

    uname = uvars[0]
    vname = vvars[0]

    # Send a warning because cdo is used in the background
    # ----------------------------------------------------

    warnings.warn("""\\
Use of cdo bindings is discouraged in pyku. The dask graph for multiprocessing
can not be passed and hence can severly degrade the performance of pyku. Use
with parcimony.""")

    # Try to load cdo and require it to be installed if not available
    # ---------------------------------------------------------------

    try:
        import cdo

    except ImportError:
        cdo = None

    if cdo is None:
        message = """To use the cdo bindings: pip install cdo"""
        raise Exception(message)

    # Set environment variable
    # ------------------------

    os.environ["IGNORE_ATT_COORDINATES"] = "1"

    # Start CDO
    # ---------

    from cdo import Cdo

    cdo = Cdo()

    if 'rotated_pole' not in ds.data_vars:
        message = "crs rotated_pole not found in dataset. can't unrotate"
        raise Exception(message)

    # Select needed variables
    # -----------------------

    prepared = ds[[uname, vname, 'rotated_pole']]

    # Derotate
    # --------

    derotated = cdo.rotuvb(
        uname, vname, input=prepared, returnXDataset='dataset'
    )

    # Reset attributes
    # ----------------

    # Only the standard name is reset, because we expect for the long name
    # 'U-component of 10m wind' instead of 'Eastward Near-Surface Wind' or
    # 'Northward Wind'. It is left as is since it is strictly correct.

    derotated[uname].attrs['standard_name'] = 'eastward_wind'
    derotated[vname].attrs['standard_name'] = 'northward_wind'

    # Drop also 'rotated_pole'
    # ------------------------

    derotated = derotated.drop('rotated_pole')

    # Drop old variables from original dataset
    # ----------------------------------------

    ds = ds.drop([uname, vname])

    # Merge derotated variables into the original dataset
    # ---------------------------------------------------

    ds = xr.merge([ds, derotated])

    # Unset cdo environment variable
    # ------------------------------

    del os.environ["IGNORE_ATT_COORDINATES"]

    return ds

    # }}}


def post(ds):

    # {{{

    """
    Extend model output:

    * If *U*, *V*, and pressure levels are present, build *U850p* and *V850p*,
      *U500p* and *V500p*, *U200p* and *V200p*.
    * If *U*, *V*, and height levels are present, build *U100m* and *V100m*.
    * if *ASWDIR_S* and *ASWDIFD_S* are present, build *ASWD_S*.
    * if *FR_SNOW*, build *W_SNOW*.

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset.
    Returns:
        :class:`xarray.Dataset`: The dataset with extended output.
    """

    import xarray as xr
    import numpy as np
    import warnings

    # Add level variables
    # -------------------

    # {{{

    if 'U' in ds.data_vars and 'V' in ds.data_vars:

        if 'pressure' in dict(ds.dims).keys():

            if 85000. in ds.pressure:
                print('Building U850p and V850p')

                ds = ds.assign(
                    U850p=ds['U'].sel(pressure=85000.).drop('pressure'))

                ds = ds.assign(
                    V850p=ds['V'].sel(pressure=85000.).drop('pressure'))

            if 50000. in ds.pressure:
                print('Building U500p and V500p')

                ds = ds.assign(
                    U500p=ds['U'].sel(pressure=50000.).drop('pressure'))

                ds = ds.assign(
                    V500p=ds['V'].sel(pressure=50000.).drop('pressure'))

            if 20000. in ds.pressure:
                print('Building 2500p and V200p')

                ds = ds.assign(
                    U200p=ds['U'].sel(pressure=20000.).drop('pressure'))

                ds = ds.assign(
                    V200p=ds['V'].sel(pressure=20000.).drop('pressure'))

        if 'height' in dict(ds.dims).keys():

            if 100. in ds.height:
                print('Building U100z and V100z')

                ds = ds.assign(U100z=ds['U'].sel(height=100.).drop('height'))
                ds = ds.assign(V100z=ds['V'].sel(height=100.).drop('height'))

    # }}}

    # Add ASWD_S
    # ----------

    # {{{

    if 'ASWDIR_S' in ds.data_vars and 'ASWDIFD_S' in ds.data_vars:

        print("Building ASWD_S")

        # Calculate
        # ---------

        ds = ds.assign(ASWD_S=ds['ASWDIR_S'] + ds['ASWDIFD_S'])

        # Set attributes for new variable
        # -------------------------------

        ds['ASWD_S'].attrs['units'] = 'W m-2'

        ds['ASWD_S'].attrs['cell_methods'] = \
            ds['ASWDIR_S'].attrs.get('cell_methods')

        ds['ASWD_S'].attrs['grid_mapping'] = \
            ds['ASWDIR_S'].attrs.get('grid_mapping')

        ds['ASWD_S'].attrs['long_name'] = \
            'Surface Downwelling Shortwave Radiation'

        ds['ASWD_S'].attrs['standard_name'] = \
            'surface_downwelling_shortwave_flux_in_air'

    # }}}

    # Add SP_10M
    # ----------

    # {{{

    if 'U_10M' in ds.data_vars and 'V_10M' in ds.data_vars:

        print("Building SP_10M")

        u_std_name = ds['U_10M'].attrs.get('standard_name')
        v_std_name = ds['V_10M'].attrs.get('standard_name')
        if u_std_name in ['grid_eastward_wind', 'grid_northward_wind'] or \
           v_std_name in ['grid_eastward_wind', 'grid_northward_wind']:

            message = f"""\
Standard name for U_10M is {ds['U_10M'].attrs['standard_name']} and standard
name for V_10M is {ds['V_10M'].attrs['standard_name']}! Are re you using
rotated lat/lon coordinates and you forgot to derotate your data? If the data
were derotated already, 'standard_name' attributes must be manually changed
before using the function. Or youcan use the pyku postmodel derotate
function"""
            warnings.warn(message)

        # Calculate windspeed
        # -------------------

        ds = ds.assign(
            SP_10M=np.sqrt(np.power(ds['U_10M'], 2) + np.power(ds['V_10M'], 2))
        )

        # Set attributes for new variable
        # -------------------------------

        ds['SP_10M'].attrs['units'] = \
            ds['U_10M'].attrs.get('units')

        ds['SP_10M'].attrs['cell_methods'] = \
            ds['U_10M'].attrs.get('cell_methods')

        ds['SP_10M'].attrs['grid_mapping'] = \
            ds['U_10M'].attrs.get('grid_mapping')

        ds = ds.pyku.to_cmor_attrs()

    # }}}

    # Add FR_SNOW
    # -----------

    # {{{

    if 'W_SNOW' in ds.data_vars:

        print("Building FR_SNOW")

        # Formulation
        # -----------

        # Max(0.01,Min(1.,W_SNOW/0.015))*H(x)
        # with H(x)=1 if W_SNOW>0.5E-06, else H(x)=0

        # Calculate windspeed
        # -------------------

        binarized_wsnow = xr.apply_ufunc(
            np.where, ds['W_SNOW'] > 0.5E-07, 1., 0., dask='allowed'
        )

        ds = ds.assign(
            FR_SNOW=np.maximum(
                0.01,
                np.minimum(1., ds['W_SNOW']/0.015)
            ) * binarized_wsnow
        )

        # Set attributes for new variable
        # -------------------------------

        ds['FR_SNOW'].attrs['units'] = '1'

        ds['FR_SNOW'].attrs['cell_methods'] = \
            ds['W_SNOW'].attrs.get('cell_methods')

        ds['FR_SNOW'].attrs['grid_mapping'] = \
            ds['W_SNOW'].attrs.get('grid_mapping')

        ds = ds.pyku.to_cmor_attrs()

    # }}}

    return ds

    # }}}
