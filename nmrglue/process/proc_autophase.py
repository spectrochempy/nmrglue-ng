"""
Automated phase correction
These functions provide support for automatic phasing of NMR data. They
consist of the core `autops` function which performs the optimisation and
a set of private functions for calculating a spectral phase quality score
for a provided spectrum.
"""


from dataclasses import dataclass
from numbers import Integral

import numpy as np
import scipy.optimize
from scipy.signal import find_peaks

from .proc_base import ps


@dataclass(frozen=True)
class PhaseEstimate:
    """Estimated correction in degrees at index zero and fit diagnostics."""

    p0: float
    p1: float
    success: bool
    message: str
    score_before: float
    score_after: float
    nfev: int


def phase_slope_from_delay(spectral_width_hz, acquisition_delay_s, *, hard_90_pulse_s=0.):
    """Return the correction p1 for a delayed first complex sample.

    Assumes fftshift(fft(fid)) on an increasing frequency grid. The delay is
    measured from the end of the excitation pulse to the first complex sample.
    For a rectangular 90-degree pulse from longitudinal magnetization, the
    small-offset model adds 2/pi times the pulse duration
    (doi:10.1002/cmr.a.21250). If the delay already uses the effective
    excitation origin, leave hard_90_pulse_s at zero. Digital filter correction
    is a separate operation.
    """
    values = np.asarray(
        [spectral_width_hz, acquisition_delay_s, hard_90_pulse_s], dtype=float,
    )
    if (values.shape != (3,) or not np.isfinite(values).all()
            or values[0] <= 0 or np.any(values[1:] < 0)):
        raise ValueError("expected a positive spectral width and nonnegative finite delays")
    width, delay, pulse = values
    slope = -360. * (width * (delay + (2. / np.pi) * pulse))
    if not np.isfinite(slope):
        raise ValueError("the phase slope must be finite")
    return float(slope)


