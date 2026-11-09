""" Unit tests for nmrglue/fileio/bruker.py module """

import os
import shutil
import tempfile

import numpy as np
import nmrglue as ng
import pytest

# Test data.
DATA_DIR = os.path.join(
    os.path.dirname(__file__), '..', 'fixtures', 'fileio', 'bruker_test_data'
)
SYNTHETIC_PPROG = os.path.join(DATA_DIR, 'synthetic_pulseprogram')


def test_jcamp1(tmp_path):
    """Read and write known acquisition parameters from a packaged fixture."""
    source = os.path.join(DATA_DIR, '1', 'acqus')
    dic = ng.bruker.read_jcamp(source)

    assert dic['LFILTER'] == 200
    assert dic['PRECHAN'] == [5, 1, 5, 5, 2, 5, 5, 5,
                              5, 5, 5, 5, 5, 5, 5, 5]
    assert dic['SW_h'] == 10000
    assert dic['NUC1'] == '1H'
    assert len(dic['_comments']) == 2

    output = tmp_path / 'acqus'
    ng.bruker.write_jcamp(dic, output)
    text = output.read_text()
    assert '##$LFILTER= 200' in text
    assert '##$PRECHAN= (0..15)' in text
    assert ng.bruker.read_jcamp(output) == dic


def test_jcamp2(tmp_path):
    """Read and write known processing parameters from a packaged fixture."""
    source = os.path.join(DATA_DIR, '1', 'pdata', '1', 'procs')
    dic = ng.bruker.read_jcamp(source)

    assert dic['OFFSET'] == 13.03153
    assert dic['SF'] == 600.13
    assert dic['SI'] == 2
    assert dic['BYTORDP'] == 0
    assert dic['AXNUC'] == '1H'

    output = tmp_path / 'procs'
    ng.bruker.write_jcamp(dic, output)
    text = output.read_text()
    assert '##$OFFSET= 13.03153' in text
    assert '##$AXNUC= <1H>' in text
    assert ng.bruker.read_jcamp(output) == dic


def test_pprog(tmp_path):
    """Read and write a synthetic pulse-program parser fixture."""
    expected = {
        'var': {'LOOPC': '58', 'DELAY': '0.25'},
        'incr': [[0], [2], [3], [4]],
        'loop': [4, 58, 8, 16],
        'phase': [[1], [2], [3], [4]],
        'ph_extra': [[''], ['(p2)'], [''], ['(p4)']],
    }

    dic = ng.bruker.read_pprog(SYNTHETIC_PPROG)
    assert dic == expected

    output = tmp_path / 'pulseprogram'
    ng.bruker.write_pprog(output, dic)
    text = output.read_text()
    assert '"LOOPC=58"' in text
    assert text.count('lo to 0 times') == 4
    assert ng.bruker.read_pprog(output) == dic


def _make_2d_dic(indirect_dic):
    """Return minimal Bruker parameters for a 2D dataset."""
    return {
        'acqus': {
            'AQ_mod': 3,
            'NUC1': '1H',
            'O1': 0.0,
            'SFO1': 400.0,
            'SW_h': 10000.0,
        },
        'procs': {'SF': 400.0},
        **indirect_dic,
    }


@pytest.mark.parametrize('fnmode', [1, 2])
def test_guess_udic_magnitude_indirect_dimension(fnmode):
    """QF and QSEC indirect dimensions are real, not complex."""
    dic = _make_2d_dic({
        'acqu2s': {
            'FnMODE': fnmode,
            'NUC1': '1H',
            'SFO1': 400.0,
            'SW': 10.0,
        },
        'proc2s': {'SF': 400.0},
    })
    data = np.zeros((40, 128), dtype=np.complex128)

    udic = ng.bruker.guess_udic(dic, data)
    converter = ng.convert.converter()
    converter.from_bruker(dic, data)
    pipe_dic, pipe_data = converter.to_pipe()
    _, transposed = ng.pipe_proc.tp(pipe_dic.copy(), pipe_data)

    assert udic[0]['encoding'] == 'magnitude'
    assert udic[0]['complex'] is False
    assert pipe_dic['FDF2QUADFLAG'] == 0.0
    assert pipe_dic['FDF1QUADFLAG'] == 1.0
    assert transposed.shape == (128, 40)


