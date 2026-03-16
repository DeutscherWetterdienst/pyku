#!/usr/bin/env python3

"""
Downscaling library
"""

from . import logger


class Downscaler:

    """
    Parent class for downscalers.

    The purpose of this class is to gather high-level optimized functions.
    """

    def groupby_fit_predict_all_variables(
            self, lowres, groupby_type='time.month', progress=False):

        """
        Group, fit and predict

        Arguments:

            ds (:class:`xarray.Dataset`): Dataset to downscale.

            groupby_type (string): Data grouping. The correction is applied
                independently to each group. The value of the groupby_type is
                expected to be 'time.month', but could also be set to
                'time.season'
        """

        import pyku.meta as libmetadata
        import xarray as xr

        svds = []

        for var in libmetadata.get_geodata_varnames(lowres):

            if progress is True:
                print(f"{var}")

            corrector_svd = SVDDownscaler(
                high_res=self.ds_obs_hr[[var]],
                low_res=self.ds_obs_lr[[var]],
                max_nsvs=self.max_nsvs,
            )

            svds.append(corrector_svd.groupby_fit_predict(
                lowres[[var]],
                groupby_type=groupby_type,
                progress=progress
            ))

        ds_svd = xr.merge(svds)

        return ds_svd

    def groupby_fit_predict(
            self, lowres, groupby_type='time.month', progress=False):

        """
        Group, fit and predict

        Arguments:

            ds (:class:`xarray.Dataset`): Dataset to downscale.

            groupby_type (string): Data grouping. The correction is applied
                independently to each group. The value of the groupby_type is
                expected to be 'time.month', but could also be set to
                'time.season'
        """

        import gc
        import xarray as xr

        # Group by type
        # -------------

        obs_hr_group = self.ds_obs_hr.groupby(groupby_type)
        obs_lr_group = self.ds_obs_lr.groupby(groupby_type)
        mod_lr_group = lowres.groupby(groupby_type)

        # Gather the correction of all groups in a list
        # ---------------------------------------------

        all_groups = []

        # Loop over all groups and correct
        # --------------------------------

        for key in mod_lr_group.groups.keys():

            print(f"Downscaling group {key}")

            # Create temporary corrector for group
            # ------------------------------------

            if self.interp_method_id in ['svd']:

                corrector = SVDDownscaler(
                    low_res=obs_lr_group[key],
                    high_res=obs_hr_group[key],
                    max_nsvs=self.max_nsvs
                )

            else:
                message = f"Method {self.inter_method_id} not implemented"
                raise Exception(message)

            # Fit
            # ---

            corrector.fit()

            # Predict and append to list of results
            # -------------------------------------

            all_groups.append(
                corrector.predict(mod_lr_group[key])
            )

            # Clean up
            # --------

            del corrector
            gc.collect()

        # Merge
        # -----

        # In order to improve memory usage, the correction is computed, which
        # permits to delete all groups.

        correction = xr.concat(all_groups, dim='time').compute()
        del all_groups
        gc.collect()

        # Sort datetimes
        # --------------

        correction = correction.sortby('time')

        return correction


