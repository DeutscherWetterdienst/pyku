#!/usr/bin/env python3

"""
Univariate and Multivariate Probability Distribution Transfer and Quantile
Mapping methods.

Low level classes for numpy arrays with dimensions (nfeatures x nsamples):

- MBCn
- NDPDF
- UQM
- QDM

High level classes for use with :class:`xarray.Dataset`. These classes are
directly compatible with NetCDF data loaded with xarray. Climate data typically
have dimensions (nfeatures x ntimes x nlats x nlons):

- MBCnCorrector
- NDPDFCorrector
- UQMCorrector
- QDMCorrector

"""

from . import logger

# Set precision
# -------------

# The rationale is to use either float64 or float32 throughout the calculations
# which should balance memory usage and precision. The operation of casting a
# type into another type is not resource intensive.

import numpy as np

float_type = np.float32


class UQM:

    """
    Univariate Quantile Mapping (UQM) for numpy arrays of size (nvariables x
    nsamples)
    """

    def __init__(self, *, nbins=None):

        """
        Initialisation

        Arguments:

            nbins (int):
                Number of bins. Data is split in percentile bins. The higher
                the number of bins the more precise the slower.
        """

        self.nbins = nbins
        self.cal_dist = []
        self.obs_dist = []

        # Sanity checks
        # -------------

        assert nbins is not None, "Parameter 'nbins' is mandatory"

    def fit(self, *, np_cal=None, np_obs=None):

        """
        Fit

        Arguments:

            np_cal (:class:`numpy.ndarray`): (nfeatures x nsamples) biased
                reference dataset.

            np_obs (:class:`numpy.ndarray`): (nfeatures x nsamples) reference
                observation dataset.
        """

        import numpy as np
        import scipy.stats

        # Sanity checks
        # -------------

        assert np_cal is not None, "Parameter 'np_cal' is mandatory"
        assert np_obs is not None, "Parameter 'np_obs' is mandatory"

        assert np.isfinite(np_cal).all(), \
            "np_cal (calibration) contains nans or inf"

        assert np.isfinite(np_obs).all(), \
            "np_obs (observation/reference) contains nans"

        # Cast types
        # ----------

        np_cal = np_cal.astype(float_type)
        np_obs = np_obs.astype(float_type)

        # Loop over features
        # ------------------

        nfeatures = np_cal.shape[0]

        # Array of equal percentils for histogram bins
        # --------------------------------------------

        # The domain from 0 to 100th percentile is divided into ``nbins`` equal
        # bins. For each percentile, the same amount of points is available in
        # each bins.

        hist_percentiles = np.linspace(0, 100, self.nbins)

        # Loop over features
        # ------------------

        for feature_idx in range(nfeatures):

            # Get numpy array for feature
            # ---------------------------

            obs = np_obs[feature_idx]
            cal = np_cal[feature_idx]

            # Sanity check
            # ------------

            assert len(obs) != 0, 'Empty obs data'
            assert len(cal) != 0, 'Empty cal data'

            # Construct histograms and corresponding distributions
            # ----------------------------------------------------

            # For precipitation which has an exponential decrease it occurs
            # that the first percentiles can have the same bounds since most of
            # the time no rain occurs. For example, when using 10 bins, the
            # following situation can occur:
            #
            # hist_cal_bins=array([
            #     0.00000000e+00, 0.00000000e+00,
            #     0.00000000e+00, 0.00000000e+00,
            #     0.00000000e+00, 1.67236725e-02,
            #     3.23435555e-01, 1.63911492e+00,
            #     5.59242672e+00, 1.95331665e+02
            # ])

            # The solution is to use np.unique in order to obtain the sorted
            # array of unique values

            hist_cal_bins = np.unique(np.percentile(cal, hist_percentiles))
            hist_obs_bins = np.unique(np.percentile(obs, hist_percentiles))

            cal_hist = np.histogram(cal, bins=hist_cal_bins, density=True)
            obs_hist = np.histogram(obs, bins=hist_obs_bins, density=True)

            # append distributions to list of distributions
            # ---------------------------------------------

            self.cal_dist.append(
                scipy.stats.rv_histogram(cal_hist, density=True)
            )

            self.obs_dist.append(
                scipy.stats.rv_histogram(obs_hist, density=True)
            )

    def predict(self, *, np_mod=None):

        """
        Predict

        Arguments:

            np_mod (:class:`numpy.ndarray`): The biased data as a numpy array
                of size (nfeatures x nsamples)

        Returns:
            :class:`numpy.ndarray`: (nfeatures x nsamples) corrected data
        """

        import numpy as np

        # Sanity checks
        # -------------

        assert np_mod is not None, "np_mod should not be None"
        assert np.isfinite(np_mod).all(), "Input contains nans or inf"

        # Cast types
        # ----------

        np_mod = np_mod.astype(float_type)

        # Get the number of features
        # --------------------------

        nfeatures = np_mod.shape[0]

        # Initalize the output O to the input X
        # -------------------------------------

        np_out = np_mod

        # Loop over features and perform correction
        # -----------------------------------------

        for feat_idx in range(nfeatures):

            np_out[feat_idx] = self.obs_dist[feat_idx].ppf(
                self.cal_dist[feat_idx].cdf(
                    np_mod[feat_idx]
                )
            )

        return np_out


class NDPDF:

    """
    N-Dimensional Probability Distribution Transfer (NDPDF) for numpy arrays of
    size (nvariables x nsamples)

    F. Pitie and A.C. Kokaram and R. Dahyot, N-dimensional probability density
    function transfer and its application to color transfer, Tenth {IEEE}
    International Conference on Computer Vision (ICCV05) Volume 1,
    10.1109/iccv.2005.166, 2005
    """

    def __str__(self):

        import textwrap

        return textwrap.dedent(
            f"""
            N-Dimensional Probability Distribution Transfer (NDPDF)
            Number of nbins: {self.nbins}
            Number of iterations: {self.niterations}
            """
        )

    def __init__(self, *, niterations=None, nbins=None):

        """
        Initialisation
        """

        self.niterations = niterations
        self.nbins = nbins

        # Save transformations in list
        # ----------------------------

        self.transforms = []

    def fit(self, *, np_cal=None, np_obs=None):

        """
        Fit

        Arguments:
            np_cal (:class:`numpy.ndarray`): The biased model calibration data
                with shape (nfeatures x nsamples)
            np_obs (:class:`numpy.ndarray`): The observation calibration data
                with shape (nfeatures x nsamples)
        """

        import numpy as np
        import scipy.stats as sc

        # Sanity checks
        # -------------

        assert np_cal is not None, "np_cal should not be None"
        assert np_obs is not None, "np_obs should not be None"

        assert np.isfinite(np_cal).all(), \
            "np_cal (model calibration) contains infinite values"

        assert np.isfinite(np_obs).all(), \
            "np_obs (reference/calibration) contains infinite values"

        # Cast types
        # ----------

        np_cal = np_cal.astype(float_type)
        np_obs = np_obs.astype(float_type)

        # Get the number of features
        # --------------------------

        n_features = np_cal.shape[0]

        # Generate orthogonal rotation matrices SO(n_features)
        # ----------------------------------------------------

        self.rotate = sc.special_ortho_group.rvs(n_features, self.niterations)

        # Prepare the inverse transformation
        # ----------------------------------

        self.unrotate = [
            np.linalg.inv(self.rotate[i])
            for i in range(self.niterations)
        ]

        # Initialize modified rotated MRX to X
        # ------------------------------------

        # X = np_cal
        Y = np_obs

        MRX = np_cal

        for i in range(self.niterations):

            # Rotate matrices
            # ---------------

            RY = self.rotate[i] @ Y
            MRX = self.rotate[i] @ MRX

            # Calculate transformation and apply
            # ----------------------------------

            transform = UQM(nbins=self.nbins)

            transform.fit(
                np_cal=MRX,
                np_obs=RY
            )

            MRX = transform.predict(
                np_mod=MRX
            )

            # Save transform in list of transforms
            # ------------------------------------

            self.transforms.append(transform)

            # Unrotate
            # --------

            MRX = self.unrotate[i] @ MRX

    def predict(self, *, np_mod=None):

        """
        Predict
        """

        import numpy as np

        # Sanity checks
        # -------------

        assert np_mod is not None, "np_mod shall not be None"

        assert np.isfinite(np_mod).all(), \
            "np_mod (model) contains infinite values"

        # Cast types
        # ----------

        np_mod = np_mod.astype(float_type)

        # Initialise
        # ----------

        RZ = np_mod

        # Loop over rotations and associated transforms
        # ---------------------------------------------

        for iter_idx in range(self.niterations):

            print(
                f"Predict iteration {iter_idx}",
                end="\r",
                flush=True
            )

            RZ = self.rotate[iter_idx] @ RZ
            RZ = self.transforms[iter_idx].predict(np_mod=RZ)
            RZ = self.unrotate[iter_idx] @ RZ

        return RZ


