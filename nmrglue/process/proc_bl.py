"""
A collection of NMR processing functions for filtering, smoothing, and
correcting spectral baselines.
"""

import numpy as np
import scipy
import scipy.ndimage
import scipy.signal
from itertools import groupby
from operator import itemgetter
from numbers import Real


# Linear (First order) baseline correction
def base(data, nl, nw=0):
    """
    Linear (first-order) baseline correction based on node list.

    Parameters
    ----------
    data : 1D or 2D ndarray
        Array of 1D or 2D NMR data.
    nl : list
        List of baseline nodes.
    nw : int, optional
        Node half-width in points.

    Returns
    -------
    ndata : ndarray
        NMR data with first order baseline correction applied.  For 2D data
        baseline correction is applied for each trace along the last
        dimension.

    """
    if data.ndim == 1:
        data = data - calc_bl_linear(data, nl, nw)
    else:   # for 2D array loop over traces
        for i, vec in enumerate(data):
            data[i] = data[i] - calc_bl_linear(vec, nl, nw)
    return data


def calc_bl_linear(x, nl, nw=0):
    """
    Calculate a baseline using linear approximation between nodes

    Parameters
    ----------
    x : 1D ndarray
        One-dimensional NMR data.
    nl : list
        List of baseline nodes
    nw : int
        Node half-width in points. Averaging windows are clipped to the
        available samples at either edge.

    Returns
    -------
    baseline : ndarray
        Base calculated using linear approximation between nodes.

    """
    bl = np.zeros_like(x)
    for i in range(len(nl) - 1):
        # minimum and maximum index
        start = nl[i]
        stop = nl[i + 1]
        # linspace s1 and s2
        s1 = x[max(0, start - nw):min(x.size, start + nw + 1)].mean()
        s2 = x[max(0, stop - nw):min(x.size, stop + nw + 1)].mean()
        bl[start:stop + 1] = np.linspace(s1, s2, stop - start + 1)
    return bl


