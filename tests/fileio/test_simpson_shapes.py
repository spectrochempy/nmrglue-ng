"""Self-contained shape-contract tests for the SIMPSON reader.

The four 1D SIMPSON encodings (TEXT, BINARY, XREIM, RAWBIN) describe the same
one-dimensional data set and must all return a 1D array when the data set has
a single element (NELEM absent or 1).  Multi-element and 2D data keep their
element/indirect axis.
"""

import math

import numpy as np
import pytest

import nmrglue.fileio.simpson as simpson


def _complex_values(count):
    """Build a 1D complex64 signal of `count` exactly representable points."""
    idx = np.arange(count, dtype='float32')
    real = 1.0 + idx * 0.25
    imag = -(0.5 + idx * 0.125)
    return (real + 1j * imag).astype('complex64')


def _simpson_word(value):
    """Encode a float as the 4-byte little-endian word of a -binary file."""
    value = float(np.float32(value))
    if value == 0.0:
        return bytes(4)
    negative = value < 0.0
    mantissa, exponent = math.frexp(abs(value))
    significand = int(round(mantissa * (1 << 23)))
    if significand == 1 << 23:
        significand >>= 1
        exponent += 1
    exponent += 0x7F
    return bytes((
        significand & 0xFF,
        (significand >> 8) & 0xFF,
        ((significand >> 16) & 0x7F) | ((exponent & 1) << 7),
        (exponent >> 1) | (0x80 if negative else 0),
    ))


def _pack_chars(data):
    """Pack 3-byte groups into the character groups of a -binary data block."""
    chars = []
    for i in range(0, len(data), 3):
        b0, b1, b2 = data[i:i + 3]
        codes = (
            b0 & 0x3F,
            (b1 & 0x0F) | ((b0 >> 6) << 4),
            (b2 & 0x03) | ((b1 >> 4) << 2),
            b2 >> 2,
        )
        chars.extend(chr(33 + code) for code in codes)
    return ''.join(chars)


def _header(np_points, ni=None, nelem=None):
    lines = ['SIMP']
    if np_points is not None:
        lines.append(f'NP={np_points}')
    lines.append('SW=8000.0')
    if ni is not None:
        lines.append(f'NI={ni}')
    if nelem is not None:
        lines.append(f'NELEM={nelem}')
    return lines


def _write_text(path, values, np_points, ni=None, nelem=None):
    lines = _header(np_points, ni=ni, nelem=nelem)
    lines.append('DATA')
    lines += [f'{v.real:.10g} {v.imag:.10g}' for v in values]
    lines.append('END')
    path.write_text('\n'.join(lines) + '\n')


def _write_binary(path, values, np_points, ni=None, nelem=None):
    words = []
    for v in values:
        words.append(_simpson_word(v.real))
        words.append(_simpson_word(v.imag))
    data = b''.join(words)
    if len(data) % 3:
        data += b'\x00' * (3 - len(data) % 3)
    lines = _header(np_points, ni=ni, nelem=nelem)
    lines.append('FORMAT=text')
    lines.append('DATA')
    path.write_text('\n'.join(lines) + '\n' + _pack_chars(data) + 'END\n')


def _write_xreim(path, values):
    lines = [f'{i} {v.real:.10g} {v.imag:.10g}' for i, v in enumerate(values)]
    path.write_text('\n'.join(lines) + '\n')


def _write_rawbin(path, values):
    data = np.concatenate([values.real, values.imag]).astype('float32')
    data.tofile(path)


def test_text_1d_single_element_is_one_dimensional(tmp_path):
    """A single-element 1D TEXT data set is a 1D array."""
    values = _complex_values(8)
    path = tmp_path / 'signal.fid'
    _write_text(path, values, np_points=8)

    dic, data = simpson.read(path)

    assert dic['NELEM'] == 1
    assert data.shape == (8,)
    assert data.dtype == np.complex64
    np.testing.assert_array_equal(data, values)


def test_text_1d_multi_element_keeps_element_axis(tmp_path):
    """A multi-element 1D TEXT data set keeps (NELEM, NP)."""
    values = _complex_values(24)
    path = tmp_path / 'multielem.fid'
    _write_text(path, values, np_points=8, nelem=3)

    dic, data = simpson.read(path)

    assert dic['NELEM'] == 3
    assert data.shape == (3, 8)
    np.testing.assert_array_equal(data.reshape(-1), values)


