"""Generate and validate the synthetic data used by Getting Started.

Run this script from any directory. It writes the NMRPipe time-domain file next
to the script, then processes it to validate the expected peak positions.
"""

from datetime import datetime
from hashlib import sha256
from pathlib import Path

import nmrglue as ng
import numpy as np


HERE = Path(__file__).resolve().parent
DATA_PATH = HERE / "synthetic_1d_time.fid"

POINTS = 2048
SPECTRAL_WIDTH_HZ = 6000.0
OBSERVATION_FREQUENCY_MHZ = 600.0
CARRIER_PPM = 4.7
RESONANCES = (
    # chemical shift / ppm, amplitude, linewidth / Hz
    (7.25, 1.00, 3.0),
    (3.55, 0.65, 5.0),
    (1.25, 0.85, 4.0),
)


def make_fid():
    """Return a reproducible complex FID containing three resonances."""
    time = np.arange(POINTS) / SPECTRAL_WIDTH_HZ
    fid = np.zeros(POINTS, dtype=np.complex128)
    for shift_ppm, amplitude, linewidth_hz in RESONANCES:
        offset_hz = (shift_ppm - CARRIER_PPM) * OBSERVATION_FREQUENCY_MHZ
        fid += amplitude * np.exp(-np.pi * linewidth_hz * time) * np.exp(
            2j * np.pi * offset_hz * time
        )

    rng = np.random.default_rng(20261012)
    noise = rng.normal(size=POINTS) + 1j * rng.normal(size=POINTS)
    return time, fid + 0.002 * noise


def write_nmrpipe(path, fid):
    """Write *fid* with a minimal, fixed NMRPipe header."""
    udic = ng.fileiobase.create_blank_udic(1)
    udic[0].update(
        size=POINTS,
        complex=True,
        sw=SPECTRAL_WIDTH_HZ,
        obs=OBSERVATION_FREQUENCY_MHZ,
        car=CARRIER_PPM * OBSERVATION_FREQUENCY_MHZ,
        label="1H",
        time=True,
        freq=False,
        encoding="direct",
    )
    header = ng.pipe.create_dic(udic, datetime(2026, 1, 1, 12, 0, 0))
    ng.pipe.write(str(path), header, fid.astype(np.complex64), overwrite=True)


def process(path):
    """Apply the same minimal processing shown in Getting Started."""
    header, fid = ng.pipe.read(str(path))
    udic = ng.pipe.guess_udic(header, fid)
    fid = ng.proc_base.zf_size(fid, size=8192)
    spectrum = ng.proc_base.fft_positive(fid)
    spectrum = ng.proc_base.di(spectrum)
    udic[0].update(
        size=spectrum.size,
        complex=False,
        time=False,
        freq=True,
    )
    ppm = ng.fileiobase.uc_from_udic(udic).ppm_scale()
    return header, fid, ppm, spectrum


def validate(ppm, spectrum):
    """Check that peak picking recovers every encoded resonance."""
    locations = ng.peakpick.pick(
        spectrum,
        pthres=0.10 * spectrum.max(),
        algorithm="downward",
        est_params=False,
        cluster=False,
        table=False,
    )
    indices = np.array([location[0] for location in locations])
    observed_ppm = np.sort(ppm[indices])
    expected_ppm = np.sort([resonance[0] for resonance in RESONANCES])
    np.testing.assert_allclose(observed_ppm, expected_ppm, atol=0.01)


def main():
    _, generated_fid = make_fid()
    write_nmrpipe(DATA_PATH, generated_fid)
    _, _, ppm, spectrum = process(DATA_PATH)
    validate(ppm, spectrum)
    checksum = sha256(DATA_PATH.read_bytes()).hexdigest()
    print(f"wrote {DATA_PATH.name} (sha256: {checksum})")


if __name__ == "__main__":
    main()