def estimate_phase(
    data, *, method="acme", order=0, mask=None, initial=(0., 0.),
    references=(), baseline_mask=None, fixed_p1=None, maxiter=None,
):
    """Estimate a phase correction for a complex 1D frequency-domain spectrum.

    True entries in mask exclude points from the score. The phase uses the
    original sample indices divided by the original spectrum length, as in ps.
    The optional baseline_mask selects fixed signal-free points (True) for a
    provisional complex linear background subtracted before either fit.
    With order=0, fixed_p1 holds a supplied slope in degrees during the fit;
    otherwise the slope is zero. Use initial[1] with order=1 to fit the slope
    starting from an estimate.

    DISPA accepts references as (start, stop, sign) tuples with half-open sample
    windows around isolated lines and expected absorption sign +1 or -1.
    Use narrow, disjoint windows around well-separated, near-Lorentzian lines
    with locally zero complex background, or provide baseline anchors.
    Local phases are unwrapped relative to initial. Choose initial close enough
    that adjacent reference errors differ by less than 180 degrees. DISPA
    scores are RMS residuals to the fitted phase ramp in degrees, whereas ACME scores are
    dimensionless. First-order fitting requires distinct peaks spanning at
    least 5% of the grid. ACME searches within 360 degrees of the initial slope.
    The optional maxiter limits iterations per ACME start (default 500).
    Solver success alone does not establish phase accuracy.
    """
    input_mask = np.ma.getmaskarray(data) if np.ma.isMaskedArray(data) else False
    data = np.asarray(data)
    if data.ndim != 1 or data.size < 3 or not np.iscomplexobj(data):
        raise ValueError("expected a complex 1D spectrum with at least three points")
    if not isinstance(order, Integral) or order not in (0, 1):
        raise ValueError("order must be 0 or 1")
    if maxiter is not None:
        if method != "acme":
            raise ValueError("maxiter is only supported for ACME")
        if not isinstance(maxiter, Integral) or maxiter < 1:
            raise ValueError("maxiter must be a positive integer")
    else:
        maxiter = 500
    initial = np.asarray(initial, dtype=float)
    if initial.shape != (2,) or not np.isfinite(initial).all():
        raise ValueError("initial must contain two finite angles")
    p0, p1 = initial
    if fixed_p1 is not None:
        if order != 0:
            raise ValueError("fixed_p1 requires order=0")
        fixed_p1 = float(fixed_p1)
        if not np.isfinite(fixed_p1):
            raise ValueError("fixed_p1 must be finite")
    if order == 0:
        p1 = 0. if fixed_p1 is None else fixed_p1
    valid = ~(_phase_selection(mask, data.shape) | input_mask)
    if np.count_nonzero(valid) < 3 or not np.isfinite(data[valid]).all():
        raise ValueError("at least three valid finite complex samples are required")
    indices = np.flatnonzero(valid)
    x = indices / data.size
    z = data[valid]
    scale = max(np.max(np.abs(z.real)), np.max(np.abs(z.imag)))
    if scale == 0:
        raise ValueError("spectrum has no signal")
    z = (z.real / scale).astype(float) + 1j * (z.imag / scale).astype(float)
    if baseline_mask is not None:
        anchors = _phase_selection(baseline_mask, data.shape)[valid]
        if np.count_nonzero(anchors) < 2:
            raise ValueError("linear baseline requires two valid anchor samples")
        design = np.column_stack((np.ones(x.size), x - x[anchors].mean()))
        coefficients, _, _, _ = np.linalg.lstsq(design[anchors], z[anchors], rcond=None)
        z = z - design @ coefficients
        residual_scale = max(np.max(np.abs(z.real)), np.max(np.abs(z.imag)))
        if residual_scale <= 1e-14:
            raise ValueError("no signal remains after provisional background removal")
        z /= residual_scale

    if method == "dispa":
        return _estimate_dispa(x, z, indices, data.size, references, order, p0, p1)
    if method != "acme":
        raise ValueError("method must be 'acme' or 'dispa'")
    if len(references):
        raise ValueError("references are only supported for DISPA")
    adjacent = np.diff(indices) == 1
    if not np.any(adjacent) or not np.any(np.abs(np.diff(z)[adjacent]) > 1e-14):
        raise ValueError("ACME requires variation between valid adjacent samples")

    if order:
        magnitude = np.abs(z)
        threshold = 0.05 * np.max(magnitude)
        breaks = np.r_[0, np.flatnonzero(~adjacent) + 1, indices.size]
        peaks = []
        for start, stop in zip(breaks[:-1], breaks[1:]):
            local, _ = find_peaks(magnitude[start:stop], prominence=threshold)
            peaks.extend(indices[start + local])
        if len(peaks) < 2 or (peaks[-1] - peaks[0]) / data.size < 0.05:
            raise ValueError("first-order phase requires two well-separated peaks")

    def score(angles):
        slope = angles[1] if order else p1
        real = (z * np.exp(1j * np.deg2rad(angles[0] + slope * x))).real
        derivative = np.abs(np.diff(real)[adjacent])
        total = derivative.sum()
        if total <= np.finfo(float).eps * max(1., np.abs(real).sum()):
            return np.inf
        probability = derivative[derivative > 0] / total
        negative = np.minimum(real, 0.)
        return -np.dot(probability, np.log(probability)) + 1000 * np.dot(negative, negative)

    start = np.array([p0, p1] if order else [p0])
    before = score(start)
    steps = np.diag([12., 24.] if order else [12.])
    bounds = [(None, None), (p1 - 360., p1 + 360.)] if order else None
    candidates = []
    for offset in (0., 90., 180., 270.):
        seed = start.copy()
        seed[0] += offset
        if not np.isfinite(score(seed)):
            continue
        candidates.append(scipy.optimize.minimize(
            score, seed, method="Nelder-Mead", bounds=bounds,
            options={"initial_simplex": np.vstack((seed, seed + steps)),
                     "maxiter": maxiter, "xatol": 1e-6, "fatol": 1e-8},
        ))
    if not candidates:
        raise ValueError("ACME found no usable variation after background removal")
    best = min(candidates, key=lambda fit: fit.fun)
    correction = _wrap_degrees(best.x[0])
    slope = float(best.x[1]) if order else p1
    at_bound = order and abs(slope - p1) >= 360. - 1e-5
    message = "First-order phase reached the search bound" if at_bound else str(best.message)
    return PhaseEstimate(
        correction, slope, bool(best.success and not at_bound),
        message, float(before), float(best.fun),
        sum(fit.nfev for fit in candidates),
    )