class SVDDownscaler(Downscaler):

    """
    Downscaler with singular value decomposition (SVD).

    .. note::

       Using a multivariable SVD was tried. It kinda worked but results were
       not convincing and was henced removed. The code can still be found in
       the old clutils repository.
    """

    def __str__(self):

        import textwrap

        return textwrap.dedent(
            f"""
            SVD Downscaler

            Number of singular values: {self.nsvs}
            """
        )

    def __init__(self, high_res, low_res, max_nsvs):

        """
        Class initialization

        Arguments:

            high_res (:class:`xarray.Dataset`): High resolution reference
                training data in high resolution target projection

            low_res (:class:`xarray.Dataset`): Low resolution reference
                training data in low resolution source projection

            max_nsvs (int): Maximal number of singular values

        """

        import textwrap
        import datetime
        import pandas as pd
        import pyku.meta as libmetadata

        self.ds_obs_hr = high_res
        self.ds_obs_lr = low_res
        self.svds = {}
        self.max_nsvs = max_nsvs

        # Get name of data variables
        # --------------------------

        self.obs_varnames = sorted(
            libmetadata.get_geodata_varnames(self.ds_obs_lr)
        )

        # Set metadata
        # ------------

        self.interp_method_id = 'svd'
        self.interp_method = textwrap.dedent(
            """
            Singular value decomposition
            """
        ).strip()

        self.creation_date = datetime.datetime.now().strftime("%Y-%m-%d")

        # Get calibration period both as string and datetime
        if 'time' in self.ds_obs_lr.dims:

            cal_begin_yyyy = pd.Timestamp(
                min(self.ds_obs_lr.time.values)
            ).strftime("%Y")

            cal_end_yyyy = pd.Timestamp(
                max(self.ds_obs_lr.time.values)
            ).strftime("%Y")

            self.interp_period = f'{cal_begin_yyyy}-{cal_end_yyyy}'

        else:
            self.interp_period = 'Not applicable'

    def fit(self):

        """
        Fit
        """

        import pyku.meta as meta

        # Get projection and geographic coordinate names
        # ----------------------------------------------

        # This is taken for low resolution (lr) and high resolution (hr)
        # datasets.

        y_name_lr, x_name_lr = \
            meta.get_projection_yx_varnames(self.ds_obs_lr)

        y_name_hr, x_name_hr = \
            meta.get_projection_yx_varnames(self.ds_obs_hr)

        # Sanity check
        # ------------

        assert y_name_lr == y_name_hr, \
            "y_name not the same for low and high resolution datasets"

        assert x_name_lr == x_name_hr, \
            "x_name not the same for low and high resolution datasets"

        # Set projection and geographic coordinate names
        # ----------------------------------------------

        y_name = y_name_lr
        x_name = x_name_lr

        # Loop over data variables
        # ------------------------

        logger.debug(
            "Marker it should be checked why lat and lon are not included")

        for varname in self.obs_varnames:

            # Perform SVD decomposition
            # -------------------------

            # Marker here it should be possible to use pyku.get_geodataset I
            # think, which would clean up the code and we would have no need
            # for y_name and x_name

            ds_obs_hr = self.ds_obs_hr[[varname, 'time', y_name, x_name]]
            ds_obs_lr = self.ds_obs_lr[[varname, 'time', y_name, x_name]]

            ntimes_hr = len(ds_obs_hr.coords['time'])
            ntimes_lr = len(ds_obs_lr.coords['time'])

            self.svds[varname] = SVD(
                high_res=ds_obs_hr[varname].values.reshape((ntimes_hr, -1)),
                low_res=ds_obs_lr[varname].values.reshape((ntimes_lr, -1)),
                max_nsvs=self.max_nsvs
            )

            self.svds[varname].fit()

    def predict(self, data):

        """
        Predict
        """

        import dask.array as dk
        import xarray as xr

        # Gather downscaled DataArrays in a list
        # --------------------------------------

        downscaled_ds_list = []

        # Loop over data variables
        # ------------------------

        logger.debug("Marker: dependence on 'x' and 'y' to be removed")

        for varname in self.obs_varnames:

            # Return exception is the number of NaNs does not match
            # -----------------------------------------------------

            count_obs_low_res = dk.count_nonzero(
                dk.isnan(self.ds_obs_lr.isel(time=0)[varname].data.reshape(-1))
            ).compute()

            count_dat_low_res = dk.count_nonzero(
                dk.isnan(data[varname].isel(time=0).data.reshape(-1))
            ).compute()

            if count_dat_low_res != count_obs_low_res:

                raise Exception(
                    "The number of NaNs in the first timestep of thelow "
                    f"resolution training data is {count_obs_low_res} while "
                    "the number of NaNs in the first timestemp of the dataset "
                    f"to be downscaled is {count_dat_low_res}. This likely "
                    "indicates that the mask is not the same for both "
                    "datasets, while it should be."
                )

            # Select and order data dimensions
            # --------------------------------

            # Marker: In places like this, libmetadata can and should be used
            da = data[[varname, 'time', 'y', 'x']]

            # Get data dimension length
            # -------------------------

            ny_hr = len(self.ds_obs_hr.coords['y'])
            nx_hr = len(self.ds_obs_hr.coords['x'])

            ntimes = len(data[varname].coords['time'])

            np_out = self.svds[varname].predict(
                da[varname].values.reshape(ntimes, -1)
            )

            da_out = xr.DataArray(
                name=f'{varname}',
                data=np_out.reshape(ntimes, ny_hr, nx_hr),
                dims=['time', 'y', 'x'],
                coords={
                    'time': (["time"], data.coords['time'].values),
                    'y':    (["y"], self.ds_obs_hr.coords['y'].values),
                    'x':    (["x"], self.ds_obs_hr.coords['x'].values),
                    'lat':  (["y", "x"], self.ds_obs_hr.coords['lat'].values),
                    'lon':  (["y", "x"], self.ds_obs_hr.coords['lon'].values)
                },
                attrs=self.ds_obs_hr[varname].attrs
            )

            # Append data to list
            # -------------------

            downscaled_ds_list.append(da_out)

        # Merge downscaled data to DataSet and return
        # -------------------------------------------

        ds_downscaled = xr.merge(downscaled_ds_list)

        # Copy attributes
        # ---------------

        ds_downscaled.attrs = data.attrs

        # Set attributes
        # --------------

        ds_downscaled.attrs['interp_method_id'] = self.interp_method_id
        ds_downscaled.attrs['interp_method'] = self.interp_method
        ds_downscaled.attrs['interp_period'] = self.interp_period
        ds_downscaled.attrs['creation_date'] = self.creation_date

        return ds_downscaled

    def eigenvectors(self):

        """
        Eigenvectors

        Returns:
            :class:`xarray.Dataset` containing the eigenvectors
        """

        import xarray as xr

        # Prepare list of DataArrays for low and high resolution eigenvectors
        # -------------------------------------------------------------------

        lr_das = []
        hr_das = []

        # Loop over variables, get eigenvectors, create DataArrays
        # --------------------------------------------------------

        logger.debug(
            "Marker. Here 'y' and 'x' dependence should be streamlined")

        for var in self.obs_varnames:

            lr_eigen, hr_eigen = self.svds[var].eigenvectors()

            ny_lr = len(self.ds_obs_lr.coords['y'])
            nx_lr = len(self.ds_obs_lr.coords['x'])

            ny_hr = len(self.ds_obs_hr.coords['y'])
            nx_hr = len(self.ds_obs_hr.coords['x'])

            nsvs_hr = hr_eigen.shape[0]
            nsvs_lr = lr_eigen.shape[0]

            lr_da = xr.DataArray(
                name=f'{var}',
                data=lr_eigen.reshape((nsvs_lr, ny_lr, nx_lr)),
                dims=['nsvs', 'y', 'x'],
                coords={
                    'nsvs': (["nsvs"], range(nsvs_lr)),
                    'y': (["y"], self.ds_obs_lr.coords['y'].values),
                    'x': (["x"], self.ds_obs_lr.coords['x'].values),
                    'lat': (["y", "x"], self.ds_obs_lr.coords['lat'].values),
                    'lon': (["y", "x"], self.ds_obs_lr.coords['lon'].values)
                },
                attrs={
                    'description': 'low resolution eigenvectors'
                }
            )

            hr_da = xr.DataArray(
                name=f'{var}',
                data=hr_eigen.reshape((nsvs_hr, ny_hr, nx_hr)),
                dims=['nsvs', 'y', 'x'],
                coords={
                    'nsvs': (["nsvs"], range(nsvs_hr)),
                    'y': (["y"], self.ds_obs_hr.coords['y'].values),
                    'x': (["x"], self.ds_obs_hr.coords['x'].values),
                    'lat': (["y", "x"], self.ds_obs_hr.coords['lat'].values),
                    'lon': (["y", "x"], self.ds_obs_hr.coords['lon'].values)
                },
                attrs={
                    'description': 'high resolution eigenvectors'
                }
            )

            lr_das.append(lr_da)
            hr_das.append(hr_da)

        # Return list as dataset
        # ----------------------

        return xr.merge(lr_das), xr.merge(hr_das)