@pytest.mark.parametrize('mc2', [0, 1])
def test_guess_udic_magnitude_indirect_dimension_from_proc_params(mc2):
    """Processed QF and QSEC indirect dimensions are real, not complex."""
    dic = _make_2d_dic({
        'proc2s': {
            'AXNUC': '1H',
            'MC2': mc2,
            'OFFSET': 0.0,
            'SF': 400.0,
            'SW_p': 4000.0,
        },
    })
    data = np.zeros((40, 128), dtype=np.complex128)

    udic = ng.bruker.guess_udic(dic, data)

    assert udic[0]['encoding'] == 'magnitude'
    assert udic[0]['complex'] is False

def test_read_pdata():
    """Reading processed bruker 1D data"""

    # read processed data
    specdir = os.path.join(DATA_DIR, '1', 'pdata', '1')
    dic, data = ng.bruker.read_pdata(specdir)

    # check that the data is correct
    assert np.all(data == [-36275840.0, -34775104.0])

    # check dictionaries are correct
    assert len(dic.keys()) == 2
    assert 'procs' in dic.keys()
    assert 'acqus' in dic.keys()
    assert len(dic['procs'].keys()) == 131
    assert len(dic['acqus'].keys()) == 298

    # specifying proc(s) files
    # (fired this error in 0.8 version:
    # UnboundLocalError: local variable 'pdata_path' referenced before
    # assignment)

    proc = os.path.join(specdir, 'procs')
    dic, data = ng.bruker.read_pdata(specdir, procs_files = [proc])
    assert len(dic['procs'].keys()) == 131


def test_reorder_submatrix():
    """reordering submatrix back and forth"""

    # make a dummy matrix
    data = np.arange(16, dtype='float64').reshape(4, 4)

    # correctly reordered matrix
    rdata = np.array([[ 0,  1,  4,  5],
                      [ 2,  3,  6,  7],
                      [ 8,  9, 12, 13],
                      [10, 11, 14, 15]], dtype='float64')

    # reorder from the submatrix form
    r1data = ng.bruker.reorder_submatrix(data, shape=(4, 4),
                                         submatrix_shape=(2, 2), reverse=False)

    # reorder to the submatrix form
    r2data = ng.bruker.reorder_submatrix(r1data, shape=(4, 4),
                                         submatrix_shape=(2, 2), reverse=True)
    # checks
    assert np.all(rdata == r1data)
    assert np.all(data == r2data)


def test_write_pdata():
    """ Writing a processed Bruker dataset """

    dic, data = ng.bruker.read_pdata(os.path.join(DATA_DIR, '1', 'pdata', '1'))

    # write to a temperory file
    td = tempfile.mkdtemp('.')
    ng.bruker.write_pdata(td, dic, data, write_procs=True, pdata_folder=10)

    assert os.path.isdir(os.path.join(td, 'pdata', '10'))
    assert os.path.isfile(os.path.join(td, 'pdata', '10', 'procs'))
    assert os.path.isfile(os.path.join(td, 'pdata', '10', 'proc'))
    assert os.path.isfile(os.path.join(td, 'pdata', '10', '1r'))

    rdic, rdata = ng.bruker.read_pdata(os.path.join(td, 'pdata', '10'))

    assert np.all(data == rdata)
    assert rdic['procs'].keys() == dic['procs'].keys()
    shutil.rmtree(td)