def _phase_selection(mask, shape):
    if mask is None:
        return np.zeros(shape, dtype=bool)
    selection = np.asarray(mask)
    if selection.shape != shape or selection.dtype != bool:
        raise ValueError("phase and baseline masks must be boolean arrays matching data")
    return selection


def _wrap_degrees(angle):
    return float((angle + 180.) % 360. - 180.)


def _estimate_dispa(x, z, indices, size, references, order, p0, p1):
    """Fit local DISPA circles and a phase ramp (doi:10.1016/0022-2364(88)90350-2)."""
    centers, corrections = [], []
    for start, stop, sign in references:
        if (not isinstance(start, Integral) or not isinstance(stop, Integral)
                or not 0 <= start < stop <= size or sign not in (-1, 1)):
            raise ValueError("invalid DISPA reference window or sign")
        keep = (indices >= start) & (indices < stop)
        line = z[keep]
        if line.size < 5:
            raise ValueError("each DISPA window needs five valid samples")
        line = line * np.exp(1j * np.deg2rad(p0 + p1 * x[keep]))
        apex = np.argmax(np.abs(line))
        if apex < 2 or apex > line.size - 3:
            raise ValueError("a DISPA reference needs valid samples on both flanks")
        xy = np.column_stack((line.real, line.imag))
        mean = xy.mean(axis=0)
        centered = xy - mean
        fit, _, rank, _ = np.linalg.lstsq(
            2 * centered, np.sum(centered**2, axis=1), rcond=None,
        )
        center = mean + fit
        if rank < 2 or np.linalg.norm(center) <= np.finfo(float).eps:
            raise ValueError("DISPA reference does not define a usable circle")
        centers.append(x[keep][apex])
        corrections.append(-np.angle(sign * complex(*center), deg=True))
    if len(set(centers)) < order + 1:
        raise ValueError("DISPA needs distinct reference peaks for the requested order")
    if order and np.ptp(centers) < 0.05:
        raise ValueError("first-order phase requires two well-separated peaks")
    sequence = np.argsort(centers)
    centers = np.asarray(centers)[sequence]
    corrections = np.rad2deg(np.unwrap(np.deg2rad(np.asarray(corrections)[sequence])))
    if order:
        ramp = scipy.optimize.least_squares(
            lambda angles: angles[0] + angles[1] * centers - corrections,
            x0=[0., 0.], loss="soft_l1", f_scale=5.,
        )
        offset, slope = ramp.x
        residual = ramp.fun
        success, message, nfev = ramp.success, ramp.message, ramp.nfev
    else:
        offset, slope = np.median(corrections), 0.
        residual = offset - corrections
        success, message, nfev = True, "Local phases estimated", 0
    return PhaseEstimate(
        _wrap_degrees(p0 + offset), float(p1 + slope), bool(success), str(message),
        float(np.sqrt(np.mean(corrections**2))),
        float(np.sqrt(np.mean(residual**2))), nfev,
    )