class QDM:

    """
    Quantile Delta Mapping (QDM) for numpy arrays of size (nfeatures x
    nsamples)
    """

    def __init__(self, *, nbins=None, kind=None):

        """
        Initialisation

        Arguments:
            nbins (int): Number of bins. Data is split in percentile bins. The
                higher the number of bins the better.
            kind (str): Either 'additive' (default) or 'multiplicative'.
        """

        self.kind = kind
        self.nbins = nbins
        self.mod_dist = []
        self.cal_dist = []
        self.obs_dist = []

        # Santiy checks
        # -------------

        assert nbins is not None, "Parameter 'nbins' is mandatory"
        assert kind is not None, "Parameter 'kind' is mandatory"

    def fit_predict(self, *, np_obs=None, np_cal=None, np_mod=None):

        """
        Fit

        Arguments:
            np_obs (:class:`numpy.ndarray`): The reference dataset for
                calibration with shape (nfeatures x nsamples).
            np_cal (:class:`numpy.ndarray`): The biased dataset for calibration
                with shape (nfeatures x nsamples)
            np_mod (:class:`numpy.ndarray`): The biased dataset to be corrected
                with shape (nfeatures x nsamples)

        Returns:
            :class:`numpy.ndarray`: (nfeatures x nsamples) corrected dataset
        """

        import scipy.stats
        import numpy as np

        # Sanity checks
        # -------------

        assert np_obs is not None, "Numpy array np_obs must be passed"
        assert np_cal is not None, "Numpy array np_cal must be passed"
        assert np_mod is not None, "Numpy array np_mod must be passed"

        assert np.isfinite(np_cal).all(), \
            "np_cal (calibration) contains infinite values"

        assert np.isfinite(np_obs).all(), \
            "np_obs (observation/reference) contains infinite values"

        assert np.isfinite(np_mod).all(), \
            "np_mod (biased data) contains infinite values"

        # Cast types
        # ----------

        np_obs = np_obs.astype(float_type)
        np_cal = np_cal.astype(float_type)
        np_mod = np_mod.astype(float_type)

        # Get the number of features
        # --------------------------

        nfeatures = np_mod.shape[0]

        # Array of percentile bins
        # ------------------------

        # The domain from 0 to 100th percentile is divided into ``nbins`` equal
        # bins. For each percentile, the same amount of points is available in
        # each bins.

        hist_percentiles = np.linspace(0, 100, self.nbins)

        # Loop over features
        # ------------------

        for feature_idx in range(nfeatures):

            # Get numpy array for feature
            # ---------------------------

            mod = np_mod[feature_idx]
            obs = np_obs[feature_idx]
            cal = np_cal[feature_idx]

            # Sanity check
            # ------------

            assert len(mod) != 0, 'Empty mod data'
            assert len(obs) != 0, 'Empty obs data'
            assert len(cal) != 0, 'Empty cal data'

            # Construct histograms and corresponding distributions
            # ----------------------------------------------------

            # For precipitation which has an exponential decrease it occurs
            # that the first percentiles can have the same bounds since most of
            # the time no rain occurs. For example, when using 10 bins, the
            # following situation can occur:
            #
            # hist_cal_bins=array([
            #     0.00000000e+00, 0.00000000e+00,
            #     0.00000000e+00, 0.00000000e+00,
            #     0.00000000e+00, 1.67236725e-02,
            #     3.23435555e-01, 1.63911492e+00,
            #     5.59242672e+00, 1.95331665e+02
            # ])

            # The solution is to use np.unique in order to obtain the sorted
            # array of unique values

            hist_mod_bins = np.unique(np.percentile(mod, hist_percentiles))
            hist_obs_bins = np.unique(np.percentile(obs, hist_percentiles))
            hist_cal_bins = np.unique(np.percentile(cal, hist_percentiles))

            mod_hist = np.histogram(mod, bins=hist_mod_bins, density=True)
            obs_hist = np.histogram(obs, bins=hist_obs_bins, density=True)
            cal_hist = np.histogram(cal, bins=hist_cal_bins, density=True)

            # append distributions to list of distributions
            # ---------------------------------------------

            self.mod_dist.append(
                scipy.stats.rv_histogram(mod_hist, density=True))

            self.obs_dist.append(
                scipy.stats.rv_histogram(obs_hist, density=True))

            self.cal_dist.append(
                scipy.stats.rv_histogram(cal_hist, density=True))

        # Perform prediction
        # ------------------

        if self.kind == 'multiplicative':

            if np_cal is not None:
                np_cor, np_car = self.predict_multiplicative(
                    np_mod=np_mod, np_cal=np_cal
                )

                return np_cor, np_car

            else:
                np_cor = self.predict_multiplicative(
                    np_mod=np_mod, np_cal=np_cal
                )
                return np_cor

        elif self.kind == 'additive':
            return self.predict_additive(np_mod=np_mod, np_cal=np_cal)

        else:
            message = (
                "kind {self.kind} not valid, shall be either 'additive', or "
                "multiplicative"
            )
            raise Exception(message)

    def predict_additive(self, *, np_mod=None, np_cal=None):

        """
        Arguments:
            np_mod (:class:`numpy.ndarray`): The biased model data with shape
                (nfeatures x nsamples).
            np_cal (:class:`numpy.ndarray`): The calibration model data with
                shape (nfeatures x nsamples).

        Returns:
            :class:`numpy.ndarray`: corrected model data with shape
            (nfeatures x nsamples)
        """

        # Sanity checks
        # -------------

        assert np_mod is not None, "np_mod should not be None"
        assert np_cal is not None, "np_cal should not be None"

        # Cast data type
        # --------------

        np_mod = np_mod.astype(float_type)
        np_cal = np_cal.astype(float_type)

        # Get the number of features
        # --------------------------

        nfeatures = np_mod.shape[0]

        # Corrected data
        # --------------

        np_cor = np.array([

            np_mod[feat_idx]

            + self.obs_dist[feat_idx].ppf(
                self.mod_dist[feat_idx].cdf(np_mod[feat_idx])
              )

            - self.cal_dist[feat_idx].ppf(
                self.mod_dist[feat_idx].cdf(np_mod[feat_idx])
              )

            for feat_idx in range(nfeatures)
        ], dtype=float_type)

        if np_cal is not None:

            np_car = np.array([

                np_cal[feat_idx]

                + self.obs_dist[feat_idx].ppf(
                    self.cal_dist[feat_idx].cdf(np_cal[feat_idx])
                  )

                - self.cal_dist[feat_idx].ppf(
                    self.cal_dist[feat_idx].cdf(np_cal[feat_idx])
                  )

                for feat_idx in range(nfeatures)
            ], dtype=float_type)

        if np_cal is not None:
            return np_cor, np_car
        else:
            return np_cor

    def predict_multiplicative(self, *, np_mod=None, np_cal=None):

        """
        Arguments:
            np_mod (:class:`numpy.ndarray`): The biased model data with shape
                (nfeatures x nsamples)
            np_cal (:class:`numpy.ndarray`): The calibration data with shape
                (nfeatures x nsamples)

        Returns:
            :class:`numpy.ndarray`: The corrected array with shape
            (nfeatures x nsamples)
        """

        import warnings

        # Sanity checks
        # -------------

        assert np_mod is not None, "np_mod should not be None"
        assert np_cal is not None, "np_cal should not be None"

        # Cast types
        # ----------

        np_mod = np_mod.astype(float_type)
        np_cal = np_cal.astype(float_type)

        # Get the number of features
        # --------------------------

        nfeatures = np_mod.shape[0]

        # Corrected data
        # --------------

        with warnings.catch_warnings():

            # The division in the QDM multiplicative formula will contain zero
            # values. One could here replace the zero values with 1, which
            # would be the proper solution without divisions by zero, but the
            # code is then harder to read. Hence the tradeoff is to suppress
            # the warnings when dividing by zero and reset the NaNs to zero
            # afterwards.

            warnings.filterwarnings(
                "ignore",
                category=RuntimeWarning,
                message="invalid value encountered in divide"
            )

            np_cor = np.array([

                np_mod[feat_idx]

                * self.obs_dist[feat_idx].ppf(
                    self.mod_dist[feat_idx].cdf(np_mod[feat_idx])
                  )

                / self.cal_dist[feat_idx].ppf(
                    self.mod_dist[feat_idx].cdf(np_mod[feat_idx])
                  )

                for feat_idx in range(nfeatures)
            ], dtype=float_type)

            if np_cal is not None:

                np_car = np.array([

                    np_cal[feat_idx]

                    * self.obs_dist[feat_idx].ppf(
                        self.cal_dist[feat_idx].cdf(np_cal[feat_idx])
                      )

                    / self.cal_dist[feat_idx].ppf(
                        self.cal_dist[feat_idx].cdf(np_cal[feat_idx])
                      )

                    for feat_idx in range(nfeatures)
                ], dtype=float_type)

        # Reset NaN values
        # ----------------

        if np_cal is not None:
            np_cor = np.nan_to_num(np_cor, nan=0.0)
            np_car = np.nan_to_num(np_car, nan=0.0)

        else:
            np_cor = np.nan_to_num(np_cor, nan=0.0)

        # Return
        # ------

        if np_cal is not None:
            return np_cor, np_car

        else:
            return np_cor


class MBCn:

    """
    MBCn Bias correction for numpy arrays of size (nfeatures x nsamples)

    The method uses an alternance of random rotation and quantile mapping to
    perform the multivariate bias correction.

    Cannon, Alex J.: Multivariate quantile mapping bias correction: an
    N-dimensional probability density function transform for climate model
    simulations of multiple variables, Climate Dynamics, nb. 1, vol. 50, p.
    31-49, 10.1007/s00382-017-3580-6
    """

    def __init__(self, *, nbins=None, niterations=None, kind=None):

        """
        Initialisation of MBCn.

        Arguments:
            nbins (int): The number of bins for the histograms.
            niterations (int): The number of iterations.
            kind (str): Either 'additive' or 'multiplicative'.

        """

        self.use_sbck = False
        self.nbins = nbins
        self.niterations = niterations
        self.kind = kind

        # Sanity checks
        # -------------

        assert nbins is not None, "Parameter 'nbins' is mandatory"
        assert niterations is not None, "Parameter 'niterations' is mandatory"
        assert kind is not None, "Parameter 'kind' is mandatory"

    def fit_predict(self, *, np_cal=None, np_obs=None, np_mod=None):

        """
        Fit predict

        Arguments:
            np_cal (:class:`numpy.ndarray`): The biased dataset for calibration
                with shape (nfeatures x nsamples)
            np_obs (:class:`numpy.ndarray`): The reference dataset for
                calibration with shape (nfeatures x nsamples)
            np_mod (:class:`numpy.ndarray`):The biased model dataset with shape
                (nfeatures x nsamples)
        """

        import numpy as np
        import scipy.stats as sc

        # Sanity checks
        # -------------

        assert np_cal is not None, "Parameter 'np_cal' is mandatory"
        assert np_obs is not None, "Parameter 'np_obs' is mandatory"
        assert np_mod is not None, "Parameter 'np_mod' is mandatory"

        assert np.isfinite(np_mod).all(), \
            "np_mod (model) contains infinite values"

        assert np.isfinite(np_cal).all(), \
            "np_cal (model calibration) contains infinite values"

        assert np.isfinite(np_obs).all(), \
            "np_obs (reference/calibration) contains infinite values"

        # Cast types
        # ----------

        np_cal = np_cal.astype(float_type)
        np_obs = np_obs.astype(float_type)
        np_mod = np_mod.astype(float_type)

        # Get the number of features
        # --------------------------

        n_features = np_mod.shape[0]

        # Generate orthogonal rotation matrices SO(n_features)
        # ----------------------------------------------------

        self.rotate = sc.special_ortho_group.rvs(n_features, self.niterations)

        # Prepare the inverse transformation
        # ----------------------------------

        self.unrotate = [
            np.linalg.inv(self.rotate[i]) for i in range(self.niterations)
        ]

        # Initialize rotated matrices
        # ---------------------------

        RMOD = np_mod
        ROBS = np_obs
        RCAL = np_cal

        for i in range(self.niterations):

            # Rotate matrices
            # ---------------

            RMOD = self.rotate[i] @ RMOD
            ROBS = self.rotate[i] @ ROBS
            RCAL = self.rotate[i] @ RCAL

            # Calculate transformation and apply
            # ----------------------------------

            # SBCK Implementation
            # -------------------

            if self.use_sbck:

                try:
                    from SBCK import QDM as SBCK_QDM
                except Exception as e:
                    message = (
                        f"{e} "
                        "The SBCK module coult not be loaded. Check the "
                        "documentation for instructions on how to install."
                    )
                    raise Exception(message)

                transform = SBCK_QDM()
                transform.fit(ROBS.T, RCAL.T, RMOD.T)
                RMOD, RCAL = transform.predict(RMOD.T, RCAL.T)
                RMOD = RMOD.T
                RCAL = RCAL.T

            else:

                transform = QDM(nbins=self.nbins, kind=self.kind)

                RMOD, RCAL = transform.fit_predict(
                    np_mod=RMOD,
                    np_obs=ROBS,
                    np_cal=RCAL
                )

                del transform

            # Unrotate
            # --------

            RMOD = self.unrotate[i] @ RMOD
            ROBS = self.unrotate[i] @ ROBS
            RCAL = self.unrotate[i] @ RCAL

        return RMOD, RCAL


