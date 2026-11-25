""" Module for LOESS smoothing of time series data
"""
import logging
from collections.abc import Callable, Hashable
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, Literal

import numpy as np
import pandas as pd
import skmisc.loess
from skmisc.loess import loess as skloess

import xarray as xr

logger = logging.getLogger(__name__)

_SpatialReduce = Literal[True] | list[str] | Callable[..., Any] | None


@dataclass
class Loess:
    """ Dataclass to hold LOESS smoothing results """
    _x: list
    _pred: skmisc.loess.loess_prediction
    _conf: SimpleNamespace

    def __repr__(self):
        return f"{self.df}"

    @property
    def time(self):
        """ Time values """
        return self._x

    @time.setter
    def time(self, values):
        self._x = values

    @property
    def values(self):
        """ Smoothed values """
        return self._pred.values

    @property
    def upper(self) -> np.array:
        """ Upper bound of confidence interval """
        return self._conf.upper

    @property
    def lower(self) -> np.array:
        """ Lower bound of confidence interval """
        return self._conf.lower

    @property
    def df(self) -> pd.DataFrame:
        """ DataFrame with smoothed values and confidence intervals """
        return pd.DataFrame({
            'time': self._x,
            'values': self._pred.values,
            'upper': self.upper,
            'lower': self.lower
        })

    def trend(self, target, ref, index=True) -> tuple:
        """ Calculate trend for a target and reference period

        Arguments:
            target: the target time/index
            ref: a tuple with start and end of reference index/period
                Note the end is exclusive for indexed based referencing,
                so ref=(0,20) means indices 0 to 19
                but inclusive for time-based referencing,
                so ref=(time1,time2) means from time1 to time2 including time2
            index: bool, if target and ref are indices, else time values

        Returns:
            trend: tuple with (target, trend value)
        """
        if not index:
            # Convert time values to indices
            import bisect
            if target not in self._x:
                raise ValueError("Target time value not found in time series")

            ref = (bisect.bisect_left(self._x, ref[0]),
                   bisect.bisect_right(self._x, ref[1]))
            target = bisect.bisect_left(self._x, target)

        ref_mean = self.values[slice(*ref)].mean()
        target_value = self.values[target]
        trend = target_value - ref_mean
        return (self._x[target], trend)


def loess(x, y, conf='wald', **loess_kwargs) -> tuple:
    """Low level binding of the skmisc.loess function for
    a simple x and y series pair and a bunch of attributes.
    If no attributes are given, the definitions of DWD and
    KNMI are prescribed

    Arguments:
        x: (Union[List,np.array,ndarray]) list of time information. e.g.
            list of years,...
        y: (Union[List,np.array,ndarray]) list of values to be estimated
        **loess_kwargs : keyword arguments directly passed to skmics.loess
            if not explicetly given, the KNMI-defaults are set

    Returns:
        Tuple (pred,conf) : pred is a skmisc.loess.prediction object. values
            can be retrieved using pred.values. conf is a
            skmisc.loess.confidence object, that contains .lower and .upper
            bounds

    Example:
        .. ipython::
            :okwarning:

            @savefig loess_example.png width=6in
            In [0]:
               ...: import pandas as pd
               ...: import numpy as np
               ...: import matplotlib.pyplot as plt
               ...: from pyku.loess import loess
               ...: x = pd.date_range(start='1920-06-01',
               ...:                   periods=101,
               ...:                   freq='YS')
               ...: y = np.random.randn(101).cumsum()
               ...: result = loess(x, y)
               ...: plt.figure(figsize=(10, 6))
               ...: plt.plot(x, y, label='Original Data', alpha=0.5)
               ...: plt.plot(x, result.values, label='Loess Smoothed',
               ...:          color='red')
               ...: plt.fill_between(x, result.lower, result.upper,
               ...:                  color='red', alpha=0.2,
               ...:                  label='Confidence Interval')
               ...: plt.legend()
    """

    # Default set for loess calculation given by KNMI
    # https://cdn.knmi.nl/system/ckeditor_assets/attachments/161/TR389.pdf
    if 'span' not in loess_kwargs:
        if len(x) <= 42:
            raise ValueError(('Time Series shorter than 42 entries are not'
                              ' supported with default span. Please manually'
                              ' set span argument to an appropriate value.'))
        loess_kwargs['span'] = 42.0 / len(x)
    if 'degree' not in loess_kwargs:
        loess_kwargs['degree'] = 1
    if 'family' not in loess_kwargs:
        loess_kwargs['family'] = 'gaussian'
    if 'surface' not in loess_kwargs:
        loess_kwargs['surface'] = 'direct'
    if 'statistics' not in loess_kwargs:
        loess_kwargs['statistics'] = 'exact'

    # Apply LOESS
    lo = skloess(
        x,
        y,
        **loess_kwargs
    )
    lo.fit()
    pred = lo.predict(x, stderror=True)

    if conf == 'wald':
        conf = _wald_confidence(pred)
    elif conf == 'bootstrap':
        # Bootstrapping with 1001 repetitions
        conf = _bootstrap_loess(x, y, **loess_kwargs)
    elif conf == 'internal':
        # scikit-misc internal confidence...
        # not looked into it how this gets estimated
        conf = pred.confidence()
    else:
        raise ValueError("Method for confidence estimation not supported")

    return Loess(x, pred, conf)


def _wald_confidence(pred):
    z = 1.959963984540054
    lower = pred.values - z * pred.stderr
    upper = pred.values + z * pred.stderr
    return SimpleNamespace(lower=lower, upper=upper)


def _bootstrap_loess(x, y, N=1001, **loess_kwargs):
    z = 1.959963984540054
    # Bootstrap zur Bestimmung des Konfidenzintervalls
    smooths = np.stack(
        [_smooth(x, y, **loess_kwargs) for k in range(N)]).T

    mean = np.nanmean(smooths, axis=1)
    stderr = np.nanstd(smooths, axis=1, ddof=0)
    lower, upper = mean - z*stderr, mean + z*stderr
#    # Berechnen der Konfidenzkorridore
#    c25 = np.nanpercentile(smooths, 2.5, axis=1) #2.5 percent
#    c97 = np.nanpercentile(smooths, 97.5, axis=1) # 97.5 percent
    return SimpleNamespace(lower=lower, upper=upper)


def _smooth(x, y, **loess_kwargs):
    samples = np.random.choice(len(x), len(x), replace=True)
    y_s = y[samples]
    x_s = x[samples]
    y_sm = skloess(x_s, y_s, **loess_kwargs)
    y_sm.fit()
    return y_sm.predict(x).values


def _wrap_loess(x, y, conf='wald', **loess_kwargs):
    loess_result = loess(x, y, conf=conf, **loess_kwargs)
    return np.stack([loess_result.values,
                     loess_result.lower,
                     loess_result.upper],
                    axis=0)


def calc_loess(
    ds: xr.Dataset,
    var: Hashable | None = None,
    spatial_reduce: _SpatialReduce = None,
    frequency: str | None = '1YS',
    time_reduce: str | Callable[..., Any] = 'mean',
    **loess_kwargs: Any,
) -> xr.Dataset:
    """Backward-compatible forwarding to :func:`pyku.compute.calc_loess`."""
    logger.warning(
        "`pyku.loess.calc_loess` will be removed in a future release because "
        "it has moved to `pyku.compute.calc_loess`; use that function instead."
    )
    from pyku.compute import calc_loess as compute_calc_loess

    return compute_calc_loess(
        ds,
        var=var,
        spatial_reduce=spatial_reduce,
        frequency=frequency,
        time_reduce=time_reduce,
        **loess_kwargs
    )