class SVD:

    """
    Singular Value Decomposition (SVD)
    """

    def __str__(self):

        import textwrap

        return textwrap.dedent(
            f"""
            Singular Value Decomposition (SVD)

            Number of singular values {self.max_nsvs}
            """
        )

    def __init__(self, high_res, low_res, max_nsvs=None):

        """
        Class initialization

        Arguments:

            high_res (:class:`numpy.ndarray`): High resolution training data
            low_res (:class:`numpy.ndarray`): Low resolution training data
        """

        self.high_res = high_res
        self.low_res = low_res

        self.lr_U = None
        self.lr_Ur = None  # Economy matrix
        self.lr_S = None
        self.lr_S_inverse = None
        self.lr_Vh = None

        self.hr_U = None
        self.hr_Ur = None  # Economy matrix
        self.hr_S = None
        self.hr_S_inverse = None
        self.hr_Vh = None

        self.hr_ny = None
        self.hr_nx = None

        self.max_nsvs = max_nsvs

    def fit(self):

        """
        Fit with singular value decomposition (SVD)
        """

        from scipy import linalg
        import numpy as np

        # Get numpy array from DataArray
        # ------------------------------

        lr_ntimes_x_nsamples_nan = self.low_res
        hr_ntimes_x_nsamples_nan = self.high_res

        # Get new npcs_x_nsample without NaNs
        # -----------------------------------

        lr_ntimes_x_nsamples_num = lr_ntimes_x_nsamples_nan[
            :, ~np.isnan(lr_ntimes_x_nsamples_nan).any(axis=0)
        ]

        lr_nsamples_x_ntimes_num = lr_ntimes_x_nsamples_num.T

        # Perform SVD on low resolution observation data
        # ----------------------------------------------

        # The left U matrix has size m x m, the right V matrix size n x n, and
        # s are the singular values

        self.lr_U, lr_s, self.lr_Vh = linalg.svd(lr_nsamples_x_ntimes_num)

        # Get the canonical matrix shapes m, n
        # ------------------------------------

        m = self.lr_U.shape[0]
        n = self.lr_Vh.shape[0]

        # Calculate the m x n singular values matrix
        # ------------------------------------------

        self.lr_S = np.zeros((m, n), dtype=self.low_res.dtype)
        np.fill_diagonal(self.lr_S, lr_s)

        # Calculate inverse n x m singular values matrix
        # ----------------------------------------------

        lr_s_inverse = 1/lr_s

        self.lr_S_inverse = np.zeros((n, m), dtype=self.low_res.dtype)
        np.fill_diagonal(self.lr_S_inverse, lr_s_inverse)

        # Transform high resolution observation data
        # ------------------------------------------

        hr_nsamples_x_ntimes_nan = hr_ntimes_x_nsamples_nan.T

        self.hr_U = hr_nsamples_x_ntimes_nan @ self.lr_Vh.T @ self.lr_S_inverse

    def predict(self, data):

        """
        Predict with singular value decomposition (SVD)

        Arguments:

            data (:class:`numpy.ndarray`): data to be recomposed with size
                                           (ntimes x nsamples).

        Returns:
            :class:`numpy.ndarray`: predicted values with shape
                                    (ntimes x nsamples)

        Notes:
            Practically the data input have shapes (ntimes x ny*nx) or
            (ntimes x nvars*ny*nx)
        """

        import numpy as np

        # Rename for clarity
        # ------------------

        lr_ntimes_x_nsamples_nan = data

        lr_ntimes = lr_ntimes_x_nsamples_nan.shape[0]

        # Get data without nans
        # ---------------------

        lr_ntimes_x_nsamples_num = lr_ntimes_x_nsamples_nan[
            ~np.isnan(lr_ntimes_x_nsamples_nan)
        ]

        lr_ntimes_x_nsamples_num = \
            lr_ntimes_x_nsamples_num.reshape(lr_ntimes, -1)

        # Select the number of eigenvectors used
        # --------------------------------------

        if self.max_nsvs is not None and self.max_nsvs <= self.lr_S.shape[0]:

            # Truncate the Matrix to a set number of singular vectors used in
            # the approximation

            self.hr_Ur = self.hr_U[:, 0:self.max_nsvs]
            self.lr_Ur = self.lr_U[:, 0:self.max_nsvs]

        else:

            # The Sigma Matrix (Singular value matrix) is the economy Matrix
            # with dimensions n x n and not the full singular value matrix of
            # size m x n which contains zeros after the last singular value.
            # Therefore when the number of singular values is not specified, we
            # need to truncate U.

            self.hr_Ur = self.hr_U[:, 0:self.lr_S.shape[0]]
            self.lr_Ur = self.lr_U[:, 0:self.lr_S.shape[0]]

        # Project on truncated eigenvectors
        # ---------------------------------

        lr_nsamples_x_ntimes_num = lr_ntimes_x_nsamples_num.T

        hr_nsamples_x_ntimes_pred_nan = \
            self.hr_Ur @ (self.lr_Ur.T @ lr_nsamples_x_ntimes_num)

        hr_ntimes_x_nsamples_pred_nan = hr_nsamples_x_ntimes_pred_nan.T

        return hr_ntimes_x_nsamples_pred_nan

    def eigenvectors(self):

        """
        Get eigenvectors of the singular value decomposition (SVD)

        Returns:
            Tuple[:class:`xarray.Dataset`]. The eigenvectors. One in low
                resolution, one in high resolution.
        """

        import numpy as np

        #
        # -----------------

        if self.max_nsvs is not None and self.max_nsvs <= self.lr_S.shape[0]:
            nsvs = self.max_nsvs
        else:
            nsvs = self.lr_S.shape[0]

        #
        # ----------------

        lr_ntimes_x_nsamples_nan = self.low_res
        hr_ntimes_x_nsamples_nan = self.high_res

        lr_nsamples_x_ntimes_nan = lr_ntimes_x_nsamples_nan.T
        hr_nsamples_x_ntimes_nan = hr_ntimes_x_nsamples_nan.T

        #
        # ----------------

        lr_U = lr_nsamples_x_ntimes_nan @ self.lr_Vh.T @ self.lr_S_inverse
        hr_U = hr_nsamples_x_ntimes_nan @ self.lr_Vh.T @ self.lr_S_inverse

        lr_Ur = lr_U[:, 0:nsvs]
        hr_Ur = hr_U[:, 0:nsvs]

        lr_nsvs_x_nsamples_nan = lr_Ur.T.reshape(-1)
        hr_nsvs_x_nsamples_nan = hr_Ur.T.reshape(-1)

        # Reshape to nsvs x nsamples
        # --------------------------

        lr_eigen = np.reshape(
            lr_nsvs_x_nsamples_nan,
            (nsvs, -1)
        )

        hr_eigen = np.reshape(
            hr_nsvs_x_nsamples_nan,
            (nsvs, -1)
        )

        return lr_eigen, hr_eigen