class PDFCorrector:

    """
    Parent corrector class for all PDF correctors.

    The purpose of this class is to gather high-level and optimized functions.
    """

    def rolling_decadal_block_fit_predict(
            self, groupby_type='time.month', block_size=None, client=None):

        """
        High level function for performing bias correction with QDM and MBCn
        methods.

        Use a 30 year rolling window, perform bias correction for the middle
        decade, and subsequently remove the first and last ten years of the
        rolling window when returning the corrected data. Then move the rolling
        window by 10 years. The correction is performed by groupby_type, which
        should generally be a monthly grouping.

        Arguments:

            groupby_type (str): How to group the data. Defaults to
                'time.month'. The parameter is expected to be of that type and
                could be changed to 'time.season'.

            client (:class:`dask.distributed.client`): Defaults to None. The
                dask client. When given, the function uses the client for
                multiprocessing. For large datasets, this parameter is most
                needed to speed up computations

            block_size (tuple[int]): Deprecated option. Block size, defaults to
                (5, 5). The data should have a form like (ntimes x ny x nx).
                Calculations are performed for each pixel. For multiprocessing,
                the block size is a chunk of data along (ny x nx) which can be
                sent to workers.

        Returns:
            class:`xarray.Dataset`: The corrected dataset.
        """

        import itertools
        import xarray as xr
        import numpy as np

        if self.bc_method_id.lower() not in ['qdm', 'mbcn']:

            message = (
                "The function only makes sense for qdm and mbcn, but not for "
                f"{self.bc_method_id}."
            )

            raise Exception(message)

        # Split years available in data into decades
        # ------------------------------------------

        years, _ = zip(*self.ds_mod.groupby('time.year'))

        decades = np.array(
            [np.array(list(g))
             for k, g in itertools.groupby(years, lambda i: (i - 1) // 10)],
            dtype=object
        )

        logger.info(f"Split: \n{decades}")

        corrected_decades = []

        # Loop over each decade in projection dataset
        # -------------------------------------------

        for decade_idx, decade in enumerate(decades):

            # Select rolling window of +/10 years around the current decade
            # -------------------------------------------------------------

            window_lower = min(decade)-10
            window_higher = max(decade)+10

            selected_ds_mod = self.ds_mod.sel(
                time=slice(f"{window_lower}", f"{window_higher}")
            )

            mod_lower = selected_ds_mod.time.dt.year.min().item()
            mod_higher = selected_ds_mod.time.dt.year.max().item()

            obs_lower = self.ds_obs.time.dt.year.min().item()
            obs_higher = self.ds_obs.time.dt.year.max().item()

            logger.info(
                f"\nCorrecting {decade}:\n"
                f"- 30 year window: {window_lower} - {window_higher} \n"
                f"- Train model: {mod_lower} - {mod_higher} \n"
                f"- Train observation: {obs_lower} - {obs_higher}"
            )

            sel_cor = self.block_fit_predict(
                groupby_type='time.month',
                block_size=block_size,
                ds_mod=selected_ds_mod,
            )

            # Select the decade from the rolling window
            # ------------------------------------------

            logger.debug(
                "Select middle decade from rolling window from "
                f"{min(decade)} until {max(decade)}"
            )

            sel_cor = sel_cor.sel(
                time=slice(f"{min(decade)}", f"{max(decade)}"))

            sel_cor = sel_cor.compute()

            logger.info("Append to results")
            corrected_decades.append(sel_cor)

        # Merge decadal data
        # ------------------

        # output = xr.merge(corrected_decades)
        output = xr.concat(corrected_decades, dim="time")

        return output

    def block_fit_predict(
            self, ds_mod=None, groupby_type='time.month', block_size=None):

        """
        Group by groupby type and fit-predict each pixel. This function is
        optimized for multiprocessing with dask.

        Arguments:

            ds_mod (:class:`xarray.Dataset`): The model data to be corrected.
                This parameter is mandatory for 'uqm', 'ndpdf' and 'lmk'
                methods. For 'qdm' and 'mbcn', this argument is ignored by
                default since the model data are already initialized with the
                corrector. However, if 'ds_mod' is passed together with 'qdm'
                or 'mbcn', this parameter permits to overwrite the default
                model data. This is usefull when performing e.g. a correction
                with a rolling window of 30 years, as it permits to select a
                subset of the projection data to be considered for the
                correction. To make sure the code works as intended as
                intended, it is recommended to pass this parameter even if it
                is already initialized with the corrector.

            groupby_type (string): Data grouping. The correction is applied
                independently to each group. The value of 'groupby_type' is
                expected to be 'time.month', but could also be set to
                'time.season'.
        """

        import xarray as xr
        import numpy as np
        import gc
        import pyku.meta as meta

        # Sanity checks
        # -------------

        message = (
            "xarray map_blocks is not compatible with cftime calendar. "
            "You can use the pyku function timekit.to_gregorian_calendar "
            "and then revert to the original calendar."
        )

        if ds_mod.time.dt.calendar not in ['proleptic_gregorian']:
            raise Exception(message)

        if self.ds_cal.time.dt.calendar not in ['proleptic_gregorian']:
            raise Exception(message)

        if self.ds_obs.time.dt.calendar not in ['proleptic_gregorian']:
            raise Exception(message)

        # Determine the block size
        # ------------------------

        if block_size is not None:

            logger.warn(
                "block_size is deprecated, use parameter chunks while "
                "opening with open_mfdataset"
            )

        # Get reference/observation, model calibration, and model projection
        # ------------------------------------------------------------------

        if self.bc_method_id.lower() in ['uqm', 'ndpdf', 'lmk']:

            assert ds_mod is not None, \
                "Parameter 'ds_mod' is mandatory for 'uqm', 'ndpdf', 'lmk'"

            ds_obs = self.ds_obs
            ds_cal = self.ds_cal
            ds_mod = ds_mod

        elif self.bc_method_id.lower() in ['qdm', 'mbcn']:

            ds_obs = self.ds_obs
            ds_cal = self.ds_cal

            # Set the projection data used for the correction
            # -----------------------------------------------

            # if 'ds_mod' is passed together with 'qdm' or 'mbcn', this
            # parameter permits to overwrite the default model data. This is
            # usefull when performing e.g. a correction with a rolling window
            # of 30 years, as it permits to select a subset of the projection
            # data to be considered for the correction. To make sure the code
            # works as intended as intended, it is recommended to pass this
            # parameter even if it is already initialized with the corrector.

            if ds_mod is not None:
                ds_mod = ds_mod

            else:
                ds_mod = self.ds_mod

        else:
            message = f"Corrector type {self.bc_method_id} not implemented"
            raise Exception(message)

        # Sanity check, is the dataset chunked
        # ------------------------------------

        y_varname, x_varname = meta.get_projection_yx_varnames(ds_mod)

        if not ds_mod.chunks:
            raise Exception("ds_mod not chunked along projection coordinates")
        if not ds_obs.chunks:
            raise Exception("ds_obs not chunked along projection coordinates")
        if not ds_cal.chunks:
            raise Exception("ds_cal not chunked along projection coordinates")

        def fit_predict_each_pixel(
                block_obs=None, block_cal=None, block_mod=None):

            """
            Loop through each pixel and fit-predict independently. This
            function is internal and not accessible directly by users.

            Arguments:
                block_obs (:class:`xarray.Dataset`): Block of observation
                    reference data.
                block_cal (:class:`xarray.Dataset`): Block of model historical
                    calibration data.
                block_mod (:class:`xarray.Dataset`): Block of model projection
                    data.
            """

            import pyku.meta as meta

            # Get name of y and x projection coordinates
            # ------------------------------------------

            y_name, x_name = meta.get_projection_yx_varnames(block_mod)

            # Get variable names
            # ------------------

            obs_varnames = meta.get_geodata_varnames(block_obs)
            cal_varnames = meta.get_geodata_varnames(block_cal)
            mod_varnames = meta.get_geodata_varnames(block_mod)

            are_equal = obs_varnames == cal_varnames == mod_varnames

            if not are_equal:
                message = (
                    "Check variables in dataset: "
                    f"{obs_varnames=}, {cal_varnames=}, {mod_varnames=}. "
                    "Notes the geodata variable names should not only be the "
                    "same, but also in the same order!"
                )
                raise Exception(message)

            varnames = obs_varnames

            # Loop over all pixels in block and save correction results in list
            # -----------------------------------------------------------------

            corrections = []

            for i in np.arange(block_mod[x_name].size):
                for j in np.arange(block_mod[y_name].size):

                    # Select a single pixel
                    # ---------------------

                    block_obs_ij = block_obs.isel({x_name: [i], y_name: [j]})
                    block_cal_ij = block_cal.isel({x_name: [i], y_name: [j]})
                    block_mod_ij = block_mod.isel({x_name: [i], y_name: [j]})

                    # Check if any of the features is only Nans
                    # -----------------------------------------

                    obs_all_nans = any([
                        np.all(np.isnan(block_obs_ij[varname].values))
                        for varname in varnames
                    ])

                    cal_all_nans = any([
                        np.all(np.isnan(block_cal_ij[varname].values))
                        for varname in varnames
                    ])

                    mod_all_nans = any([
                        np.all(np.isnan(block_mod_ij[varname].values))
                        for varname in varnames
                    ])

                    # If any of the features is all Nans, return NaNs
                    # -----------------------------------------------

                    if obs_all_nans or cal_all_nans or mod_all_nans:
                        corrections.append(block_mod_ij)

                    elif self.bc_method_id.lower() in ['uqm']:

                        corrector = UQMCorrector(
                            ds_obs=block_obs_ij,
                            ds_cal=block_cal_ij,
                            nbins=self.nbins,
                        )

                        corrections.append(
                            corrector.fit_predict(block_mod_ij)
                        )

                    elif self.bc_method_id.lower() in ['ndpdf']:

                        corrector = NDPDFCorrector(
                            ds_obs=block_obs_ij,
                            ds_cal=block_cal_ij,
                            nbins=self.nbins,
                            niterations=self.niterations
                        )

                        corrections.append(
                            corrector.fit_predict(block_mod_ij)
                        )

                    elif self.bc_method_id.lower() in ['qdm']:

                        corrector = QDMCorrector(
                            ds_mod=block_mod_ij,
                            ds_obs=block_obs_ij,
                            ds_cal=block_cal_ij,
                            implementation=self.implementation,
                            nbins=self.nbins,
                            kind=self.kind
                        )

                        corrections.append(
                            corrector.fit_predict()
                        )

                    elif self.bc_method_id.lower() in ['mbcn']:

                        corrector = MBCnCorrector(
                            ds_mod=block_mod_ij,
                            ds_obs=block_obs_ij,
                            ds_cal=block_cal_ij,
                            implementation=self.implementation,
                            niterations=self.niterations,
                            nbins=self.nbins,
                            kind=self.kind
                        )

                        corrections.append(
                            corrector.fit_predict()
                        )

                    else:
                        message = \
                            f"Corrector {self.bc_method_id} not implemented"
                        raise Exception(message)

            # Explicitely call the garbage collector
            # --------------------------------------

            gc.collect()

            # Merge, reindex output like input and return
            # -------------------------------------------

            correction = xr.merge(corrections,
                                  compat='no_conflicts',
                                  join='outer')

            # Reindexing the corrected data with the uncorrected data is needed
            # because the y and x projection Coordinates are not necessarily
            # returned in the same order.

            correction = correction.reindex({
                y_name: block_mod[y_name],
                x_name: block_mod[x_name],
            })

            return correction

        def block_function(ds_block):

            """
            Fit predict one block of data.

            This function is internal and not accessible by users. It is
            written to be passed to xarray.map_blocks. In that framework, only
            a single dataset can be passed. For that reason,
            reference/observation, model calibration/historical and model
            projection data are merged into a single Dataset.

            Arguments:
                ds (:class:`xarray.Dataset`): Dataset containing data for
                    observation, model calibration, and model projection.

            Returns:
                :class:`xarray.Dataset`: Corrected model projection.
            """

            reconstructed_mod = ds_block.pyku.get_geodataset([
                varname for varname in ds_block.pyku.get_geodata_varnames()
                if '_mod' in varname
            ])

            reconstructed_obs = ds_block.pyku.get_geodataset([
                varname for varname in ds_block.pyku.get_geodata_varnames()
                if '_obs' in varname
            ])

            reconstructed_cal = ds_block.pyku.get_geodataset([
                varname for varname in ds_block.pyku.get_geodata_varnames()
                if '_cal' in varname
            ])

            reconstructed_mod = reconstructed_mod.rename({
                varname: varname.replace('_mod', '') for varname
                in reconstructed_mod.pyku.get_geodata_varnames()
            })

            reconstructed_obs = reconstructed_obs.rename({
                varname: varname.replace('_obs', '') for varname
                in reconstructed_obs.pyku.get_geodata_varnames()
            })

            reconstructed_cal = reconstructed_cal.rename({
                varname: varname.replace('_cal', '') for varname
                in reconstructed_cal.pyku.get_geodata_varnames()
            })

            block_mod = reconstructed_mod.rename({'time_mod': 'time'})
            block_obs = reconstructed_obs.rename({'time_obs': 'time'})
            block_cal = reconstructed_cal.rename({'time_cal': 'time'})

            block_obs = block_obs.compute()
            block_cal = block_cal.compute()
            block_mod = block_mod.compute()

            # Free memory (Maybe not needed)
            # ------------------------------

            # del ds
            # gc.collect()

            # Group by
            # --------

            if groupby_type is not None:

                # Split data into groups
                # ----------------------

                obs_group = block_obs.groupby(groupby_type)
                cal_group = block_cal.groupby(groupby_type)
                mod_group = block_mod.groupby(groupby_type)

                # Initialize list of all corrected months
                # ---------------------------------------

                all_months = []

                # Loop over all months and fit-predict
                # ------------------------------------

                for key in obs_group.groups.keys():

                    all_months.append(
                        fit_predict_each_pixel(
                            block_obs=obs_group[key].compute(),
                            block_cal=cal_group[key].compute(),
                            block_mod=mod_group[key].compute(),
                        )
                    )

            else:

                all_months = []

                all_months.append(
                    fit_predict_each_pixel(
                        block_obs=block_obs,
                        block_cal=block_cal,
                        block_mod=block_mod
                    )
                )

            # Merge and return
            # ----------------

            cor = xr.merge(all_months,
                           compat='no_conflicts',
                           join='outer')
            cor = cor.compute()

            return cor

        # Concatenate all datasets into a single xarray Dataset
        # -----------------------------------------------------

        renamed_mod = ds_mod.rename({
            var: f"{var}_mod" for var in ds_mod.pyku.get_geodata_varnames()
        })

        renamed_obs = ds_obs.rename({
            var: f"{var}_obs" for var in ds_obs.pyku.get_geodata_varnames()
        })

        renamed_cal = ds_cal.rename({
            var: f"{var}_cal" for var in ds_cal.pyku.get_geodata_varnames()
        })

        renamed_mod = renamed_mod.rename({'time': 'time_mod'})
        renamed_obs = renamed_obs.rename({'time': 'time_obs'})
        renamed_cal = renamed_cal.rename({'time': 'time_cal'})

        ds_blocks = xr.merge([renamed_mod, renamed_obs, renamed_cal],
                             compat='no_conflicts')

        # Chunk dataset according to block size
        # -------------------------------------

        ds_blocks = ds_blocks.chunk(chunks={
            'time_mod': -1, 'time_obs': -1, 'time_cal': -1,
        })

        ds_blocks = ds_blocks.unify_chunks()

        # Template
        # --------

        # Define the output template of the map_block function. The template
        # shall have the same dimensions, coordinates and chunks

        ds_mod = ds_mod.chunk(chunks={'time': -1})

        logger.debug(f"Mapping blocks {len(ds_obs.time)=}")
        logger.debug(f"Mapping blocks {len(ds_cal.time)=}")
        logger.debug(f"Mapping blocks {len(ds_mod.time)=}")
        logger.debug(f"Mapping blocks {ds_obs.chunks=}")
        logger.debug(f"Mapping blocks {ds_cal.chunks=}")
        logger.debug(f"Mapping blocks {ds_mod.chunks=}")
        logger.debug(f"Mapping blocks {ds_blocks.pyku.get_dataset_size()}")
        logger.debug(f"Mapping blocks {ds_blocks.dims=}")
        logger.debug(f"Mapping blocks {ds_blocks.chunks=}")

        # Map blocks
        # ----------

        cor = xr.map_blocks(
            block_function,
            ds_blocks,
            template=ds_mod
        )

        # Set attributes
        # --------------

        cor.attrs['bc_method_id'] = self.bc_method_id
        cor.attrs['bc_method'] = self.bc_method
        cor.attrs['bc_period'] = self.bc_period
        cor.attrs['creation_date'] = self.creation_date

        return cor

    def regional_fit_predict(self, ds_mod=None, regions=None, area_def=None):

        """
        Regionalized fit_predict

        Arguments:
            regions (:class:`geopandas.GeoDataFrame`): Region file.
            area_def (:class:`pyresample.AreaDefinition`): Area definition.

        """

        import sys
        import pyku.features as libfeatures
        import pyku.meta as libmetadata
        import xarray as xr
        import numpy as np

        assert regions is not None, "Parameter 'regions' is mandatory"
        assert area_def is not None, "parameter 'area_def' is mandatory"

        # Datasets are splitted in a list of smaller datasets
        # ---------------------------------------------------

        ds_obs_elements = []
        ds_cal_elements = []
        ds_mod_elements = []

        # Load data
        # ---------

        # qdm correctors are initialized together with the data to be corrected

        print("Loading to memory...")

        if self.bc_method_id in ['uqm', 'ndpdf', 'lmk']:

            ds_obs = self.ds_obs
            ds_cal = self.ds_cal
            ds_mod = ds_mod

        elif self.bc_method_id in ['qdm', 'mbcn']:

            ds_obs = self.ds_obs
            ds_cal = self.ds_cal
            ds_mod = self.ds_mod

        else:

            message = f"Corrector type {self.bc_method_id} not implemented"
            raise Exception(message)

        print("Data loaded into memory")

        # Split regions
        # -------------

        print("Rasterize regions")

        # Rasterize polygons to raster
        # ----------------------------

        regions_da = libfeatures.rasterize_polygons(
            regions,
            area_def=area_def
        )

        # Load all data in memory, keeping the dask structure
        # ---------------------------------------------------

        # regions_da = regions_da.persist()

        # Get the indices of the polygons where there is data
        # ---------------------------------------------------

        regions_indices = np.unique(
            regions_da.values[np.isfinite(regions_da.values)].astype(int)
        )

        # Split time groups into regions
        # ------------------------------

        print("Split dataset into regions")

        # Convert datasets to list of datasets
        # ------------------------------------

        # Data along the 'x' and 'y' axis are dropped for memory usage
        # efficiency

        for region_idx in regions_indices:

            print(f"region: {region_idx}   ", end='\r')
            sys.stdout.flush()

            y_name, x_name = libmetadata.get_projection_yx_varnames(regions_da)

            y = regions_da.where(regions_da == region_idx) \
                .dropna(dim=y_name, how='all') \
                .dropna(dim=x_name, how='all') \
                .y
            x = regions_da.where(regions_da == region_idx) \
                .dropna(dim=y_name, how='all') \
                .dropna(dim=x_name, how='all') \
                .x

            ds_obs_element = ds_obs.where(regions_da == region_idx)
            ds_cal_element = ds_cal.where(regions_da == region_idx)
            ds_mod_element = ds_mod.where(regions_da == region_idx)

            ds_obs_element = ds_obs_element.sel({y_name: y, x_name: x})
            ds_cal_element = ds_cal_element.sel({y_name: y, x_name: x})
            ds_mod_element = ds_mod_element.sel({y_name: y, x_name: x})

            ds_obs_elements.append(ds_obs_element)
            ds_cal_elements.append(ds_cal_element)
            ds_mod_elements.append(ds_mod_element)

        print("\nTime groups and regions loaded in list")

        # Construct independent corrector for each element
        # ------------------------------------------------

        ds_cor_elements = []

        print("Building correctors")

        for idx in regions_indices:

            print(f"element: {idx}     ")

            cor_result = self.generic_fit_predict(
                ds_obs=ds_obs_elements[idx],
                ds_cal=ds_cal_elements[idx],
                ds_mod=ds_mod_elements[idx],
            )

            ds_cor_elements.append(cor_result)

        # Merge results
        # -------------

        cor = xr.merge(ds_cor_elements)

        # Merge with mask
        # ---------------

        # The data have been split in regions and nans outside region taken
        # out. Hence even when combining the regional data back together, the
        # number of longitude and latitude points is not necessarily the same
        # as the original data, because there may have been nans along the
        # borders in the first place. Hence the output is merged with the mask
        # which contains all lat lon points.

        # Furthermore, the join on the data inverses the y coordinates, hence
        # the join='right' which select the orientation from the mask.

        cor = xr.merge([cor, regions_da], join='right').drop('regions')

        return cor

    def groupedby_fit_predict(self, ds_mod=None, groupby_type=None):

        """
        grouped by type fit_predict

        Arguments:
            ds_mod (:class:`xarray.Dataset`): The biased model dataset.
            groupby_type (str): The grouping method, expected the expected
                value is 'time.month'.
        """

        import xarray as xr

        # Sanity checks
        # -------------

        assert ds_mod is not None, "Parameter 'ds_mod' is mandatory"
        assert groupby_type is not None, \
            "Parameter 'groupby_type' is mandatory"

        if groupby_type is None:
            raise Exception("groupby_type not set")

        # Get reference/observation, model calibration, and model projection
        # ------------------------------------------------------------------

        if self.bc_method_id in ['uqm', 'ndpdf', 'lmk']:

            ds_obs = self.ds_obs
            ds_cal = self.ds_cal
            ds_mod = ds_mod

        elif self.bc_method_id in ['qdm', 'mbcn']:

            ds_obs = self.ds_obs
            ds_cal = self.ds_cal
            ds_mod = self.ds_mod

        else:

            message = f"Corrector type {self.bc_method_id} not implemented"
            raise Exception(message)

        # Split data into groups
        # ----------------------

        obs_group = ds_obs.groupby(groupby_type)
        cal_group = ds_cal.groupby(groupby_type)
        mod_group = ds_mod.groupby(groupby_type)

        # Initialize the list of all corrected groups
        # -------------------------------------------

        corrected_list = []

        for key in obs_group.groups.keys():

            corrected = self.generic_fit_predict(
                ds_obs=obs_group[key],
                ds_cal=cal_group[key],
                ds_mod=mod_group[key],
            )

            corrected_list.append(corrected)

        return xr.merge(corrected_list)

    def regional_groupedby_fit_predict(
            self, ds_mod, groupby_type=None, regions=None, area_def=None,
            output_varnames=None):

        """
        Regionalized fit_predict

        Arguments:
            groupby_type (str): Type of grouping. The value is expected to be
                'time.month'
            regions (:class:`geopandas.GeoDataFrame`): regions file
            area_def (:class:`pyresample.AreaDefinition`): Projection

        """

        import sys
        import pyku.features as libfeatures
        import pyku.meta as libmetadata
        import xarray as xr
        import numpy as np
        from dask import delayed
        from dask.distributed import Client, default_client

        # Sanity checks
        # -------------

        assert regions is not None, "Parameter 'regions' is mandatory"
        assert area_def is not None, "Parameter 'area_def' is mandatory"
        assert groupby_type is not None, \
            "Parameter 'groupby_type' is mandatory"

        # If Dask client already created in parent code, use it
        # -----------------------------------------------------

        if default_client() is None:
            client = Client()
        else:
            client = default_client()

        # Load data
        # ---------

        print("Loading to memory...")

        if self.bc_method_id in ['uqm', 'ndpdf', 'lmk']:

            ds_obs = self.ds_obs
            ds_cal = self.ds_cal
            ds_mod = ds_mod

        elif self.bc_method_id in ['qdm', 'mbcn']:

            ds_obs = self.ds_obs
            ds_cal = self.ds_cal
            ds_mod = self.ds_mod

        else:

            message = f"Corrector type {self.bc_method_id} not implemented"
            raise Exception(message)

        print("Data loaded into memory")

        # Split regions
        # -------------

        print("Rasterize regions")

        # Rasterize polygons to raster
        # ----------------------------

        regions_da = libfeatures.rasterize_polygons(
            regions,
            area_def=area_def
        )

        # Load all data in memory, keeping the dask structure
        # ---------------------------------------------------

        # regions_da = regions_da.persist()

        # Get the indices of the polygons where there is data
        # ---------------------------------------------------

        regions_indices = np.unique(
            regions_da.values[np.isfinite(regions_da.values)].astype(int)
        )

        # Split time groups into regions
        # ------------------------------

        print("Split dataset")

        # Convert datasets to list of datasets
        # ------------------------------------

        # Data along the 'x' and 'y' axis are dropped for memory usage
        # efficiency

        # Datasets are splitted in a list of smaller datasets
        # ---------------------------------------------------

        ds_obs_elements = []
        ds_cal_elements = []
        ds_mod_elements = []

        for region_idx in regions_indices:

            print(f"region: {region_idx}   ", end='\r')
            sys.stdout.flush()

            y_name, x_name = libmetadata.get_projection_yx_varnames(regions_da)

            y = regions_da.where(regions_da == region_idx) \
                .dropna(dim=y_name, how='all') \
                .dropna(dim=x_name, how='all') \
                .y
            x = regions_da.where(regions_da == region_idx) \
                .dropna(dim=y_name, how='all') \
                .dropna(dim=x_name, how='all') \
                .x

            ds_obs_region = ds_obs.where(regions_da == region_idx)
            ds_cal_region = ds_cal.where(regions_da == region_idx)
            ds_mod_region = ds_mod.where(regions_da == region_idx)

            ds_obs_region = ds_obs_region.sel({y_name: y, x_name: x})
            ds_cal_region = ds_cal_region.sel({y_name: y, x_name: x})
            ds_mod_region = ds_mod_region.sel({y_name: y, x_name: x})

            # Split data into groups
            # ----------------------

            obs_group = ds_obs_region.groupby(groupby_type)
            cal_group = ds_cal_region.groupby(groupby_type)
            mod_group = ds_mod_region.groupby(groupby_type)

            # Obtain the keys from the groupby object
            # ---------------------------------------

            keys = obs_group.groups.keys()

            for key in keys:
                ds_obs_elements.append(obs_group[key])
                ds_cal_elements.append(cal_group[key])
                ds_mod_elements.append(mod_group[key])

        print("\nTime groups and regions loaded in list")

        print("Building correctors")

        # Define the loop logic as a delayed function
        # -------------------------------------------

        @delayed
        def process_element(ds_obs_element, ds_cal_element, ds_mod_element):

            corrected_element = self.generic_fit_predict(
                ds_obs=ds_obs_element,
                ds_cal=ds_cal_element,
                ds_mod=ds_mod_element,
            )

            return corrected_element

        # Scattering the data before hand certainly solves the warning,
        # but seems to result in increased computation time.

        # ds_obs_elements = client.scatter(ds_obs_elements)
        # ds_cal_elements = client.scatter(ds_cal_elements)
        # ds_mod_elements = client.scatter(ds_mod_elements)

        # Obtain the elements indices
        # ---------------------------

        indices = range(len(ds_obs_elements))

        # List of delayed computations
        # ----------------------------

        print('delayed results')

        delayed_results = [
            process_element(
                ds_obs_elements[idx],
                ds_cal_elements[idx],
                ds_mod_elements[idx]
            )
            for idx in indices
        ]

        # Compute the delayed results using Dask
        # --------------------------------------

        print('compute')
        results = client.compute(delayed_results, scheduler='synchronous')
        # results = dask.compute(*delayed_results, scheduler='synchronous')

        # Retrieve the actual results
        # ---------------------------

        print('retrieve...')
        actual_results = client.gather(results)

        # Collect the corrected groups
        # ----------------------------

        print('collect...')
        ds_cor_elements = [result for result in actual_results]

        # Select output variables
        # -----------------------

        print('select output variables')

        # I could not manage to very efficiently merge all data back together
        # due to a spike in RAM. Hence the output variable can be selected to
        # reduce the amount of RAM necessary in the host machine when
        # collecting the results of each regions and time slices.

        if output_varnames is not None:
            for idx, _ in enumerate(ds_cor_elements):
                ds_cor_elements[idx] = ds_cor_elements[idx][output_varnames]

        # Merge regions
        # -------------

        # Concatenate the data of each regions along the time coordinates,
        # since the data have been split in time groups.

        print("merging regions...")

        nelements = len(ds_cor_elements)
        ngroups = len(ds_obs.groupby(groupby_type).groups.keys())
        nregions = len(regions_indices)

        merged_corrected_elements = []

        for element_idx in np.arange(nelements, step=nregions-1):
            region_indices = np.arange(element_idx, element_idx + ngroups)
            merged_corrected_elements.append(
                xr.concat(
                    [ds_cor_elements[i] for i in region_indices],
                    dim='time'
                )
            )
            print(f"merged {list(region_indices)}")

        # combine data
        # ------------

        # When merging data back together, we optimize for memory by using
        # combine_first. In that situation, all regions have been group
        # together and contain the same time stampls, but not the same
        # geographical coordinates

        print("merging groups...")

        for idx, _ in enumerate(merged_corrected_elements):

            if idx == 0:

                # Initialize
                # ----------

                # The data have been split in regions and nans outside region
                # taken out. Hence even when combining the regional data back
                # together, the number of longitude and latitude points is not
                # necessarily the same as the original data, because there may
                # have been nans along the borders in the first place. Hence
                # the output is merged with the mask which contains all lat lon

                # Furthermore, the join on the data inverses the y coordinates,
                # hence the join='left' which select the orientation from the
                # mask. points.

                cor = xr.merge(
                    [regions_da, merged_corrected_elements[idx]],
                    join='left',
                    combine_attrs='drop_conflicts',
                ).drop('regions')

            else:
                cor = cor.combine_first(merged_corrected_elements[idx])

        cor = xr.merge(
            [regions_da, cor],
            join='left',
            combine_attrs='drop_conflicts',
        ).drop('regions')

        print("sort time index")
        cor = cor.sortby('time')

        return cor

    def generic_fit_predict(self, ds_obs=None, ds_cal=None, ds_mod=None):

        """
        Fit and predict

        The purpose of this function is to be able to reset an existing
        corrector with new data and fit_predict.

        Arguments:
            ds_obs (:class:`xarray.Dataset`): Observation training dataset
            ds_cal (:class:`xarray.Dataset`): Model calibration dataset
            ds_mod (:class:`xarray.Dataset`): Bias model dataset
        """

        # Sanity checks
        # -------------

        assert ds_obs is not None, "Parameter 'ds_obs' is mandatory"
        assert ds_cal is not None, "Parameter 'ds_cal' is mandatory"
        # assert ds_mod is not None, "Parameter 'ds_mod' is mandatory"

        if self.bc_method_id in ['uqm']:

            corrector = UQMCorrector(
                ds_obs=ds_obs,
                ds_cal=ds_cal,
                nbins=self.nbins,
            )

        elif self.bc_method_id in ['ndpdf']:

            corrector = NDPDFCorrector(
                ds_obs=ds_obs,
                ds_cal=ds_cal,
                nbins=self.nbins,
                niterations=self.niterations
            )

        elif self.bc_method_id in ['qdm']:

            corrector = QDMCorrector(
                ds_mod=ds_mod,
                ds_obs=ds_obs,
                ds_cal=ds_cal,
                implementation=self.implementation,
                nbins=self.nbins,
                kind=self.kind
            )

        elif self.bc_method_id in ['mbcn']:

            corrector = MBCnCorrector(
                ds_mod=ds_mod,
                ds_obs=ds_obs,
                ds_cal=ds_cal,
                implementation=self.implementation,
                niterations=self.niterations,
                nbins=self.nbins,
                kind=self.kind
            )

        else:
            message = f"Corrector type {corrector.type} not implemented"
            raise Exception(message)

        correction = corrector.fit_predict(
            ds_mod=ds_mod,
        )

        return correction


class UQMCorrector(PDFCorrector):

    """
    Univariate Quantile Corrector (UQM) for xarray Dataset
    """

    # Convention: nu_* refers to arrays with numerical values only (i.e.
    # without NaNs). np_* refers to arrays with numerical values and NaN
    # values. This is needed because some data on a raster can have no values
    # (e.g. due to missing radar coverage)

    def __str__(self):

        import textwrap

        return textwrap.dedent(
            f"""
            Univariate Quantile Corrector (UQM)
            Number of nbins: {self.nbins}
            """
        )

    def __init__(self, *, ds_obs=None, ds_cal=None, nbins=None):

        """
        Class initialization

        Initialize the Quantile Correcter with data from the training dataset

        Arguments:
           ds_obs (:class:`xarray.Dataset`): The reference dataset.
           ds_cal (:class:`xarray.Dataset`): The model calibration dataset.
           nbin (int): Number of bins (e.g. 128)
        """

        import textwrap

        self.bc_method_id = 'uqm'
        self.ds_obs = ds_obs
        self.ds_cal = ds_cal
        self.nbins = nbins
        self.method = UQM(nbins=self.nbins)

        # Sanity checks
        # -------------

        assert nbins is not None, "Parameter 'nbins' is mandatory"
        assert ds_obs is not None, "Parameter 'ds_obs' is mandatory"
        assert ds_cal is not None, "Parameter 'ds_cal' is mandatory"

        if len(self.ds_obs.data_vars) != len(self.ds_cal.data_vars):

            message = textwrap.dedent(
                """
                The calibration and observation datasets do not contain the
                same number variables. The calibration dataset contains
                {self.ds_cal.data_vars} and the observation dataset contains
                {self.ds_obs.data_vars}.
                """
            )

            raise Exception(message)

    def fit(self):

        """
        Compute the map
        """

        import numpy as np
        import pyku.meta as libmetadata

        # Get name of data variables
        # --------------------------

        obs_varnames = sorted(libmetadata.get_geodata_varnames(self.ds_obs))
        cal_varnames = sorted(libmetadata.get_geodata_varnames(self.ds_cal))

        if obs_varnames != cal_varnames:

            message = (
                f"obs_varnames is {obs_varnames} should equal cal_varnames "
                f"{cal_varnames}"
            )

            raise Exception(message)

        # Construct numpy arrays of size nfeatures x npixels
        # --------------------------------------------------

        np_obs = np.array([
            self.ds_obs[var].values.reshape(-1) for var in obs_varnames
        ])

        np_cal = np.array([
            self.ds_cal[var].values.reshape(-1) for var in cal_varnames
        ])

        # Construct numpy arrays of size nfeatures x npixels without NaNs
        # ---------------------------------------------------------------

        nu_obs = np.array([
            np_obs[idx][np.isfinite(np_obs[idx])]
            for idx in range(np_obs.shape[0])
        ])

        nu_cal = np.array([
            np_cal[idx][np.isfinite(np_cal[idx])]
            for idx in range(np_cal.shape[0])
        ])

        # Fit
        # ---

        self.method.fit(np_cal=nu_cal, np_obs=nu_obs)

    def predict(self, ds_mod=None):

        """
        Predict

        Arguments:
            ds_mod (:class:`xarray.Dataset`): Biased dataset to be corrected

        Returns:
            :class:`xarray.Dataset`: Bias corrected dataset
        """

        import textwrap
        import numpy as np
        import pyku.meta as libmetadata

        if len(self.ds_obs.data_vars) != len(ds_mod.data_vars):
            message = textwrap.dedent(
                f"""
                The dataset to be corrected and the observation datasets do not
                contain the same number of variables. The dataset to be
                corrected contains {ds_mod.data_vars} and the observation
                dataset contains {self.ds_obs.data_vars}.
                """
            )
            raise Exception(message)

        # Get name of data variables
        # --------------------------

        varnames = sorted(libmetadata.get_geodata_varnames(ds_mod))

        # Get original shape of data from the first variable
        # --------------------------------------------------

        original_shape = ds_mod[varnames[0]].shape

        # Construct numpy arrays of size nfeatures x npixels
        # --------------------------------------------------

        np_mod = np.array([ds_mod[var].values.reshape(-1) for var in varnames])

        # Construct numpy arrays of size nfeatures x npixels without NaNs
        # ---------------------------------------------------------------

        nu_mod = np.array([
            np_mod[idx][np.isfinite(np_mod[idx])]
            for idx in range(np_mod.shape[0])
        ])

        # Correct
        # -------

        nu_cor = self.method.predict(np_mod=nu_mod)

        # Initialize output with the same size as the input filled with NaNs
        # ------------------------------------------------------------------

        np_cor = np.full(np_mod.shape, np.nan, dtype=float_type)

        # Place transformed numerical data where original array not NaN
        # -------------------------------------------------------------

        np.place(np_cor, np.isfinite(np_mod), nu_cor)

        # Deep copy the original data
        # ---------------------------

        ds_cor = ds_mod.copy(deep=True)

        # Reshape data to the original 2D array shape and mask
        # ----------------------------------------------------

        for idx, varname in enumerate(varnames):
            ds_cor[varname].values = np_cor[idx, ...].reshape(original_shape)

        return ds_cor

    def fit_predict(self, ds_mod=None):

        """
        Fit and predict

        Arguments:
            ds_md (:class:`xarray.Dataset`): Biased dataset to be corrected

        Returns:
            :class:`xarray.Dataset`: Corrected dataset
        """

        self.fit()

        return self.predict(ds_mod=ds_mod)

    def save(self, pickle_file):

        """
        Save map to file

        Args:
            pickle_file (str): File name
        """

        import pickle

        self.ds_obs.close()
        self.ds_cal.close()

        with open(pickle_file, 'wb') as handle:
            pickle.dump(self, handle, pickle.HIGHEST_PROTOCOL)


class NDPDFCorrector(PDFCorrector):

    """
    N-Dimensional Probability Distribution Transfer (NDPDF) for xarray Dataset
    """

    def __str__(self):

        import textwrap

        return textwrap.dedent(
            f"""
            N-Dimensional Probability Distribution Transfer (NDPDF)
            Number of nbins: {self.nbins}
            Number of iterations: {self.niterations}
            """
        )

    def __init__(
            self, *, ds_cal=None, ds_obs=None, niterations=None, nbins=None):

        """
        Initialize

        Arguments:
           obs_da (:class:`xarray.Dataset`): Calibration observation dataset.
           cal_da (:class:`xarray.Dataset`): Calibration model dataset.
           niterations (int): Number of iterations (e.g. 20)
           nbins (int): Number of percentile bins (e.g. 128)
        """

        self.bc_method_id = 'ndpdf'
        self.ds_obs = ds_obs
        self.ds_cal = ds_cal

        self.nbins = nbins
        self.niterations = niterations
        self.method = NDPDF(
            niterations=self.niterations,
            nbins=self.nbins
        )

        assert self.nbins is not None, "Parameter 'nbins' is mandatory"

        assert self.niterations is not None, \
            "Parameter 'niterations' is mandatory"

    def fit(self):

        """
        Compute map
        """

        import numpy as np
        import pyku.meta as libmetadata

        # Get name of data variables
        # --------------------------

        obs_varnames = sorted(libmetadata.get_geodata_varnames(self.ds_obs))
        cal_varnames = sorted(libmetadata.get_geodata_varnames(self.ds_cal))

        # Sanity check
        # ------------

        assert obs_varnames == cal_varnames, \
            f"obs_varnames is {obs_varnames} should equal cal_varnames {cal_varnames}"  # noqa

        # Construct numpy arrays of size nfeatures x npixels
        # --------------------------------------------------

        np_obs = np.array([
            self.ds_obs[var].values.reshape(-1) for var in obs_varnames
        ])

        np_cal = np.array([
            self.ds_cal[var].values.reshape(-1) for var in cal_varnames
        ])

        # Construct numpy arrays of size nfeatures x npixels without NaNs
        # ---------------------------------------------------------------

        nu_obs = np.array([
            np_obs[idx][np.isfinite(np_obs[idx])]
            for idx in range(np_obs.shape[0])
        ])

        nu_cal = np.array([
            np_cal[idx][np.isfinite(np_cal[idx])]
            for idx in range(np_cal.shape[0])
        ])

        # Fit
        # ---

        self.method.fit(np_cal=nu_cal, np_obs=nu_obs)

    def predict(self, ds_mod=None):

        """
        Predict

        Arguments:
            ds_mod (xarray.Dataset): Biased dataset

        Returns:
            xarray.Dataset: Corrected dataset
        """

        import numpy as np
        import pyku.meta as libmetadata

        # Get name of data variables
        # --------------------------

        varnames = sorted(libmetadata.get_geodata_varnames(ds_mod))

        # Get original shape of data from the first variable
        # --------------------------------------------------

        original_shape = ds_mod[varnames[0]].shape

        # Construct numpy arrays of size nfeatures x npixels
        # --------------------------------------------------

        np_mod = np.array([ds_mod[var].values.reshape(-1) for var in varnames])

        # Set data type
        # -------------

        np_mod = np_mod.astype(float_type)

        # Construct numpy arrays of size nfeatures x npixels without NaNs
        # ---------------------------------------------------------------

        nu_mod = np.array([
            np_mod[idx][np.isfinite(np_mod[idx])]
            for idx in range(np_mod.shape[0])
        ])

        # Predict
        # -------

        nu_cor = self.method.predict(np_mod=nu_mod)

        # Set data type
        # -------------

        nu_cor = nu_cor.astype(float_type)

        # Initialize output with the same size as the input filled with NaNs
        # ------------------------------------------------------------------

        np_cor = np.full(np_mod.shape, np.nan, dtype=float_type)

        # Place transformed numerical data where original array not NaN
        # -------------------------------------------------------------

        np.place(np_cor, np.isfinite(np_mod), nu_cor)

        # Deep copy the original data
        # ---------------------------

        ds_cor = ds_mod.copy(deep=True)

        # Reshape data to the original 2D array shape and mask
        # ----------------------------------------------------

        for idx, varname in enumerate(varnames):
            ds_cor[varname].values = np_cor[idx, ...].reshape(original_shape)

        return ds_cor

    def save(self, pickle_file):

        """
        Save map to file
        """

        import pickle

        # Delete the data themselves, as only the map is needed
        # -----------------------------------------------------

        self.ds_obs.close()
        self.ds_cal.close()

        self.ds_obs = None
        self.ds_cal = None

        with open(pickle_file, 'wb') as handle:
            pickle.dump(self, handle, pickle.HIGHEST_PROTOCOL)


class QDMCorrector(PDFCorrector):

    """
    Quantile Delta Mapping Corrector (QDM) for :class:`xarray.Dataset`

    https://journals.ametsoc.org/view/journals/clim/28/17/jcli-d-14-00754.1.xml
    """

    def __str__(self):

        import textwrap

        return textwrap.dedent(
            f"""
            Quantile Delta Mapping Corrector (QDM)
            Implementation: {self.implementation}
            Kind: {self.kind}
            Number of nbins: {self.nbins}
            """
        )

    def __init__(
            self, *, ds_mod=None, ds_obs=None, ds_cal=None, nbins=None,
            kind=None, implementation='SH'):

        """
        Corrector initialization

        Arguments:

           ds_obs (:class:`xarray.Dataset`): The reference dataset.
           ds_cal (:class:`xarray.Dataset`): The biased calibration dataset.
           ds_mod (:class:`xarray.Dataset`): The biased model dataset.
           nbins (int): Number of bins in the histograms.
           kind (str): Either 'additive' or 'multiplicative'.
           implementation: Either 'SH', 'MBC', or 'SBCK'. 'SH' corresponds to
               the implementation by S. Haussler. 'SBCK' corresponds to the
               implementation of the Statistical Bias Correction Kit:
               https://github.com/yrobink/SBCK-python/. The two independent
               implementations permit to check for correctness.
        """

        import pandas as pd

        self.bc_method_id = 'QDM'
        self.bc_method = 'Quantile Delta Mapping (QDM)'
        self.bc_period = (
            f"{ds_obs.time.dt.year.min().item()}-"
            f"{ds_obs.time.dt.year.max().item()}"
        )
        self.creation_date = pd.Timestamp.today().strftime("%Y-%m-%d %H:%M")
        self.ds_mod = ds_mod
        self.ds_obs = ds_obs
        self.ds_cal = ds_cal
        self.ds_cor = None  # Placeholder for corrected dataset
        self.implementation = implementation
        self.nbins = nbins
        self.kind = kind

        # Sanity checks
        # -------------

        assert kind is not None, "Parameter 'kind' is mandatory"
        assert ds_mod is not None, "Parameter 'ds_mod' is mandatory"
        assert ds_obs is not None, "Parameter 'ds_obs' is mandatory"
        assert ds_cal is not None, "Parameter 'ds_cal' is mandatory"

        if self.implementation in ['SBCK'] and nbins is not None:
            raise Exception(
                "The SBCK implemenation of QDM does not require the parameter"
                "'nbins'."
            )

        if self.implementation not in ['SBCK'] and nbins is None:
            raise Exception("Parameter 'nbins' is mandatory")

    def fit_predict(self):

        """
        Fit and predict.

        Returns:
            :class:`xarray.Dataset`: The corrected dataset.
        """

        import textwrap
        import numpy as np
        import pyku.meta as libmetadata

        # Get name of data variables
        # --------------------------

        obs_varnames = sorted(libmetadata.get_geodata_varnames(self.ds_obs))
        mod_varnames = sorted(libmetadata.get_geodata_varnames(self.ds_mod))
        cal_varnames = sorted(libmetadata.get_geodata_varnames(self.ds_cal))

        if obs_varnames != mod_varnames or obs_varnames != cal_varnames:

            message = textwrap.dedent(
                f"""
                Issue found with the variables contained in the datasets:
                obs_varnames: {obs_varnames}
                mod_varnames: {mod_varnames}
                cal_varnames: {mod_varnames}

                The variable names should be the same
                """
            )

            raise Exception(message)

        # Construct numpy arrays of size nfeatures x npixels
        # --------------------------------------------------

        np_obs = np.array([
            self.ds_obs[var].values.reshape(-1) for var in obs_varnames
        ])

        np_mod = np.array([
            self.ds_mod[var].values.reshape(-1) for var in mod_varnames
        ])

        np_cal = np.array([
            self.ds_cal[var].values.reshape(-1) for var in cal_varnames
        ])

        # Cast types
        # ----------

        np_obs = np_obs.astype(float_type)
        np_mod = np_mod.astype(float_type)
        np_cal = np_cal.astype(float_type)

        # Construct numpy arrays of shape nfeatures x npixels without NaNs
        # ----------------------------------------------------------------

        nu_mod = np.array([
            np_mod[idx][np.isfinite(np_mod[idx])]
            for idx in range(np_mod.shape[0])
        ])

        nu_obs = np.array([
            np_obs[idx][np.isfinite(np_obs[idx])]
            for idx in range(np_obs.shape[0])
        ])

        nu_cal = np.array([
            np_cal[idx][np.isfinite(np_cal[idx])]
            for idx in range(np_cal.shape[0])
        ])

        # Cast types
        # ----------

        nu_mod = nu_mod.astype(float_type)
        nu_obs = nu_obs.astype(float_type)
        nu_cal = nu_cal.astype(float_type)

        if nu_mod.size == 0 or nu_obs.size == 0 or nu_cal.size == 0:

            # Get original shape of data from the first variable
            # --------------------------------------------------

            original_shape = self.ds_mod[mod_varnames[0]].shape

            # Initialize output with same size as input filled with NaNs
            # ----------------------------------------------------------

            np_cor = np.full(np_mod.shape, np.nan, dtype=float_type)

            # Deep copy the original data
            # ---------------------------

            ds_cor = self.ds_mod.copy(deep=True)

            # Reshape data to the original 2D array shape and mask
            # ----------------------------------------------------

            for idx, varname in enumerate(mod_varnames):

                ds_cor[varname].values = \
                    np_cor[idx, ...].reshape(original_shape)

            return ds_cor

        # Apply tranformation
        # -------------------

        if self.implementation in ['SBCK']:

            try:
                from SBCK import QDM as SBCK_QDM
            except Exception as e:
                message = (
                    f"{e} "
                    "The SBCK module coult not be loaded. Check the "
                    "documentation for instructions on how to install."
                )
                raise Exception(message)

            method = SBCK_QDM(delta=self.kind)
            method.fit(nu_obs.T, nu_cal.T, nu_mod.T)
            nu_cor = method.predict(nu_mod.T).T

        elif self.implementation in ['SH']:

            method = QDM(nbins=self.nbins, kind=self.kind)

            nu_cor, nu_car = method.fit_predict(
                np_mod=nu_mod,
                np_cal=nu_cal,
                np_obs=nu_obs
            )

        elif self.implementation in ['MBC']:

            # Import MBC R library
            # --------------------

            from rpy2.robjects.packages import importr
            import rpy2.robjects.numpy2ri

            MBC = importr("MBC")
            rpy2.robjects.numpy2ri.activate()

            # Perform correction
            # ------------------

            nu_car, nu_cor = MBC.QDM(
                nu_obs,
                nu_cal,
                nu_mod,
                ratio=self.kind in ['multiplicative'],
                n_tau=self.nbins
            )

        else:
            message = textwrap.dedent(
                f"""
                implementation shall be 'SBCK', 'MBC', or 'SH', not
                {self.implementation}
                """)

            raise Exception(message)

        # Get original shape of data from the first variable
        # --------------------------------------------------

        original_shape = self.ds_mod[mod_varnames[0]].shape

        # Initialize output with the same size as the input filled with NaNs
        # ------------------------------------------------------------------

        np_cor = np.full(np_mod.shape, np.nan, dtype=float_type)

        # Place transformed numerical data where original array not NaN
        # -------------------------------------------------------------

        np.place(np_cor, np.isfinite(np_mod), nu_cor)

        # Deep copy the original data
        # ---------------------------

        ds_cor = self.ds_mod.copy(deep=True)

        # Reshape data to the original 2D array shape and mask
        # ----------------------------------------------------

        for idx, varname in enumerate(mod_varnames):
            ds_cor[varname] = ds_cor[varname]
            ds_cor[varname].values = np_cor[idx, ...].reshape(original_shape)

        return ds_cor


class MBCnCorrector(PDFCorrector):

    """
    MBCn Corrector for xarray DataSet
    """

    def __str__(self):

        import textwrap

        return textwrap.dedent(
            f"""
            MBCn Corrector
            Implementation: {self.implementation}
            Number of nbins: {self.nbins}
            Number of niterations: {self.niterations}
            Kind: {self.kind}
            """
        )

    def __init__(
            self, *, ds_mod=None, ds_obs=None, ds_cal=None, nbins=None,
            niterations=None, kind=None, implementation='SH'):

        """
        Initialize Corrector

        Arguments:
           ds_obs (:class:`xarray.Dataset`): Reference data for calibration
           ds_mod (:class:`xarray.Dataset`): Biased data for calibration
           ds_dat (:class:`xarray.Dataset`): Biased data to be corrected
           nbins (int): number of bins in histogram
           niterations (int): Number of iterations
           kind (str): Either 'additive' or 'multiplicative'
        """

        import pandas as pd

        self.bc_method_id = 'mbcn'
        self.bc_method = 'MBCn'
        self.bc_period = (
            f"{ds_obs.time.dt.year.min().item()}-"
            f"{ds_obs.time.dt.year.max().item()}"
        )
        self.creation_date = pd.Timestamp.today().strftime("%Y-%m-%d %H:%M")
        self.implementation = implementation
        self.ds_mod = ds_mod
        self.ds_obs = ds_obs
        self.ds_cal = ds_cal
        self.niterations = niterations
        self.nbins = nbins
        self.kind = kind

    def fit_predict(self):

        """
        Compute the map
        """

        import textwrap
        import warnings
        import numpy as np
        import pyku.meta as libmetadata

        # Get name of data variables
        # --------------------------

        obs_varnames = sorted(libmetadata.get_geodata_varnames(self.ds_obs))
        mod_varnames = sorted(libmetadata.get_geodata_varnames(self.ds_mod))
        cal_varnames = sorted(libmetadata.get_geodata_varnames(self.ds_cal))

        if obs_varnames != mod_varnames or obs_varnames != cal_varnames:
            message = textwrap.dedent(
                f"""
                Issue found with the variables contained in the datasets:
                obs_varnames: {obs_varnames}
                mod_varnames: {mod_varnames}
                cal_varnames: {mod_varnames}

                The variable names should be the same
                """)
            raise Exception(message)

        # Construct numpy arrays of size nfeatures x npixels
        # --------------------------------------------------

        np_obs = np.array([
            self.ds_obs[var].values.reshape(-1) for var in obs_varnames
        ])

        np_mod = np.array([
            self.ds_mod[var].values.reshape(-1) for var in mod_varnames
        ])

        np_cal = np.array([
            self.ds_cal[var].values.reshape(-1) for var in cal_varnames
        ])

        # Construct numpy arrays of shape nfeatures x npixels without NaNs
        # ----------------------------------------------------------------

        try:

            nu_mod = np.array([
                np_mod[idx][np.isfinite(np_mod[idx])]
                for idx in range(np_mod.shape[0])
            ])

        except Exception as e:
            debug_info = []
            debug_info.append("All lengths should be equal in mod")
            for idx in range(np_mod.shape[0]):
                arr = np_mod[idx][np.isfinite(np_mod[idx])]
                debug_info.append(f"idx={idx}, length={len(arr)}")

            error_msg = (
                f"{e}\nShape: {np_mod.shape}\n" + "\n".join(debug_info)
            )

            raise ValueError(error_msg)

        try:
            nu_obs = np.array([
                np_obs[idx][np.isfinite(np_obs[idx])]
                for idx in range(np_obs.shape[0])
            ])

        except Exception as e:
            debug_info = []
            debug_info.append("All lengths should be equal in obs")
            for idx in range(np_obs.shape[0]):
                arr = np_obs[idx][np.isfinite(np_obs[idx])]
                debug_info.append(f"idx={idx}, length={len(arr)}")

            error_msg = (
                f"{e}\nShape: {np_obs.shape}\n" + "\n".join(debug_info)
            )

            raise ValueError(error_msg)

        try:
            nu_cal = np.array([
                np_cal[idx][np.isfinite(np_cal[idx])]
                for idx in range(np_cal.shape[0])
            ])

        except Exception as e:
            debug_info = []
            debug_info.append("All lengths should be equal in cal")
            for idx in range(np_cal.shape[0]):
                arr = np_cal[idx][np.isfinite(np_cal[idx])]
                debug_info.append(f"idx={idx}, length={len(arr)}")

            error_msg = (
                f"{e}\nShape: {np_mod.shape}\n" + "\n".join(debug_info)
            )

            raise ValueError(error_msg)

        if nu_mod.size == 0 or nu_obs.size == 0 or nu_cal.size == 0:

            # Get original shape of data from the first variable
            # --------------------------------------------------

            original_mod_shape = self.ds_mod[mod_varnames[0]].shape
            # original_cal_shape = self.ds_mod[cal_varnames[0]].shape

            # Initialize output with same size as input filled with NaNs
            # ----------------------------------------------------------

            np_cor = np.full(np_mod.shape, np.nan, dtype=float_type)
            # np_car = np.full(np_car.shape, np.nan)

            # Deep copy the original data
            # ---------------------------

            ds_cor = self.ds_mod.copy(deep=True)
            # ds_car = self.ds_car.copy(deep=True)

            # Reshape data to the original 2D array shape and mask
            # ----------------------------------------------------

            for idx, varname in enumerate(mod_varnames):
                ds_cor[varname].values = \
                    np_cor[idx, ...].reshape(original_mod_shape)

            # for idx, varname in enumerate(cal_varnames):
            #     ds_car[varname].values = \
            #            np_car[idx,...].reshape(original_cal_shape)

            return ds_cor  # , ds_car

        # Fit predict
        # -----------

        if self.implementation in ['SH']:

            self.method = MBCn(
                nbins=self.nbins,
                niterations=self.niterations,
                kind=self.kind
            )

            nu_cor, nu_car = self.method.fit_predict(
                np_mod=nu_mod,
                np_obs=nu_obs,
                np_cal=nu_cal
            )

        elif self.implementation in ['SBCK']:

            from SBCK import MBCn as SBCK_MBCn

            self.method = SBCK_MBCn(
                kind=self.kind,
                metric=lambda x, y: 999,
                stopping_criteria_params={
                    "minit": self.niterations,
                    "maxit": self.niterations,
                    "tol": 1e-3
                }
            )

            self.method.fit(nu_obs.T, nu_cal.T, nu_mod.T)

            nu_cor, nu_car = self.method.predict(nu_mod.T, nu_cal.T)
            nu_cor = nu_cor.T
            nu_car = nu_car.T

        elif self.implementation in ['MBC']:

            # Import MBC R library
            # --------------------

            from rpy2.robjects.packages import importr
            import rpy2.robjects.numpy2ri

            MBC = importr("MBC")
            rpy2.robjects.numpy2ri.activate()

            # Perform correction
            # ------------------

            warnings.warn("Ratio seems to take a column of booleans")
            out_ = MBC.MBCn(
                nu_obs.T,
                nu_cal.T,
                nu_mod.T,
                iter=self.niterations,
                n_tau=self.nbins,
                ratio_max=2
                # ratio=self.kind in ['multiplicative']
            )

            pydict = dict(zip(out_.names, map(list, list(out_))))

            nu_car = np.array(pydict['mhat.c'])
            nu_cor = np.array(pydict['mhat.p'])

            nu_car = nu_car.T
            nu_cor = nu_cor.T

        else:

            message = textwrap.dedent(
                f"""
                Implementation should be 'SH' or 'SBCK', not
                {self.implementation}
                """
            )

            raise Exception(message)

        # Get original shape of data from the first variable
        # --------------------------------------------------

        original_mod_shape = self.ds_mod[mod_varnames[0]].shape
        # original_cal_shape = self.ds_cal[cal_varnames[0]].shape

        # Initialize output with the same size as the input filled with NaNs
        # ------------------------------------------------------------------

        np_cor = np.full(np_mod.shape, np.nan, dtype=float_type)
        # np_car = np.full(np_cal.shape, np.nan)

        # Place transformed numerical data where original array not NaN
        # -------------------------------------------------------------

        nu_cor = nu_cor.astype(float_type)
        np.place(np_cor, np.isfinite(np_mod), nu_cor)
        # np.place(np_car, np.isfinite(np_cal), nu_car)

        # Deep copy the original xarray datasets
        # --------------------------------------

        ds_cor = self.ds_mod.copy(deep=True)
        # ds_car=self.ds_cal.copy(deep=True)

        # Reshape data to the original 2D array shape and mask
        # ----------------------------------------------------

        for idx, varname in enumerate(mod_varnames):

            ds_cor[varname].values = \
                np_cor[idx, ...].reshape(original_mod_shape)

            # ds_car[varname].values = \
            #    np_car[idx,...].reshape(original_cal_shape)

        return ds_cor  # , ds_car
