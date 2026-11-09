"""
Functions for reading and writing files created by the `SIMPSON simulations
program <http://www.bionmr.chem.au.dk/bionmr/software/simpson.php>`_.
"""

from itertools import islice
import math
from warnings import warn

import numpy as np


def read(filename, ftype=None, ndim=None, NP=None, NI=None, spe=None, *, legacy_layout=False):
    """
    Read a SIMPSON file.

    Read a NMR data file saved using in a number of formats produced using
    the SIMPSON simulation program.

    Parameters
    ----------
    filename : str
        Name of SIMPSON file to read data from.
    ftype : {None, 'TEXT', 'BINARY', 'XREIM', 'XYREIM', 'RAWBIN'}, optional
        A string indicating the type of SIMPSON file:

        ``TEXT`` : SIMPSON text format, no fsave arguments.

        ``BINARY`` : SIMPSON binary format, -binary fsave argument.

        ``XREIM`` : Indexed 1D format, rows of frequency/time, real and
        imaginary parts of the data.  Saved with -xreim argument.

        ``XYREIM`` : Indexed 2D format, rows of frequency/time (indirect
        dimension then direct dimension), real and imaginary parts of the
        data. Saved with -xyreim argument.

        ``RAWBIN`` : Raw binary format.  Saved with -raw_bin argument.  ndim
        and spe must also be provided.  In addition if ndim is 2, NP and NI
        must be defined.

        ``None`` : Automatically determine file type.  If this fails the file
        type should be implicitly provided.

        Other formats of files may be created by SIMPSON, but are not currently
        supported.

    Other Parameters
    ----------------
    ndim : {None, 1, 2}, optional
        Dimensionality of the data in the file, only used when ftype is
        "RAWBIN".
    NP : int, optional
        Number of points {R|I} in the direct dimension.  Only used when
        ftype is "RAWBIN" and ndim is 2.
    NI : int, optional
        Number of points in the indirect dimension.  Only used when ftype is
        "RAWBIN" and ndim is 2.
    spe : bool, optional
        True when the data is in the frequency domain, False for time domain
        data.  Only used when ftype is "RAWBIN"

    legacy_layout : bool, optional
        Sort both coordinate axes of XYREIM data as in the historical
        SpectroChemPy reader. The default retains first occurrence order.

    Returns
    -------
    dic : dict
        Dictionary of spectra parameters.  For some file formats this may be
        empty.
    data : ndarray
        Complex array of spectral data.  A single-element data set
        (``NELEM`` absent or 1) gives ``(NP,)`` for 1D data and ``(NI, NP)``
        for 2D data; a multi-element data set keeps the element axis as
        ``(NELEM, NP)`` and ``(NI*NELEM, NP)``.  The 1D encodings of one
        data set therefore share the same shape.

    """
    if ftype is None:
        ftype = guess_ftype(filename)

    if ftype == "TEXT":
        return read_text(filename)
    elif ftype == "BINARY":
        return read_binary(filename)
    elif ftype == "XREIM":
        return read_xreim(filename)
    elif ftype == "XYREIM":
        return read_xyreim(filename, sort_axes=legacy_layout)
    elif ftype == "RAWBIN":
        if spe is None:
            raise ValueError('spe must be True or False for raw_bin data')
        if ndim == 1:
            return read_raw_bin_1d(filename, spe)
        elif ndim == 2:
            if NP is None or NI is None:
                raise ValueError("NP and NI must be given for raw_bin data")
            return read_raw_bin_2d(filename, NP, NI, spe)
        else:
            raise ValueError('ndim must be 1 or 2 for raw_bin data')
    else:
        raise ValueError("unknown ftype")


def guess_ftype(filename):
    """Determine the SIMPSON file type from a bounded sample of rows."""
    with open(filename, "rb") as stream:
        first = next((line.strip() for line in stream if line.strip()), b"")
        if first.startswith(b"SIMP"):
            for line in stream:
                record = line.strip()
                if record.startswith(b"FORMAT"):
                    return "BINARY"
                if record == b"DATA":
                    break
            return "TEXT"
        stream.seek(0)
        rows = list(islice((line.split() for line in stream if line.strip()), 8))

    if rows and len(rows[0]) in (3, 4) and all(len(row) == len(rows[0]) for row in rows):
        try:
            for row in rows:
                tuple(float(value) for value in row)
        except ValueError:
            return "RAWBIN"
        return "XREIM" if len(rows[0]) == 3 else "XYREIM"
    return "RAWBIN"

