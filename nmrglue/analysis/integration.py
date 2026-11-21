import numpy as np


def _index_limits(unit_conv, bounds, unit, size):
    low, high = sorted((unit_conv(bounds[0], unit), unit_conv(bounds[1], unit)))
    return max(0, min(size, low)), max(0, min(size, high))


def integrate(data, unit_conv, limits, unit='ppm', noise_limits=None,
              norm_to_range=None, calibrate=1.0):
    r"""
    Integrate one 1D data array within limits given in units. Data points must
    be equally spaced.

    Functional form of integration is:

    .. math::
        value = \sum_a^b s(x_{i}) dx

    Where:
    s is the signal, a and b are the limits of integration and dx is the width
    of each bin.

    The integration error due to baseline noise is calculated as:

    .. math::
        error = \sigma_{vol} = \sigma \sqrt{n} dx

    if the noise_limits are set.

    Where:

    .. math::
        n = N_{\mathrm{selected}}

    sigma is the standard deviation of the baseline noise. n is the number
    of bins in the integration range. The bin width dx is in ppm, so the error
    has the same units as the integral.

    Parameters
    ----------
    data: array like
        1d array of intensity
    unit_conv: `fileiobase.unit_conversion` object
        unit_conversion object associated with data
    limits: array like
        With shape (2,) or (P, 2). Array with lower and upper integration
        limit. Or array with P rows of lower and upper integration limits.
        Converted index windows are half-open and clipped to available data.
    noise_limits: Optional[array like]
        With shape(2, ). Array with lower and upper limits to section of data
        with only noise. A larger range will likely yield a more accurate
        estimate. It is unwise to use the very end of the spectrum for the
        noise range.
    norm_to_range: Optional[int]
        If given, all values are normalized to the value determined within the
        range given by limits[norm_to_range, :]. The reference integral must
        be nonzero.
    calibrate: Optional[float]
        If norm_to_range is given, the values are re-normalized so that the
        integral within limits[norm_to_range, :] equals some number. The
        uncertainty scales with the magnitude of the normalization factor.

    Returns
    -------
    array
        [value, ...] integration values

    if noise_limits is given:

    array
        [[value, error], ...] where error a one sigma estimate of the error
        only from the spectrum noise

    """
    # convert form limits in units to lower and upper index
    limits = np.array(limits)
    if limits.size == 2:
        limits = np.expand_dims(limits, axis=0)
    inds = np.array([_index_limits(unit_conv, bounds, unit, len(data)) for bounds in limits])

    # sum part of the integral
    sum_slice = np.array([np.sum(data[slice(*ind)]) for ind in inds])

    # dx part of the integral
    scale = unit_conv.ppm_scale()
    dx = abs(scale[1]-scale[0])

    # put together the integral
    values = sum_slice * dx
    reference = None
    if norm_to_range is not None:
        reference = values[norm_to_range]
        if reference == 0:
            raise ValueError("normalization integral is zero")
        values = (values / reference) * calibrate

    if noise_limits is not None:

        # determine the standard deviation of the noise
        noise_inds = _index_limits(unit_conv, noise_limits, unit, len(data))
        if noise_inds[0] == noise_inds[1]:
            raise ValueError("noise window is empty after clipping to the data")

        # the error (from noise) is  std * dx * limits range
        std = np.std(data[slice(*noise_inds)])
        errors = std * np.sqrt(inds[:, 1] - inds[:, 0]) * dx

        if reference is not None:
            errors = np.abs((errors / reference) * calibrate)
        return np.vstack((values, errors)).T

    return values


def ndintegrate(data, unit_conv, limits, unit='ppm', noise_limits=None):
    r"""
    Integrate one nD data array within limits given in units. Data points must
    be equally spaced. Can only integrate one region per function call.

    The integration error due to baseline noise is calculated as:

    .. math::
        error = \sigma_{vol} = \sigma \sqrt{\prod_i^{d} n_{i}}
        \prod_i^{d} dx_i,

    if the noise_limits are set.

    Where:
    sigma is the standard deviation of the baseline noise. n is the number
    of bins in the integration range for each d dimensions. dx_i is the bin
    width in ppm along dimension i, so the error has the same units as the
    integrated volume.

    See integrate for more information.

    Parameters
    ----------
    data: array like
        1d array of intensity
    unit_convs: [`fileiobase.unit_conversion`, ] list
        list of unit_conversion object associated with each dim of data.
    limits: array like
        With shape (2,) or (d, 2). 1D Array with lower and upper integration
        limits for 1D . Or array with d rows of lower and upper integration
        limits for each dimension.
        Converted index windows are half-open and clipped to available data.
    noise_limits: Optional[array like]
        With shape(2, ). Array with lower and upper limits to section of data
        with only noise. A larger range will likely yield a more accurate
        estimate. It is unwise to use the very end of the spectrum for the
        noise range.

    Returns
    -------
    array
        [value, ...] integration values

    if noise_limits is given:

    array
        [[value, error], ...] where error a one sigma estimate of the error
        only from the spectrum noise
    """

    # determine the dimensionality of the data.
    d = np.ndim(data)

    try:
        iter(unit_conv)
    except TypeError:
        unit_conv = [unit_conv, ]

    if d != len(unit_conv):
        mesg = 'A unit_conversion object is needed for each dimension.'
        raise ValueError(mesg)

    limits = np.array(limits)
    if limits.ndim == 1:
        limits = np.expand_dims(limits, axis=0)

    if limits.ndim != 2 or limits.shape != (d, 2):
        mesg = 'A lower and upper limit is needed for each dimension.'
        raise ValueError(mesg)

    inds = [_index_limits(uc, bounds, unit, size)
            for uc, bounds, size in zip(unit_conv, limits, data.shape[::-1])]

    # the integrate_nd needs to be scaled by the bin width in ppm
    ppm_scales = [x.ppm_scale() for x in unit_conv]
    dx = np.prod(np.array([abs(x[1]-x[0]) for x in ppm_scales]))

    signal = data[tuple(slice(*ind) for ind in np.flipud(inds))]
    slice_sum = signal.sum()

    value = slice_sum * dx

    if noise_limits is None:
        return value

    else:
        noise_limits = np.array(noise_limits)
        if noise_limits.ndim == 1:
            noise_limits = np.expand_dims(noise_limits, axis=0)

        if noise_limits.ndim != 2 or noise_limits.shape != (d, 2):
            mesg = 'If given, a noise limit is needed for each dimension.'
            raise ValueError(mesg)

        noise_inds = [_index_limits(uc, bounds, unit, size)
                      for uc, bounds, size in zip(unit_conv, noise_limits, data.shape[::-1])]

        # see docstring of integrate
        nm = signal.size
        noise_slices = tuple(slice(*ind) for ind in np.flipud(noise_inds))
        noise_region = data[noise_slices]
        if noise_region.size == 0:
            raise ValueError("noise window is empty after clipping to the data")
        std = np.std(noise_region)

        error = std * np.sqrt(nm) * dx
        return np.hstack((value, error))