# Constant baseline correction
def cbf(data, last=10, apply=slice(None)):
    """
    Constant baseline correction from percentage of data.

    Parameters
    ----------
    data : 1D or 2D ndarray
        Array of 1D or 2D NMR data.
    last : float, optional
        Percent (0 - 100) of last axis used to calculate the baseline
        correction. The historical selection includes one trailing sample
        beyond the truncated percentage, up to the full trace length.
    apply : slice, optional
        Slice describing first-axis region(s) to which the baseline correction
        should be applied.  Parameter is ignored for 1D data.

    Returns
    -------
    ndata : 1D or 2D ndarray
        NMR data with a constant baseline subtracted.

    """
    # calculate the correction
    if not isinstance(last, Real) or not np.isfinite(last) or not 0 <= last <= 100:
        raise ValueError("last must be a finite percentage between 0 and 100")
    size = data.shape[-1]
    if size == 0:
        raise ValueError("cannot estimate baseline from an empty trace")
    n = min(size, int(size * last // 100) + 1)
    corr = data[..., -n:].mean(axis=-1)

    # apply correction
    if data.ndim == 2:
        data[apply] = data[apply] - np.array([corr]).transpose()[apply]
        return data
    else:
        return data - corr


def cbf_explicit(data, calc=slice(None), apply=slice(None)):
    """
    Constant Baseline correction from an explicit region of the data.

    Parameters
    ----------
    data : 1D or 2D ndarray
        Array of 1D or 2D NMR data.
    calc : slice, optional
        Slice describing region to use for calculating the baseline correction.
    apply : slice, optional
        Slice describing first-axis region(s) to which the baseline correction
        should be applied.  Parameter is ignored for 1D data.

    Returns
    -------
    ndata : 1D or 2D ndarray
        NMR data with a constant baseline subtracted.

    """
    # calculate correction
    n = len(range(data.shape[-1])[calc])
    corr = data[..., calc].sum(axis=-1) / n

    # apply correction
    if data.ndim == 2:
        data[apply] = data[apply] - np.array([corr]).transpose()[apply]
        return data
    else:
        return data - corr


# Median baseline correction
def med(data, mw=24, sf=16, sigma=5.0):
    """
    Median baseline correction.

    Algorithm described in: Friedrichs, M.S. JBNMR 1995 5 147-153.

    Parameters
    ----------
    data : 1D or 2D ndarray
        Array of 1D or 2D NMR data.
    mw : float
        Median window size in pts.
    sf : float
        Smooth window size in pts.
    sigma : float
        Standard-deviation of convoluted Gaussian window.

    Returns
    -------
    ndata : 1D or 2D ndarray
        NMR data with the median baseline subtracted.

    """
    if data.ndim == 1:
        data = data - calc_bl_med(data, mw, sf, sigma)
    else:
        for i, vec in enumerate(data):
            data[i] = vec - calc_bl_med(vec, mw, sf, sigma)
    return data


def calc_bl_med(x, mw, sf, sigma):
    """
    Calculate a baseline using median baseline correction.

    Algorithm described in: Friedrichs, M.S. JBNMR 1995 5 147-153

    Parameters
    ----------
    x : 1D ndarray
        One dimensional NMR data
    mw : float
        Median window size in pts.
    sf : float
        Smooth window size in pts.
    sigma : float
        Standard-deviation of convoluted Gaussian window.

    Returns
    -------
    baseline : 1D ndarray
        Baseline calculated using median baseline correction

    """
    # create extrema array (non extrema values are masked out)
    mask = x == scipy.ndimage.median_filter(x, size=3)
    mask[0] = False     # first pt always extrema
    mask[-1] = False    # last pt always extrema
    e = np.ma.masked_array(x, mask)

    # fill in the median vector
    m = scipy.ndimage.median_filter(e, mw + 1, mode="mirror")
    # using the median_filter might give slightly different results than
    # described algorithm but is MUCH faster

    # convolve with a gaussian
    g = scipy.signal.windows.gaussian(sf, sigma)
    g = g / g.sum()
    return scipy.signal.convolve(m, g, mode='same')


# Distribution based classification method for calculation of baseline
# in 1D spectra
def baseline_corrector(data, wd=20):
    """
    Subtract a distribution-classified baseline from a real 1D spectrum.

    Based on the main routine in Wang et al., Anal. Chem. 2013, 85,
    1231-1239, DOI: 10.1021/ac303233c, Supporting Information S5-S7.

    Parameters
    ----------
    data : 1D ndarray
        One dimensional NMR data with real values
    wd : int
        Positive half-width of the centered standard-deviation window in points.
        Windows contain up to ``2 * wd + 1`` available samples.

    Returns
    -------
    data : 1D ndarray
        Baseline corrected spectrum  calculated using distribution based
        classification

    Raises
    ------
    ValueError
        If the input is not a nonempty finite unmasked real vector, wd is not
        a positive integer, or every sample is classified as signal.

    Notes
    -----
    Uses centered clipped standard-deviation windows, local interpolation
    across signal segments and a centered clipped mean filter. The published
    pseudocode averages segment endpoints but writes the interpolation formula
    with the original intensities; here the averaged endpoints define the line.
    Historical NumPy population standard deviations and the noise-rejection
    helper are retained. The diffusion-edited extension and resampling described
    in the paper are not implemented.

    Broad low-contrast signals may be classified as baseline and removed.
    Check the estimated baseline (input minus output) and peak areas before
    quantitative use; this is not a universal automatic baseline estimator.

    """
    if np.ma.isMaskedArray(data):
        raise ValueError("data must be a nonempty finite real one-dimensional array without a mask")
    data = np.asarray(data)
    if (data.ndim != 1 or data.size == 0 or np.iscomplexobj(data)
            or data.dtype.kind not in "buif" or not np.isfinite(data).all()):
        raise ValueError("data must be a nonempty finite real one-dimensional array")
    if isinstance(wd, (bool, np.bool_)) or not isinstance(wd, (int, np.integer)) or wd < 1:
        raise ValueError("wd must be a positive integer half-width")
    data = data.astype(np.float64, copy=False)
    sd_set = _get_sd(data, wd)
    sigma = _find_noise_sd(sd_set, 0.999)
    sn_vector = _is_signal(sigma, sd_set, 3)
    if np.all(sn_vector):
        raise ValueError("classification provides no noise-only support for baseline estimation")
    s_start = _get_signal_start(sn_vector)
    s_end = np.sort(len(data) - 1 - _get_signal_start(sn_vector[::-1]))
    r = _get_temp_baseline(data, s_start, s_end, 7)
    baseline = _smooth(r, 60)
    return data - baseline


def _rolling_window(a, window):
    shape = a.shape[:-1] + (a.shape[-1] - window + 1, window)
    strides = a.strides + (a.strides[-1],)
    return np.lib.stride_tricks.as_strided(a, shape=shape, strides=strides)


def _get_sd(data, k):
    size = len(data)
    radius = min(k, size - 1)
    result = np.empty(size, dtype=float)
    width = 2 * radius + 1
    if width <= size:
        windows = np.lib.stride_tricks.sliding_window_view(data, width)
        result[radius:size-radius] = np.std(windows, axis=-1)
        edges = list(range(radius)) + list(range(size-radius, size))
    else:
        edges = range(size)
    for i in edges:
        result[i] = np.std(data[max(0, i-radius):min(size, i+radius+1)])
    return result


def _find_noise_sd(sd_set, ratio):
    '''Recompute the median after each rejection of estimates above twice it.

    Positive estimates are retained as in the historical filter. Stop when
    the ratio of consecutive medians reaches ratio; a zero median gives zero.
    '''
    sd_set = np.asarray(sd_set, dtype=float)
    if (sd_set.ndim != 1 or sd_set.size == 0
            or not np.isfinite(sd_set).all() or np.any(sd_set < 0)):
        raise ValueError("noise estimates must be a nonempty finite nonnegative vector")
    if not np.isfinite(ratio) or not 0 < ratio <= 1:
        raise ValueError("ratio must be finite and in (0, 1]")

    def median(values):
        low, high = (values.size - 1) // 2, values.size // 2
        ordered = np.partition(values, (low, high))
        a, b = ordered[low], ordered[high]
        if b > np.finfo(float).max / 2:
            return a / 2 + b / 2
        return (a + b) / 2

    m1 = median(sd_set)
    if m1 == 0:
        return m1
    while True:
        sd_set = sd_set[(sd_set > 0) & (sd_set - m1 <= m1)]
        m2 = median(sd_set)
        if m2 / m1 >= ratio:
            return m2
        m1 = m2


def _is_signal(sigma, sd_set, w):
    sn_vector = sd_set * 0
    for i in np.arange(len(sn_vector)):
        if sd_set[i] > sigma * 1.1:
            sn_vector[np.maximum(0, i-w):np.minimum(i + w + 1, len(sn_vector))] = 1
    return sn_vector


def _get_signal_start(sn_vector):
    s_start = []
    for k, v in groupby(enumerate(sn_vector), key=itemgetter(1)):
        if k:
            v = list(v)
            s_start.append(v[0][0])
    return np.array(s_start, dtype=np.intp)


def _get_temp_baseline(data, s_start, s_end, w):
    result = np.array(data, dtype=float, copy=True)
    size = len(data)
    for start, end in zip(s_start, s_end):
        left = np.mean(data[max(0, start-w):min(size, start+w+1)])
        right = np.mean(data[max(0, end-w):min(size, end+w+1)])
        result[start:end+1] = np.linspace(left, right, end-start+1)
    return result


def _smooth(r, w):
    radius = min(w, len(r) - 1)
    weights = np.full(2 * radius + 1, 1. / (2 * radius + 1))
    numerator = scipy.signal.convolve(r, weights, mode='same')
    denominator = scipy.signal.convolve(np.ones(len(r)), weights, mode='same')
    return numerator / denominator


# Solvent Filter
def sol_general(data, filter, w=16, mode='same'):
    """
    Solvent filter with generic filter.

    Algorithm described in: Marion et al. JMR 1989 84 425-430

    Parameters
    ----------
    data : 1D or 2D ndarray
        Array of 1D or 2D NMR data.
    filter : ndarray
        Filter to convolve with data.  Not used in solvent filter functions
        which specific the filter, e.g. sol_boxcar.
    w : int, optional
        Filter length.  Not used here but is used in solent filter functions
        which specify the filter, e.g. sol_boxcar.
    mode : {'valid', 'same', 'full'}, optional
        Convolution mode, 'same' should be used.

    Returns
    -------
    ndata : 1D or 2D ndarray
        NMR data with solvent filter applied

    """
    A = filter.sum()
    if data.ndim == 2:
        filter = np.atleast_2d(filter)
    return data - scipy.signal.convolve(data, filter, mode=mode) / A


def sol_boxcar(data, w=16, mode='same'):
    """
    Solvent filter with boxcar filter.  See :py:func:`sol_general`.
    """
    filter = scipy.signal.windows.boxcar(w)
    return sol_general(data, filter, w=w, mode=mode)


def sol_sine(data, w=16, mode='same'):
    """
    Solvent filter with sine-bell filter. See :py:func:`sol_general`.
    """
    filter = np.cos(np.pi * np.linspace(-0.5, 0.5, w))
    return sol_general(data, filter, w=w, mode=mode)


def sol_sine2(data, w=16, mode='same'):
    """
    Solvent filter with square sine-bell filter. See :py:func:`sol_general`.
    """
    filter = np.cos(np.pi * np.linspace(-0.5, 0.5, w)) ** 2
    return sol_general(data, filter, w=w, mode=mode)


def sol_gaussian(data, w=16, mode='same'):
    """
    Solvent filter with square gaussian filter. See :py:func:`sol_general`.
    """
    filter = scipy.signal.windows.gaussian(w, w / 2.)
    return sol_general(data, filter, w=w, mode=mode)


# Polynomial Solvent Subtraction
def poly_td(data):
    """
    Polynomial time domain solvent subtraction - Not Implemented
    """
    # From NMRPipe paper(appendix):
    #
    # when used with the argument -time, fits all data points to a polynomial,
    # which is then subtracted from the original data.  It is intended to fit
    # and subtract low-freqency solvent signal in the FID, a procedure that
    # often causes less distortions than time-domain convolution methods.
    # By default, a fourth-order polynomials is used.  For speed successive
    # averages of regions are usually fit, rather than fitting all of the data.
    #
    # Algorithm
    #
    # 1. Calculate average of blocks
    # 2. Fit these averages to polynomial (block parameters)
    # 3. Back out "real" polynomial parameters from these block parameters
    # 4. Subtract off the polynomial from data
    raise NotImplementedError


def poly_fd(data):
    """
    Polynomial frequency domain baseline correction - Not Implemented
    """
    # From NMRPipe paper (appendix):
    #
    # applies a polynomial baseline correction of the order specified by
    # argument -ord via an automated base-line detection method when used
    # with argument -auto.  The default is a forth-order polynomial. The
    # automated base-line mode works as follows: a copy of a given vector is
    # divided into a series of adjacent sections, typically eight points wide.
    # The average value of each section is subtracted from all points in that
    # section, to generate a 'centered' vector.  The intensities of the entire
    # centered vector are sorted, and the standard deviation of the noise is
    # estimated under the assumption that a given fraction (typically about
    # 30%) of the smallest intensities belong to the base-line, and that the
    # noise is normally distributed.  This noise estimate is multiplied by a
    # constant, typically about 1.5, to yield a classification threshold.
    # Then, each section in the centered vector is classified as base line only
    # if its standard deviation does not exceed the threshold.  These
    # classifications are used to correct the original vector.
    #
    # Algorithm
    #
    # 1. Divide into 'blocks'
    # 2. Center each block and create centered vector
    # 3. Calculate intensity (abs) of each centered vector
    # 4. Sort intensities, lower 30% belong to baseline
    # 5. Fit base line intensities to Normal distribution, gives estimation
    #    of standard deviation (std) of noise
    # 6. Classification threshold set to 1.5*std
    # 7. Qualify each block in centered vector as baseline only
    #    (its std < thres) or not (std > thres)
    # 8. Fit baseline only points to polynomial and subtract off
    raise NotImplementedError
