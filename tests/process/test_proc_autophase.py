import numpy as np
import pytest

from nmrglue.process.proc_autophase import autops, estimate_phase


@pytest.mark.parametrize("size, center", [(256, 128), (256, 20), (256, 235), (11, 3)])
def test_peak_minima_handles_truncated_windows(size, center):
    x = np.arange(size) - center
    data = (1 / (1 + (x / 3) ** 2)).astype(complex)

    result, phases = autops(data, "peak_minima", disp=False, return_phases=True)

    assert result.shape == data.shape
    assert np.isfinite(result).all()
    assert np.isfinite(phases).all()


@pytest.mark.parametrize("center", [0, 10])
def test_peak_minima_rejects_endpoint_at_initial_phase(center):
    x = np.arange(11) - center
    data = (1 / (1 + (x / 3) ** 2)).astype(complex)

    with pytest.raises(ValueError, match="initial peak.*endpoint"):
        autops(data, "peak_minima", peak_width=3, disp=False)


def test_peak_minima_requires_positive_width():
    with pytest.raises(ValueError, match="peak_width must be positive"):
        autops(np.array([0, 1, 0], dtype=complex), "peak_minima", peak_width=0)


def test_peak_minima_does_not_mistake_overflow_for_endpoint():
    data = np.array([-9.13e307, 9.13e307, 0], dtype=complex)

    with np.errstate(over="ignore", invalid="ignore"):
        result = autops(data, "peak_minima", p0=10, peak_width=1, maxiter=1,
                        disp=False)

    assert np.isfinite(result).all()


@pytest.fixture
def synthetic_spectrum():
    # Known absorption and dispersion; independent phase injection on the full grid.
    j = np.arange(4096)
    first = 1 / (1 + 1j * (j - 900) / 8)
    second = 0.65 / (1 + 1j * (j - 3000) / 12)
    rng = np.random.default_rng(935)
    noise = 0.001 * (rng.normal(size=j.size) + 1j * rng.normal(size=j.size))
    rotation = np.exp(1j * np.deg2rad(45 - 110 * j / j.size))
    return j, first, second, noise, rotation


def test_masked_acme_preserves_grid_and_intensity_scale(synthetic_spectrum):
    j, first, second, noise, rotation = synthetic_spectrum
    mask = (j > 1550) & (j < 2300)
    data = (first + second + noise) * rotation
    reference = estimate_phase(data, order=1, mask=mask)
    contaminated = data * 0.001
    contaminated[mask] = np.nan + 1j * np.nan
    result = estimate_phase(np.ma.array(contaminated, mask=mask), order=1)

    assert reference.success and result.success
    assert (result.p0, result.p1) == pytest.approx((reference.p0, reference.p1), abs=1e-4)
    local_phase = result.p0 + result.p1 * j[[900, 3000]] / j.size
    expected = -45 + 110 * j[[900, 3000]] / j.size
    np.testing.assert_allclose(local_phase, expected, atol=3)
    assert result.score_after < result.score_before


def test_acme_removes_fixed_complex_background_for_scoring(synthetic_spectrum):
    j, first, second, noise, rotation = synthetic_spectrum
    anchors = (j < 400) | (j > 3800)
    signal = (first + second + noise) * rotation
    signal[anchors] = 0
    drift = 0.12 + 0.25 * j / j.size + 1j * (0.04 - 0.1 * j / j.size)
    before = estimate_phase(signal, order=1, baseline_mask=anchors)
    after = estimate_phase(signal + drift, order=1, baseline_mask=anchors)

    assert before.success and after.success
    assert (after.p0, after.p1) == pytest.approx((before.p0, before.p1), abs=1e-4)


def test_dispa_recovers_signed_noisy_peak_phases(synthetic_spectrum):
    j, first, second, noise, rotation = synthetic_spectrum
    data = (first - second + noise) * rotation
    result = estimate_phase(
        data, method="dispa", order=1, references=[(880, 921, 1), (2975, 3026, -1)]
    )

    assert result.success
    assert result.p0 == pytest.approx(-45, abs=1.5)
    assert result.p1 == pytest.approx(110, abs=3)
    corrected = data * np.exp(1j * np.deg2rad(result.p0 + result.p1 * j / j.size))
    assert corrected.real[900] > 0.99
    assert corrected.real[3000] < -0.64
    assert max(abs(corrected.imag[[900, 3000]])) < 0.012


def test_estimate_rejects_zero_spectrum_and_unidentifiable_dispa_slope(synthetic_spectrum):
    _, first, _, _, rotation = synthetic_spectrum
    with pytest.raises(ValueError, match="no signal"):
        estimate_phase(np.zeros(12, dtype=complex))
    with pytest.raises(ValueError, match="distinct reference peaks"):
        estimate_phase(
            first * rotation, method="dispa", order=1, references=[(880, 921, 1)]
        )


def test_acme_rejects_first_order_on_one_narrow_unmasked_line():
    j = np.arange(4096)
    data = np.exp(1j * np.deg2rad(45)) / (1 + 1j * (j - 2048) / 8)
    mask = np.abs(j - 2048) > 30

    with pytest.raises(ValueError, match="well-separated peaks"):
        estimate_phase(data, order=1, mask=mask)
    result = estimate_phase(data, order=0)
    assert result.success
    assert result.p0 == pytest.approx(-45, abs=1)


def test_dispa_complex_background_uses_fixed_anchors():
    j = np.arange(1024)
    line = 1 / (1 + 1j * (j - 400) / 8)
    anchors = (j < 200) | (j > 700)
    line[anchors] = 0
    background = 0.03 + 0.5j
    result = estimate_phase(
        line + background, method="dispa", references=[(380, 421, 1)],
        baseline_mask=anchors,
    )
    assert result.p0 == pytest.approx(0, abs=1e-8)


@pytest.mark.parametrize("method", ["acme", "dispa"])
def test_fixed_slope_corrects_a_fractionally_delayed_fid(method):
    from nmrglue.process.proc_autophase import phase_slope_from_delay
    from nmrglue.process.proc_base import ps

    size = 4096
    width = 10_000.
    frequencies = np.array([-1800., 2400.])
    delay = 8e-6
    pulse = 10e-6
    effective = delay + 2 * pulse / np.pi
    time = np.arange(size) / width
    bins = np.rint((frequencies / width + 0.5) * size).astype(int)

    def spectrum_at(times):
        rates = -50 + 2j * np.pi * frequencies
        fid = np.exp(times[:, None] * rates) @ np.array([1., 0.7])
        return np.fft.fftshift(np.fft.fft(fid))

    reference = spectrum_at(time)
    data = spectrum_at(time + effective) * np.exp(1j * np.deg2rad(31))
    slope = phase_slope_from_delay(width, delay, hard_90_pulse_s=pulse)
    options = (
        {"references": [(bins[0] - 10, bins[0] + 11, 1)]}
        if method == "dispa" else {}
    )
    result = estimate_phase(data, method=method, fixed_p1=slope, **options)

    assert result.success
    assert slope == pytest.approx(-51.7183118, abs=1e-6)
    assert result.p1 == slope
    corrected = ps(data, result.p0, result.p1)
    relative_peak_phase = np.angle(corrected[bins] / reference[bins], deg=True)
    # The sampled lines retain a common phase bias from the shape score.
    # The differential error isolates the timing-derived slope.
    assert abs(relative_peak_phase[1] - relative_peak_phase[0]) < 0.2
    assert np.max(np.abs(relative_peak_phase)) < 3.
    with pytest.raises(ValueError, match="fixed_p1 requires order=0"):
        estimate_phase(data, order=1, fixed_p1=slope)