class PCA:

    """
    Principal components analysis (PCA)
    This class is deprecated but kept for now
    """

    def __str__(self):

        import textwrap

        return textwrap.dedent(
            f"""
            Principal component analysis (PCA)

            Number of principal components: {self.npcs}
            """
        )

    def __init__(self, da, npcs):

        """
        Class initialization

        Args:
           da (DataArray): DataArray of size (ntimes x ny x nx)
           npcs (int): number of principal components
        """

        from sklearn import decomposition

        self.da = da
        self.npcs = npcs
        self.pca = decomposition.PCA(n_components=self.npcs)
        # self.pca = decomposition.FastICA(n_components=self.npcs)

    def fit(self):

        """
        Fit with principal component analysis (PCA)
        """

        import numpy as np

        # Get numpy array from DataArray
        # ------------------------------

        np_dat = self.da.values

        # Get size of dimensions
        # ----------------------

        ntimes = len(self.da.coords['time'])
        # ny = len(self.da.coords['y'])
        # nx = len(self.da.coords['x'])

        # Reshape to ntimes x ny*nx
        # -------------------------

        nfeatures_x_nsamples_nan = np_dat.reshape((ntimes, -1))

        # Get new nfeatures_x_nsample without NaNs
        # ----------------------------------------

        nfeatures_x_nsamples_num = nfeatures_x_nsamples_nan[
            :, ~np.isnan(nfeatures_x_nsamples_nan).any(axis=0)
        ]

        # Take the transpose. Time is the feature and spatial is the sample
        # -----------------------------------------------------------------

        nsamples_x_nfeatures_num = nfeatures_x_nsamples_num.T

        # Fit
        # ---

        self.pca.fit(nsamples_x_nfeatures_num)

    def transform(self, da):

        """
        .. note

           da_hr is only there to get lons lats for writing DataArray

        Returns:
            :class:`xarray.Dataset`: Transformed data with size
                                     (npcs x ny x nx)
        """

        import numpy as np
        import xarray as xr

        # Get numpy array from DataArray
        # ------------------------------

        np_dat = da.values

        # Get size of dimensions
        # ----------------------

        ntimes = len(da.coords['time'])
        ny = len(da.coords['y'])
        nx = len(da.coords['x'])

        # Reshape to ntimes x ny*nx
        # -------------------------

        nfeatures_x_nsamples_nan = np_dat.reshape((ntimes, -1))

        # Get new nfeatures_x_nsample without NaNs
        # ----------------------------------------

        nfeatures_x_nsamples_num = \
            nfeatures_x_nsamples_nan[
                :, ~np.isnan(nfeatures_x_nsamples_nan).any(axis=0)
            ]

        # Take the transpose. Time is the feature and spatial is the sample
        # -----------------------------------------------------------------

        nsamples_x_nfeatures_num = nfeatures_x_nsamples_num.T

        # Apply PCA transform (npcs x nsamples)
        # -------------------------------------

        # The function returns nsamples x npcs and the transpose must be taken

        npcs_x_nsamples_num = self.pca.transform(nsamples_x_nfeatures_num).T

        # Get the mask from the first timestep
        # ------------------------------------

        # Get the mask from the first timestep of size ny x nx
        # Copy the mask npcs times to obtain shape npcs x ny x nx
        # Flatten everything
        # Get the indices
        # Copy numerical values

        np_mask = np.where(np.isnan(np_dat[0]), 1, 0)

        np_mask = np.repeat(np_mask[np.newaxis, ...], self.npcs, axis=0)\
                    .reshape(-1)

        num_indices = np.argwhere(np.not_equal(np_mask, 1)).reshape(-1)

        npcs_x_nsamples_nan = np.full(
            (self.npcs*ny*nx), np.nan, dtype=np.float32
        )

        npcs_x_nsamples_nan[num_indices] = npcs_x_nsamples_num.reshape(-1)

        # Resphape to npcs x ny x nx
        # --------------------------

        out_dat = np.reshape(npcs_x_nsamples_nan, (self.npcs, ny, nx))

        # Prepare DataArray
        # -----------------

        varname = 'principal_component'

        out_dims = [
            'pc',
            'y',
            'x'
        ]

        pcs = list(range(0, self.npcs))
        y = da.coords['y'].values
        x = da.coords['x'].values
        lats = da.coords['lat'].values
        lons = da.coords['lon'].values

        out_coords = {}
        out_coords['pc'] = (["pc"], pcs)
        out_coords['y'] = (["y"], y)
        out_coords['x'] = (["x"], x)
        out_coords['lat'] = (["y", "x"], lats)
        out_coords['lon'] = (["y", "x"], lons)

        out_da = xr.DataArray(
            name=varname,
            data=out_dat,
            dims=out_dims,
            coords=out_coords,
            attrs={}
        )

        # Set (copy) dimensions attributes
        # --------------------------------

        out_da.coords['lat'].attrs = da.coords['lat'].attrs
        out_da.coords['lon'].attrs = da.coords['lon'].attrs
        out_da.coords['y'].attrs = da.coords['y'].attrs
        out_da.coords['x'].attrs = da.coords['x'].attrs

        return out_da