def test_dspfvs_clamp():
    """DSPFVS values below 10 are clamped to 10 (default for DQD).

    Older Bruker files may report DSPFVS < 10. The lookup table starts at
    DSPFVS = 10, so values below 10 are clamped to 10 rather than raising.
    """
    data = np.exp(-np.arange(256) / 30.0).astype(np.complex128)

    # DSPFVS = 0, DECIM = 2 -> clamped to DSPFVS = 10, phase = 44.75
    dic = {'acqus': {'DECIM': 2, 'DSPFVS': 0, 'TD': 512}}
    out = ng.bruker.remove_digital_filter(dic, data.copy())
    assert len(out) == 256 - int(np.floor(44.75 + 2))

    # DSPFVS = 1, DECIM = 2 -> also clamped to 10
    dic = {'acqus': {'DECIM': 2, 'DSPFVS': 1, 'TD': 512}}
    out = ng.bruker.remove_digital_filter(dic, data.copy())
    assert len(out) == 256 - int(np.floor(44.75 + 2))

    # DSPFVS = 9, DECIM = 2 -> also clamped to 10
    dic = {'acqus': {'DECIM': 2, 'DSPFVS': 9, 'TD': 512}}
    out = ng.bruker.remove_digital_filter(dic, data.copy())
    assert len(out) == 256 - int(np.floor(44.75 + 2))

    # DSPFVS = 10, DECIM = 2 -> not clamped, same result
    dic = {'acqus': {'DECIM': 2, 'DSPFVS': 10, 'TD': 512}}
    out10 = ng.bruker.remove_digital_filter(dic, data.copy())
    assert len(out10) == 256 - int(np.floor(44.75 + 2))

    # DSPFVS = 0 and DSPFVS = 10 give identical output
    dic = {'acqus': {'DECIM': 2, 'DSPFVS': 0, 'TD': 512}}
    out0 = ng.bruker.remove_digital_filter(dic, data.copy())
    dic = {'acqus': {'DECIM': 2, 'DSPFVS': 10, 'TD': 512}}
    out10 = ng.bruker.remove_digital_filter(dic, data.copy())
    assert np.allclose(out0, out10)


def test_remove_dc_offset():
    """remove_dc_offset=True removes the DC spike from the spectrum."""
    # synthetic FID: decaying exponential at a non-centre frequency + known
    # complex DC offset.  The DC offset dominates the spectrum; after
    # remove_dc_offset=True the maximum spectral value drops to the signal
    # level.
    n = 256
    t = np.arange(n)
    signal = np.exp(-t / 30.0) * np.exp(1j * 2 * np.pi * 0.125 * t)
    dc_offset = 3.0 + 2.0j
    data = signal + dc_offset

    # without DC offset removal: DC spike dominates the spectrum
    out_off = ng.bruker.rm_dig_filter(data, decim=80, dspfvs=21,
                                      grpdly=76.0, remove_dc_offset=False)
    sp_off = np.abs(np.fft.fftshift(np.fft.fft(out_off)))

    # with DC offset removal: DC spike is gone
    out_on = ng.bruker.rm_dig_filter(data, decim=80, dspfvs=21,
                                     grpdly=76.0, remove_dc_offset=True)
    sp_on = np.abs(np.fft.fftshift(np.fft.fft(out_on)))

    # The DC spike must dominate without removal
    assert sp_off.max() > 100, f"expected DC spike, got max={sp_off.max():.2f}"
    # After removal, the maximum drops to signal level
    assert sp_on.max() < sp_off.max() / 10, (
        f"expected DC spike removed, got {sp_on.max():.2f} vs {sp_off.max():.2f}"
    )