def test_binary_1d_single_element_is_one_dimensional(tmp_path):
    """A single-element 1D BINARY data set is a 1D array."""
    values = _complex_values(8)
    path = tmp_path / 'signal.binary.fid'
    _write_binary(path, values, np_points=8)

    dic, data = simpson.read(path)

    assert dic['NELEM'] == 1
    assert data.shape == (8,)
    assert data.dtype == np.complex64
    np.testing.assert_array_equal(data, values)


def test_binary_1d_multi_element_keeps_element_axis(tmp_path):
    """A multi-element 1D BINARY data set keeps (NELEM, NP)."""
    values = _complex_values(24)
    path = tmp_path / 'multielem.binary.fid'
    _write_binary(path, values, np_points=8, nelem=3)

    dic, data = simpson.read(path)

    assert dic['NELEM'] == 3
    assert data.shape == (3, 8)
    np.testing.assert_array_equal(data.reshape(-1), values)


def test_binary_1d_rejects_block_shorter_than_np(tmp_path):
    """A single-element BINARY block shorter than header NP still raises."""
    values = _complex_values(6)
    path = tmp_path / 'short.binary.fid'
    _write_binary(path, values, np_points=8)

    with pytest.raises(ValueError):
        simpson.read(path)


def test_binary_1d_rejects_missing_np_header(tmp_path):
    """A single-element BINARY header without NP still raises."""
    values = _complex_values(8)
    path = tmp_path / 'no_np.binary.fid'
    _write_binary(path, values, np_points=None)

    with pytest.raises(KeyError):
        simpson.read(path)


def test_text_2d_shape_is_unchanged(tmp_path):
    """2D TEXT data is (NI, NP) with or without multiple elements."""
    values = _complex_values(12)
    path = tmp_path / 'ser2d.fid'
    _write_text(path, values, np_points=4, ni=3)

    _, data = simpson.read(path)

    assert data.shape == (3, 4)
    np.testing.assert_array_equal(data.reshape(-1), values)

    values = _complex_values(24)
    path = tmp_path / 'multielem2d.fid'
    _write_text(path, values, np_points=4, ni=3, nelem=2)

    dic, data = simpson.read(path)

    assert dic['NELEM'] == 2
    assert data.shape == (6, 4)
    np.testing.assert_array_equal(data.reshape(-1), values)


def test_indexed_and_raw_1d_encodings_are_one_dimensional(tmp_path):
    """XREIM and RAWBIN keep returning 1D arrays for 1D data."""
    values = _complex_values(8)

    xreim_path = tmp_path / 'signal.xreim'
    _write_xreim(xreim_path, values)
    _, xreim_data = simpson.read(xreim_path)
    assert xreim_data.shape == (8,)
    np.testing.assert_array_equal(xreim_data, values)

    rawbin_path = tmp_path / 'signal.rawbin'
    _write_rawbin(rawbin_path, values)
    _, rawbin_data = simpson.read(rawbin_path, ftype='RAWBIN',
                                  spe=False, ndim=1)
    assert rawbin_data.shape == (8,)
    np.testing.assert_array_equal(rawbin_data, values)


def test_1d_encodings_agree(tmp_path):
    """All four 1D encodings give the same shape and the same values."""
    values = _complex_values(8)

    readers = []
    for name, writer in (('text.fid', _write_text),
                         ('binary.fid', _write_binary)):
        path = tmp_path / name
        writer(path, values, np_points=8)
        readers.append(simpson.read(path))

    xreim_path = tmp_path / 'xreim.fid'
    _write_xreim(xreim_path, values)
    readers.append(simpson.read(xreim_path))

    rawbin_path = tmp_path / 'rawbin.fid'
    _write_rawbin(rawbin_path, values)
    readers.append(simpson.read(rawbin_path, ftype='RAWBIN', spe=False,
                                ndim=1))

    for _, data in readers:
        assert data.shape == values.shape
        np.testing.assert_array_equal(data, values)