###############################
# Read SIMPSON text file data #
###############################


def read_text(filename):
    """Read a SIMPSON text file. See :py:func:`read`."""
    with open(filename, 'r') as stream:
        return _read_text(stream)


def _read_header(stream):
    metadata = {}
    for line in stream:
        record = line.strip()
        if not record or record == "SIMP":
            continue
        if record == "DATA":
            break
        key, separator, value = record.partition("=")
        if separator:
            metadata[key.strip()] = value.strip()
        else:
            warn(f"Skipping SIMPSON header line: {record!r}", stacklevel=2)
    else:
        raise ValueError("SIMPSON requires a DATA block")
    for key in ("SW", "SW1"):
        if key in metadata:
            metadata[key] = float(metadata[key])
    for key in ("NP", "NI", "NELEM"):
        if key in metadata:
            metadata[key] = int(metadata[key])
    metadata.setdefault("NELEM", 1)
    return metadata


def _read_text(f):
    dic = _read_header(f)
    elements = dic["NELEM"]
    direct = dic["NP"]
    indirect = dic.get("NI", 1)
    if min(elements, direct, indirect) < 1:
        raise ValueError("SIMPSON point and element counts must be positive")
    shape = (elements * indirect, direct) if "NI" in dic or elements > 1 else (direct,)
    data = np.empty(shape, dtype="complex64")
    count = 0
    for line in f:
        record = line.strip()
        if record == "END":
            break
        if not record:
            continue
        fields = record.split()
        if len(fields) < 2 or count == data.size:
            raise ValueError("SIMPSON TEXT block disagrees with its declared shape")
        data.flat[count] = complex(float(fields[0]), float(fields[1]))
        count += 1
    if count != data.size:
        raise ValueError("SIMPSON TEXT block disagrees with its declared shape")
    return dic, data


#############################
# Read xreim or xyreim data #
#############################


def read_xreim(filename):
    """Read indexed 1D points in file order."""
    rows = np.loadtxt(filename, ndmin=2, comments=None)
    if rows.shape[0] == 0 or rows.shape[1] != 3:
        raise ValueError("SIMPSON XREIM requires three columns")
    data = np.empty(rows.shape[0], dtype="complex64")
    data.real, data.imag = rows[:, 1], rows[:, 2]
    return {"units": rows[:, 0].astype("float32")}, data


def read_xyreim(filename, *, sort_axes=False):
    """Read a rectangular indexed 2D grid with consistent axis ordering."""
    rows = np.loadtxt(filename, ndmin=2, comments=None)
    if rows.shape[0] == 0 or rows.shape[1] != 4 or not np.isfinite(rows[:, :2]).all():
        raise ValueError("SIMPSON XYREIM requires four columns and finite coordinates")

    axes = []
    indices = []
    for column in rows[:, :2].T:
        values, first, inverse = np.unique(column, return_index=True, return_inverse=True)
        order = np.arange(values.size) if sort_axes else np.argsort(first)
        axes.append(values[order])
        indices.append(np.argsort(order)[inverse])

    shape = tuple(axis.size for axis in axes)
    positions = np.ravel_multi_index(tuple(indices), shape)
    if positions.size != math.prod(shape) or np.unique(positions).size != positions.size:
        raise ValueError("SIMPSON XYREIM requires one sample per point of a complete grid")
    data = np.empty(shape, dtype="complex64")
    data.real.flat[positions] = rows[:, 2]
    data.imag.flat[positions] = rows[:, 3]
    units = np.recarray(shape, dtype=[("ni_unit", "f8"), ("np_unit", "f8")])
    units.ni_unit = axes[0][:, None]
    units.np_unit = axes[1][None, :]
    return {"units": units}, data


######################
# Read raw_bin files #
######################