def test_remove_digital_filter_post_proc_positive_fft():
    """Conjugation adapts the positive ramp to the NMRPipe FT -df sign."""
    points, delay = 16, 2.25
    bins = np.array([3, 10])
    amplitudes = np.array([2 + 3j, -4 + 1j])
    dic = {'acqus': {'DECIM': 24, 'DSPFVS': 20, 'GRPDLY': delay}}
    samples = np.arange(points)
    fid = amplitudes[:, None] * np.exp(
        2j * np.pi * (
            delay * bins[:, None] - (bins[:, None] - points // 2) * samples
        ) / points
    )
    spectrum = ng.proc_base.fft_positive(fid)
    corrected = ng.bruker.remove_digital_filter(
        dic, spectrum.conj(), truncate=False, post_proc=True
    ).conj()
    expected = np.zeros((2, points), dtype=complex)
    expected[np.arange(2), bins] = points * amplitudes
    np.testing.assert_allclose(corrected, expected, rtol=0, atol=1e-12)


def test_remove_dc_offset_post_proc_incompatible():
    """remove_dc_offset=True with post_proc=True raises ValueError."""
    data = np.exp(-np.arange(256) / 30.0).astype(np.complex128)
    with pytest.raises(ValueError, match="remove_dc_offset"):
        ng.bruker.rm_dig_filter(data, decim=80, dspfvs=21, grpdly=76.0,
                                post_proc=True, remove_dc_offset=True)

    dic = {'acqus': {'DECIM': 80, 'DSPFVS': 21, 'GRPDLY': 76.0, 'TD': 512}}
    with pytest.raises(ValueError, match="remove_dc_offset"):
        ng.bruker.remove_digital_filter(dic, data.copy(),
                                        post_proc=True, remove_dc_offset=True)


def test_remove_dc_offset_default_false():
    """Default remove_dc_offset=False is identical to not passing the flag."""
    data = np.exp(-np.arange(256) / 30.0).astype(np.complex128)
    out_default = ng.bruker.rm_dig_filter(data, decim=80, dspfvs=21,
                                          grpdly=76.0)
    out_explicit = ng.bruker.rm_dig_filter(data, decim=80, dspfvs=21,
                                           grpdly=76.0, remove_dc_offset=False)
    assert np.allclose(out_default, out_explicit)


def _real_acqus_bytes():
    """Bytes of the real acqus file shipped with the test data."""
    with open(os.path.join(DATA_DIR, '1', 'acqus'), 'rb') as f:
        return f.read()


def _write_temp(content):
    fd, temp_path = tempfile.mkstemp()
    with os.fdopen(fd, 'wb') as f:
        f.write(content)
    return temp_path


def test_read_jcamp_cp1252():
    """cp1252-encoded acqus (e.g. degree sign) decodes correctly."""
    content = _real_acqus_bytes().replace(
        b"##END=", "##$SOLVENT= <CDCl3 at 25\u00b0C>\n##END=".encode("cp1252"))
    temp_path = _write_temp(content)
    try:
        dic = ng.bruker.read_jcamp(temp_path)
        assert dic["SOLVENT"] == "CDCl3 at 25\u00b0C"
        assert dic["LOCKED"] is True
    finally:
        os.remove(temp_path)


def test_read_jcamp_cr_only_line_endings(tmp_path):
    """CR-only JCAMP records are split like normal text-file reading."""
    path = tmp_path / "acqus"
    path.write_bytes(b"##TITLE= synthetic\r##$FOO= 1\r##END=\r")

    dic = ng.bruker.read_jcamp(path)

    assert dic["FOO"] == 1


def test_read_jcamp_undecodable_bytes():
    """bytes invalid in both utf-8 and cp1252 do not crash the reader."""
    content = _real_acqus_bytes().replace(
        b"##END=", b"##$BAD= <\x81>\n##END=")
    temp_path = _write_temp(content)
    try:
        with pytest.warns(UserWarning, match="latin-1"):
            dic = ng.bruker.read_jcamp(temp_path)
        assert dic["BAD"] == "\x81"
        assert dic["LOCKED"] is True
    finally:
        os.remove(temp_path)


def test_read_jcamp_explicit_encoding():
    """an explicit encoding is tried first."""
    content = _real_acqus_bytes().replace(
        b"##END=", b"##$TEMPUNIT= <\xb0C>\n##END=")
    temp_path = _write_temp(content)
    try:
        dic = ng.bruker.read_jcamp(temp_path, encoding="mac-roman")
        assert dic["TEMPUNIT"] == "\u221eC"
        dic = ng.bruker.read_jcamp(temp_path)
        assert dic["TEMPUNIT"] == "\u00b0C"
    finally:
        os.remove(temp_path)


def test_read_jcamp_unknown_encoding():
    """an unknown explicit encoding falls back to the detected encoding."""
    temp_path = _write_temp(_real_acqus_bytes())
    try:
        dic = ng.bruker.read_jcamp(temp_path, encoding="not-a-codec")
        assert dic["LOCKED"] is True
    finally:
        os.remove(temp_path)


def test_read_jcamp_utf8_bom():
    """a byte order mark does not hide the first record."""
    import warnings
    content = b"\xef\xbb\xbf" + _real_acqus_bytes()
    temp_path = _write_temp(content)
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            dic = ng.bruker.read_jcamp(temp_path)
        assert not [w for w in caught if "Extraneous line" in str(w.message)]
        assert dic["_coreheader"][0].startswith("##TITLE=")
        assert dic["LOCKED"] is True
    finally:
        os.remove(temp_path)


@pytest.mark.parametrize("stored_rows", [4, 8])
@pytest.mark.parametrize("nus", [False, True])
def test_read_bruker_can_keep_flat_samples_on_declared_shape_mismatch(
    tmp_path, stored_rows, nus,
):
    (tmp_path / "acqus").write_text(
        "##TITLE= Synthetic SER\n##$TD= 240\n##$AQ_mod= 3\n"
        "##$BYTORDA= 1\n##$DTYPA= 0\n##$PARMODE= 1\n"
        f"##$FnTYPE= {2 if nus else 0}\n##END=\n"
    )
    (tmp_path / "acqu2s").write_text("##TITLE= Indirect\n##$TD= 6\n##END=\n")
    words = np.arange(stored_rows * 256, dtype=">i4")
    (tmp_path / "ser").write_bytes(words.tobytes())
    expected = words[::2] + 1j * words[1::2]
    if nus:
        (tmp_path / "nuslist").write_text("0\n2\n")
    metadata, automatic = ng.bruker.read(tmp_path, read_pulseprogram=False)
    np.testing.assert_array_equal(automatic, expected.reshape(stored_rows, 128))
    if nus:
        assert metadata["nuslist"] == [(0,), (2,)]
        (tmp_path / "nuslist").unlink()
        (tmp_path / "nuslist").mkdir()

    with pytest.warns(UserWarning, match="A 1D array will be returned"):
        metadata, flat = ng.bruker.read(
            tmp_path, read_pulseprogram=False, recover_shape=False,
            read_nus_schedule=False,
        )
    assert "nuslist" not in metadata
    assert metadata["acqus"]["FnTYPE"] == (2 if nus else 0)
    np.testing.assert_array_equal(flat, expected)



def test_float64_ser_can_use_historical_flat_shape(tmp_path):
    (tmp_path / "acqus").write_text(
        "##TITLE= Float64 SER\n##$TD= 120\n##$AQ_mod= 3\n"
        "##$BYTORDA= 0\n##$DTYPA= 2\n##$PARMODE= 1\n##END=\n"
    )
    (tmp_path / "acqu2s").write_text("##TITLE= Indirect\n##$TD= 8\n##END=\n")
    words = np.arange(8 * 128, dtype="<f8")
    (tmp_path / "ser").write_bytes(words.tobytes())
    expected = words[::2] + 1j * words[1::2]

    _, native = ng.bruker.read(tmp_path, read_pulseprogram=False)
    np.testing.assert_array_equal(native, expected.reshape(8, 64))

    with pytest.warns(UserWarning, match="A 1D array will be returned"):
        _, flat = ng.bruker.read(
            tmp_path, read_pulseprogram=False, recover_shape=False, legacy_layout=True,
        )
    np.testing.assert_array_equal(flat, expected)


@pytest.mark.parametrize("indirect_td", [2, "unavailable"])
def test_historical_fid_layout_ignores_stale_indirect_status(tmp_path, indirect_td):
    (tmp_path / "acqus").write_text(
        "##TITLE= Synthetic FID\n##$TD= 256\n##$AQ_mod= 3\n"
        "##$BYTORDA= 1\n##$DTYPA= 0\n##$PARMODE= 0\n##END=\n"
    )
    (tmp_path / "acqu2s").write_text(
        f"##TITLE= Stale indirect\n##$TD= {indirect_td}\n##END=\n"
    )
    words = np.arange(512, dtype=">i4")
    (tmp_path / "fid").write_bytes(words.tobytes())
    if indirect_td == 2:
        _, native = ng.bruker.read(tmp_path, read_pulseprogram=False)
        assert native.shape == (2, 128)

    with pytest.warns(UserWarning, match="A 1D array will be returned"):
        _, flat = ng.bruker.read(
            tmp_path, read_pulseprogram=False, recover_shape=False, legacy_layout=True,
        )
    np.testing.assert_array_equal(flat, words[::2] + 1j * words[1::2])