def autops(data, fn, p0=0.0, p1=0.0, return_phases=False, peak_width=100, **kwargs):
    """
    Automatic linear phase correction

    Parameters
    ----------
    data : ndarray
        Array of NMR data.
    fn : str or function
        Algorithm to use for phase scoring. Built in functions can be
        specified by one of the following strings: "acme", "peak_minima"
    p0 : float
        Initial zero order phase in degrees.
    p1 : float
        Initial first order phase in degrees.
    peak_width : int
        Positive window width for peak_minima optimization. Windows are
        truncated at the spectrum boundaries. This algorithm needs a 1D
        spectrum with at least three points and an initial maximum away
        from the endpoints.
    return_phases : Bool
        returns a list of optimized values of phases [p0, p1] in addition
        to the phased data
    kwargs : additional key-word arguments to be passed to the solver
        The are documented at the following link:
        https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.fmin.html
        Some of the more useful ones for this use case:

        * disp : Bool
            Turns on or off the printing of convergence messages
            By default, this is set to True.
        * ftol : float
            Absolute error in fn between iterations that is acceptable for
            convergence. The default is 1e-4.

    Returns
    -------
    ndata : ndarray
        Phased NMR data.

    """
    arguments = [data,]

    if not callable(fn):
        if fn == 'peak_minima':
            if peak_width < 1:
                raise ValueError("peak_width must be positive")
            if np.ndim(data) != 1 or len(data) < 3:
                raise ValueError(
                    "peak_minima requires a 1D spectrum with at least three points"
                )
            arguments.append(peak_width)
            initial_peak = np.argmax(ps(data, p0=p0, p1=p1).real)
            if initial_peak in (0, data.size - 1):
                raise ValueError("peak_minima initial peak is at a spectrum endpoint")

        try:
            fn = {
                'peak_minima': _ps_peak_minima_score,
                'acme': _ps_acme_score,
            }[fn]
        except KeyError:
            raise KeyError(f'Unable to find algorithm "{fn}". Use "acme", "peak_minima" or pass a custom function.')

    opt = [p0, p1]

    opt = scipy.optimize.fmin(fn, x0=opt, args=tuple(arguments), **kwargs)

    phasedspc = ps(data, p0=opt[0], p1=opt[1])

    if return_phases:
        return phasedspc, opt
    else:
        return phasedspc


def _ps_acme_score(ph, data):
    """
    Phase correction using ACME algorithm by Chen Li et al.
    Journal of Magnetic Resonance 158 (2002) 164-168

    Parameters
    ----------
    ph : tuple
        Current p0 and p1 values
    data : ndarray
        Array of NMR data.

    Returns
    -------
    score : float
        Value of the objective function (phase score)

    """
    stepsize = 1

    phc0, phc1 = ph

    s0 = ps(data, p0=phc0, p1=phc1)
    data = np.real(s0)

    # Calculation of first derivatives
    ds1 = np.abs((data[1:]-data[:-1]) / (stepsize*2))
    p1 = ds1 / np.sum(ds1)

    # Calculation of entropy
    p1[p1 == 0] = 1

    h1 = -p1 * np.log(p1)
    h1s = np.sum(h1)

    # Calculation of penalty
    pfun = 0.0
    as_ = data - np.abs(data)
    sumas = np.sum(as_)

    if sumas < 0:
        pfun = pfun + np.sum((as_/2) ** 2)

    p = 1000 * pfun

    return (h1s + p) / data.shape[-1] / np.max(data)


def _ps_peak_minima_score(ph, data, peak_width):
    """
    Phase correction using simple minima-minimisation around highest peak

    This is a naive approach but is quick and often achieves reasonable
    results.  The optimisation is performed by finding the highest peak in the
    spectra (e.g. TMSP) and then attempting to reduce minima surrounding it.

    Parameters
    ----------
    ph : tuple
        Current p0 and p1 values
    peak_width : int
        Lookup width
    data : ndarray
        Array of NMR data.

    Returns
    -------
    score : float
        Value of the objective function (phase score)

    """

    phc0, phc1 = ph

    s0 = ps(data, p0=phc0, p1=phc1)
    data = np.real(s0)

    i = np.argmax(data)
    if i == 0 or i == data.size - 1:
        return np.inf
    mina = np.min(data[max(0, i - peak_width):i])
    minb = np.min(data[i:i + peak_width])

    return np.abs(mina - minb)