def read_raw_bin_1d(filename, spe=False):
    """Read a 1D raw binary SIMPSON file. See :py:func:`read`. """
    data = unappend_data(np.fromfile(filename, dtype='float32'))
    if spe:
        return {}, data[::-1]   # freq domain data is flipped
    else:
        return {}, data


def read_raw_bin_2d(filename, NP, NI, spe=False):
    """Read a 2D raw binary SIMPSON file. See :py:func:`read`. """
    data = np.fromfile(filename, dtype='float32').reshape(NI, NP * 2)
    if spe:
        # freq domain is saved reversed and shifted by 1 pt in each dimension,
        # so the first points is 0 in each vector, then N-1, N-2, ... 1
        # A bug? in SIMPSON causes the direct dimension shift to be left off
        # the imaginary data.  In addition the first real point in each vector
        # is the first real point in the spectrum.  Therefore only data[:,1:]
        # will match with other file formats.
        cdata = np.empty((NI, NP), dtype='complex64')
        cdata.real = np.roll(np.roll(data[::-1, NP - 1::-1], 1, 1), 1, 0)
        cdata.imag = np.roll(data[::-1, 2 * NP:NP - 1:-1], 1, 0)
        return {}, cdata
    else:
        # time domain is written as vectors of NP, with the imag appended
        return {}, unappend_data(data)


def unappend_data(data):
    """
    Return complex data with last axis unappended.

    Data should have imaginary data vector appended to real data vector.
    """
    h = int(data.shape[-1] / 2.0)
    return np.array(data[..., :h] + data[..., h:] * 1.j, dtype='complex64')


#############################
# Read SIMPSON binary files #
#############################


def read_binary(filename):
    """Read a binary SIMPSON file. See :py:func:`read`."""
    with open(filename, 'r') as stream:
        return _read_binary(stream)


def _read_binary(f):
    dic = _read_header(f)

    # extract characters from data block
    chardata = "".join([line.strip('\n') for line in f])
    chardata = chardata.removesuffix("END")

    # convert every 4 character to 3 'bytes'
    nquads, mod = divmod(len(chardata), 4)
    if mod:
        raise ValueError("SIMPSON binary data length is not a multiple of four")
    bytes = []
    for i in range(nquads):
        bytes += chars2bytes(chardata[i * 4:(i + 1) * 4])

    # DEBUGGING
    # return dic, bytes
    # convert every 4 'bytes' to a float, then complex data
    num_points, _num_pad = divmod(len(bytes), 4)
    data = np.empty((num_points, ), dtype='float32')

    for i in range(num_points):
        data[i] = bytes2float(bytes[i * 4: (i + 1) * 4])
    data = data.view('complex64')

    # reorder data according to dimensionality and domain
    if 'NI' in dic:  # 2D data
        return dic, data.reshape(dic['NI']*dic['NELEM'], dic['NP'])

    else:   # 1D data
        if dic['NELEM'] == 1:  # single-element 1D data is 1D
            # the reshape also revalidates the block size against header NP
            return dic, data.reshape(dic['NP'])
        return dic, data.reshape(dic['NELEM'], dic['NP'])

BASE = 33
FIRST = lambda f, x: ((x) & ~(~0 << f))
LAST = lambda f, x: ((x) & (~0 << (8 - f)))


def chars2bytes(chars):
    """Convert four characters from a data block into 3 'bytes'."""
    c0, c1, c2, c3 = (ord(c) - BASE for c in chars)

    return [FIRST(6, c0) | LAST(2, c1 << 2),
            FIRST(4, c1) | LAST(4, c2 << 2),
            FIRST(2, c2) | LAST(6, c3 << 2)]


def bytes2float(bytes):
    """ Convert four bytes to a string. """
    # the first 23 bits (0-22) define the mantissa
    # the next 8 bits (23-30) the exponent,
    # the last bit (31) defines the sign
    b0, b1, b2, b3 = bytes
    mantissa = ((b2 % 128) << 16) + (b1 << 8) + b0
    exponent = (b3 % 128) * 2 + (b2 >= 128) * 1
    negative = b3 >= 128

    e = exponent - 0x7f
    m = np.abs(mantissa) / np.float64(1 << 23)

    if negative:
        return -math.ldexp(m, e)
    return math.ldexp(m, e)