def manual_ps(data, notebook=False):
    """
    Manual Phase correction using matplotlib

    A matplotlib widget is used to manually correct the phase of a Fourier
    transformed dataset. If the dataset has more than 1 dimensions, the first
    trace will be picked up for phase correction.  Clicking the 'Set Phase'
    button will print the current linear phase parameters to the console.
    A ipywidget is provided for use with Jupyter Notebook to avoid changing
    backends. This can be accessed with notebook=True option in this function

    .. note:: Needs matplotlib with an interactive backend.

    Parameters
    ----------
    data : ndarray
        Array of NMR data.
    notebook : Bool
        True for plotting interactively in Jupyter Notebook
        Uses ipywidgets instead of matplotlib widgets

    Returns
    -------
    p0, p1 : float
        Linear phase correction parameters. Zero and first order phase
        corrections in degrees calculated from pc0, pc1 and pivot displayed
        in the interactive window.

    Examples
    --------
    >>> import nmrglue as ng
    >>> p0, p1 = ng.process.proc_autophase.manual_ps(data)
    >>> # do manual phase correction and close window
    >>> phased_data = ng.proc_base.ps(data, p0=p0, p1=p1)

    If you are using a Jupyter Notebook::

        In  [1] ng.process.proc_autophase.manual_ps(data)
        Out [1] # do manual phase correction. p0 and p1 values will be updated
                # continuously as you do so and are printed below the plot
        In  [2] phased_data = ng.proc_base.ps(data, p0=p0, p1=p1)

    """

    if len(data.shape) == 2:
        data = data[0, ...]
    elif len(data.shape) == 3:
        data = data[0, 0, ...]
    elif len(data.shape) == 4:
        data = data[0, 0, 0, ...]

    if notebook:
        from ipywidgets import interact, fixed
        import matplotlib.pyplot as plt

        def phasecorr(dataset, phcorr0, phcorr1, pivot):
            fig, ax = plt.subplots(figsize=(10, 7))
            phaseddata = dataset * np.exp(
                1j * (phcorr0 + phcorr1 * (
                    np.arange(-pivot, -pivot+dataset.size)/dataset.size)))

            ax.plot(np.real(phaseddata))
            ax.set(ylim=(np.min(np.real(data))*2, np.max(np.real(data))*2))
            ax.axvline(pivot, color='r', alpha=0.5)
            plt.show()

            p0 = np.round(
                (phcorr0 - phcorr1 * pivot/dataset.size) * 360 / 2 / np.pi, 3)
            p1 = np.round(phcorr1*360/2/np.pi, 3)

            print('p0 =', p0, 'p1 =', p1)

        interact(
            phasecorr,
            dataset=fixed(data),
            phcorr0=(-np.pi, np.pi, 0.01),
            phcorr1=(-10*np.pi, 10*np.pi, 0.01),
            pivot=(0, data.size, 1))

    else:

        from matplotlib.widgets import Slider, Button
        import matplotlib.pyplot as plt

        plt.subplots_adjust(left=0.25, bottom=0.35)

        interactive, = plt.plot(data.real, lw=1, color='black')

        axcolor = 'white'
        axpc0 = plt.axes([0.25, 0.10, 0.65, 0.03], facecolor=axcolor)
        axpc1 = plt.axes([0.25, 0.15, 0.65, 0.03], facecolor=axcolor)
        axpiv = plt.axes([0.25, 0.20, 0.65, 0.03], facecolor=axcolor)
        axpst = plt.axes([0.25, 0.25, 0.15, 0.04], facecolor=axcolor)

        spc0 = Slider(axpc0, 'p0', -360, 360, valinit=0)
        spc1 = Slider(axpc1, 'p1', -360, 360, valinit=0)
        spiv = Slider(axpiv, 'pivot', 0, data.size, valinit=0)
        axps = Button(axpst, 'Set Phase', color=axcolor)

        def update(val):
            pc0 = spc0.val * np.pi / 180
            pc1 = spc1.val * np.pi / 180
            pivot = spiv.val
            interactive.set_ydata((data * np.exp(
                1.0j * (pc0 + (pc1 * np.arange(-pivot, -pivot + data.size) /
                        data.size))).astype(data.dtype)).real)
            plt.draw()

        def setphase(val):
            p0 = spc0.val-spc1.val*spiv.val/data.size
            p1 = spc1.val
            print(p0, p1)

        spc0.on_changed(update)
        spc1.on_changed(update)
        spiv.on_changed(update)
        axps.on_clicked(setphase)

        plt.show(block=True)

        p0 = spc0.val-spc1.val*spiv.val/data.size
        p1 = spc1.val
        return p0, p1
