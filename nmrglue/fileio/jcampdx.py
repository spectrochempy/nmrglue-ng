"""
Functions for reading JCAMP-DX files.

The interface is oriented towards 1D data. Multidimensional NTUPLES spectra
can be read, as the set of 1D pages they are stored as, but guess_udic
describes their direct dimension only.
"""

import os
import re
from warnings import warn

import numpy as np

from . import fileiobase

__developer_info__ = """
JCAMP-DX file format information
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The format reference publications are available at:
http://www.jcamp-dx.org/protocols.html

Notes:
    * Writing NMR data in JCAMP-DX format is not currently supported.
    * Multidimensional NTUPLES spectra are read as sets of 1D pages;
      guess_udic describes the direct dimension only.
"""


def _getkey(keystr):
    '''
    Format key strings.
    From JCAMP-DX specs:
    "When LABELS are parsed, alphabetic
    characters are converted to upper case, and all spaces,
    dashes, slashes, and underlines are discarded. (XUNITS,
    xunits, xUNITS, and X-UNITS are equivalent.)"
    '''
    return (keystr.strip().upper().replace(" ", "")
            .replace("-", "").replace("_", "").replace("/", ""))


def _parsejcampdx(filename, read_err=None, _opened=None):
    '''
    Actual JCAMP-DX reading. Returns a list of data sections i.e. "blocks",
    each of them being a dictionary of JCAMP-DX tags, in the order the blocks
    end in the file (so a LINK block follows the blocks it contains).

    If _opened is a list, a (block, enclosing block or None) tuple is appended
    to it for every block, in the order the blocks begin in the file.
    '''

    # "blocks" in JCAMP-DX may be nested, and they begin with ##TITLE and
    # end with ##END. Keep active blocks in stack:
    blockstack = []
    # keep reference to active block, i.e. the one to which to read
    activeblock = None
    # when encountering ##END, push the ready dict to another list
    readyblocklist = []

    errors = "replace" if read_err is None else read_err
    filein = open(filename, 'r', encoding="utf-8-sig", errors=errors)

    currentkey = None
    currentvaluestrings = []

    for line in filein:

        # split comments
        commentsplit = line.split("$$", 1)
        actual = commentsplit[0].lstrip()
        if len(commentsplit) > 1:
            if activeblock:
                activeblock["_comments"].append(commentsplit[1])

        # continue with rest:
        if not actual:
            continue  # line had with nothing but comments

        # for multi-line data, linebreak must be restored if it has been
        # cut out with comments:
        if actual[-1] != "\n":
            actual += "\n"

        # encountered new key:
        if actual[:2] == "##":

            # push previous key/value pair to active dictionary
            # single value is continuous string including newlines
            # but there might be multiple values if the same key exist
            # multiple times thus values are collected to list
            if currentkey is not None and currentvaluestrings:
                key = _getkey(currentkey)
                value = "".join(currentvaluestrings)  # collapse
                if not value.strip():
                    warn(f"JCAMP-DX key without value: {key}")
                else:
                    try:
                        activeblock[key].append(value)
                    except KeyError:
                        activeblock[key] = [value]
                currentkey = None
                currentvaluestrings = []

            if actual[:7] == "##TITLE":
                # begin new block dictionary
                activeblock = {"_comments": []}
                if _opened is not None:
                    parent = blockstack[-1] if blockstack else None
                    _opened.append((activeblock, parent))
                blockstack.append(activeblock)

            # only ##END= closes a block; ##END NTUPLES= closes the NTUPLES
            # table inside it and, as before, is not kept
            endkey = _getkey(actual[2:].split("=", 1)[0])
            if endkey == "ENDNTUPLES":
                continue
            if endkey == "END":
                # finalize current block
                if activeblock:  # ensure that we had active block instead of too many ##ENDs
                    readyblocklist.append(blockstack.pop())
                if blockstack:
                    # continue reading to previous block in stack, if available
                    activeblock = blockstack[-1]
                else:
                    # otherwise mark it None to prevent reading
                    activeblock = None
                continue

            if activeblock:
                # try to split to key and value and check sanity
                keysplit = actual.split("=", 1)
                if len(keysplit) < 2:
                    warn("Bad JCAMP-DX line, can't split key and value correctly:" +
                         line)
                    continue
                keystr = keysplit[0][2:]  # remove "##" already here
                valuestr = keysplit[1]
                if not keystr:
                    warn(f"Empty key in JCAMP-DX line: {line}")
                    currentkey = None
                    currentvaluestrings = []
                    continue

                # split ok, init new key
                currentkey = keystr
                currentvaluestrings.append(valuestr)

        # line continues data of previous key, append to currentvaluestrings:
        else:
            if activeblock:
                if currentkey is None:
                    warn(f"JCAMP-DX data line without associated key: {line}")
                    continue

                currentvaluestrings.append(commentsplit[0])

    # push possible non-closed blocks
    while blockstack:
        readyblocklist.append(blockstack.pop())

    filein.close()

    return readyblocklist


def _readrawdic(filename, read_err=None):
    '''
    Reads entire JCAMP-DX file to dictionary, from which actual
    data is parsed later. Return value is a dictionary of different
    DATATYPEs, containing lists of actual block dictionaries(as it
    is possible have multiple entries of same DATATYPE in one file).
    '''

    # parse file to list of "blocks" i.e. separate data sections
    blocklist = _parsejcampdx(filename, read_err)

    # clean whitespace from entries, and remove empty entries
    cleandiclist = []
    for dic in blocklist:
        for key, valuelist in dic.items():
            dic[key] = [value.strip() for value in valuelist]
        for key, valuelist in dic.items():
            dic[key] = [value for value in valuelist if value]
        dic = {key: valuelist for key, valuelist in dic.items() if valuelist}
        if dic:
            cleandiclist.append(dic)

    returndic = {}
    # check DATATYPE entry of each block,
    # and build a dict of lists of dicts
    for dic in cleandiclist:
        try:
            datatypelist = dic["DATATYPE"]
            currdatatype = datatypelist[0].strip().upper().replace(" ", "")
            if len(datatypelist) > 1:
                # basically sections with multiple DATATYPES
                # are invalid, but we may still give it a try:
                for datatype in datatypelist:
                    cleandatatype = datatype.strip().upper().replace(" ", "")
                    if cleandatatype == "NMRSPECTRUM":
                        currdatatype = cleandatatype
                        break
                    if cleandatatype == "NMRFID":
                        currdatatype = cleandatatype
                        break
                # no SPECTRUM / FID found, just go with the first entry
        except KeyError:
            # no datatype in this section, use dummy
            currdatatype = "NA"

        # push to result dict
        key = "_datatype_"+currdatatype
        try:
            returndic[key].append(dic)
        except KeyError:
            returndic[key] = [dic]

    return returndic


def read_blocks(filename, read_err=None):
    """
    Read every data block of a JCAMP-DX file, in file order.

    Where :func:`read` selects a single NMR block, this returns all blocks of
    a file, of any DATATYPE and including those nested in a LINK block, in
    the order they begin in the file, so that the caller can choose between
    them.

    Parameters
    ----------
    filename : str
        File to read from.
    read_err : str, optional
        Error handling for character decoding, as for :func:`read`.

    Returns
    -------
    blocks : list of dict
        One dictionary per block, in the order the blocks begin in the file.
        Keys are labels normalised as in :func:`read` and values are lists of
        stripped strings, one per occurrence of the label in the block. Data
        tables such as ``XYDATA``, ``DATATABLE``, ``PEAKTABLE`` and
        ``XYPOINTS`` are kept unparsed; pass a block to :func:`getdataarray`
        to parse its data. ``blocks[i]["_parent"]`` is the index of the block
        enclosing block ``i``, or None for a top-level block.
    """
    if os.path.isfile(filename) is not True:
        raise OSError("file %s does not exist" % (filename))

    opened = []
    _parsejcampdx(filename, read_err, _opened=opened)

    # same cleaning as _readrawdic, but empty blocks are kept so that
    # the _parent indices stay valid
    position = {id(block): i for i, (block, _) in enumerate(opened)}
    blocks = []
    for block, parent in opened:
        clean = {}
        for key, valuelist in block.items():
            values = [value.strip() for value in valuelist]
            values = [value for value in values if value]
            if values:
                clean[key] = values
        clean["_parent"] = None if parent is None else position[id(parent)]
        blocks.append(clean)
    return blocks


###############################################################################
# digit dictionaries for pseudodigit parsing
_DIGITS = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "."]
_SQZ_DIGITS = {"@": "0",
               "A": "1", "B": "2", "C": "3", "D": "4", "E": "5",
               "F": "6", "G": "7", "H": "8", "I": "9",
               "a": "-1", "b": "-2", "c": "-3", "d": "-4", "e": "-5",
               "f": "-6", "g": "-7", "h": "-8", "i": "-9"}
_DIF_DIGITS = {"%": "0",
               "J": "1", "K": "2", "L": "3", "M": "4", "N": "5",
               "O": "6", "P": "7", "Q": "8", "R": "9",
               "j": "-1", "k": "-2", "l": "-3", "m": "-4", "n": "-5",
               "o": "-6", "p": "-7", "q": "-8", "r": "-9"}
_DUP_DIGITS = {"S": "1", "T": "2", "U": "3", "V": "4", "W": "5",
               "X": "6", "Y": "7", "Z": "8", "s": "9"}
###############################################################################


def _detect_format(dataline):
    '''
    Detects and returns digit format:
    0  Normal
    1  Pseudodigits
    2  Coordinate list (XY..XY)
    -1 Error
    '''
    # check for coordinate list first
    # values may be signed, and writers commonly indent pair lines
    xy_re = re.compile(r'^\s*[+-]?[0-9.]+(?:[eE][+-]?\d+)?\s*,\s*'
                       r'[+-]?[0-9.]+(?:[eE][+-]?\d+)?')
    if re.search(xy_re, dataline):
        return 2

    # regexp to find & skip the first value of line, that never begins
    # with a pseudodigit in any format
    firstvalue_re = re.compile(
        r"(\s)*([+-]?\d+\.?\d*|[+-]?\.\d+)([eE][+-]?\d+)?(\s)*")

    index = firstvalue_re.match(dataline).end()
    if index is None:
        return -1
    try:
        firstchar = dataline[index:index+1]
    except IndexError:
        return -1
    # detect the format from the first character of the second value in line
    if firstchar in _SQZ_DIGITS:
        return 1
    if firstchar in _DIF_DIGITS:
        return 1
    if firstchar in _DUP_DIGITS:
        return 1
    return 0


def _parse_affn_pac(datalines):
    ''' Parses datalines that do NOT contain any pseudodigits  '''

    # regexp explained:
    # -values may be delimited with whitespace, comma, or sign (+/-)
    # -may contain leading + or -
    # -base number may have decimal separator (.) or not
    # -if decimal separator is present, number can be given without leading
    #  zero (.1234) or decimals (123.)
    # -exponent (E/e) may be present
    value_re = re.compile(r"(\s|,)*([+-]?\d+\.?\d*|[+-]?\.\d+)([eE][+-]?\d+)?")

    data = []
    for dataline in datalines:
        linedata = []
        for match in value_re.finditer(dataline):
            base = match.group(2)
            exp = match.group(3)
            try:
                value = float(base + (exp if exp is not None else ""))
            except ValueError:
                warn(f"Data parsing failed at line: {dataline}")
                return None
            linedata.append(value)
        if len(linedata) > 1:
            data.extend(linedata[1:])  # ignore first column (X value)
    return data


def _append_value(data, value_to_append, isdif):
    '''
    Helper function for _finish_value: actual data push happens
    here based on isdif flag (direct value or difference from prev)
    '''
    if isdif:
        data.append(data[-1] + value_to_append)
    else:
        data.append(value_to_append)


def _finish_value(valuestr, currentmode, prev_value_to_append, data):
    '''
    Helper for _parse_pseudo:
    -Processes value in prev_value_to_append based on currentmode
    -Parses and returns next value_to_append for next round
    '''

    try:
        # squeeze format: number is added to data array as such
        if currentmode == 1:
            if prev_value_to_append is not None:
                _append_value(data, *prev_value_to_append)
            new_value_to_append = (float(valuestr), False)  # isdif=False
            return new_value_to_append, True
        # diff format: number is diff from previous entry
        elif currentmode == 2:
            if prev_value_to_append is not None:
                _append_value(data, *prev_value_to_append)
            new_value_to_append = (float(valuestr), True)  # isdif=True
            return new_value_to_append, True
        # duplicate format: push previous number (or diff) n times
        elif currentmode == 3:
            if prev_value_to_append is None:
                warn("Parse error: DUP entry without preceding value")
                return None, False
            dupcount = int(valuestr)
            for _i in range(dupcount):
                _append_value(data, *prev_value_to_append)
            new_value_to_append = None
            return new_value_to_append, True
        else:  # first value
            return None, True
    except ValueError:
        return None, False


def _parse_pseudo(datalines):
    ''' Parses datalines packed with pseudodigits  '''

    # regexp to find the first value of line, that never begins
    # with a pseudodigit (exponents are not allowed here)
    firstvalue_re = re.compile(r"(\s)*([+-]?\d+\.?\d*|[+-]?\.\d+)")

    data = []
    currentmode = 0
    valuestr = []
    skip_checkpoint = False

    # since the DUP mode entries may duplicate previous number n times,
    # we can't directly append newly read values to data. Instead, store
    # them here until next value is read:
    value_to_append = None

    for dataline in datalines:
        if not dataline:
            continue

        # ignore first value of line (X value)
        firstmatch = firstvalue_re.match(dataline)
        y_valuestring = dataline[firstmatch.end():]

        first_of_line = True

        # parse rest one char at a time
        for char in y_valuestring.strip():

            # char is digit = continues the current number
            if char in _DIGITS:
                valuestr.append(char)
                continue

            # char is pseudodigit = begin new number
            try:
                valuechar = _SQZ_DIGITS[char]
                newmode = 1
            except KeyError:
                try:
                    valuechar = _DIF_DIGITS[char]
                    newmode = 2
                except KeyError:
                    try:
                        valuechar = _DUP_DIGITS[char]
                        newmode = 3
                    except KeyError:
                        warn(f"Unknown pseudo-digit: {char} at line: {dataline}")
                        return None

            # finish previous number
            valuestr = "".join(valuestr)

            # before updating value_to_append, store the mode of last value
            # actually appended to data.
            # this is needed for the DIF checkpoint removal below
            previous_is_dif = False
            if currentmode == 2:
                previous_is_dif = True
            elif currentmode == 3 and value_to_append[1]:
                previous_is_dif = True

            if not skip_checkpoint:
                # append number in value_to_append to data array if exists,
                # and update value_to_append
                value_to_append, success = _finish_value(valuestr,
                                                         currentmode,
                                                         value_to_append,
                                                         data)
                if not success:
                    warn(f"Data parsing failed at line: {dataline}")
                    return None

            # in DIF mode last of line is same than the first of next line
            # (= checkpoint). In such case raise a flag that this number
            # is to be skipped in _finish_value
            skip_checkpoint = first_of_line and previous_is_dif

            # init new number
            currentmode = newmode
            valuestr = [valuechar]
            first_of_line = False

    # read ended. finish last number:
    if not skip_checkpoint:
        valuestr = "".join(valuestr)
        value_to_append, success = _finish_value(valuestr,
                                                 currentmode,
                                                 value_to_append,
                                                 data)
        if not success:
            warn("Data parsing failed at last dataline")
            return None

    # append last number now in value_to_append:
    if value_to_append is not None:
        _append_value(data, *value_to_append)

    return data


# variable list of a data table header, e.g. (X++(R..R)) or (F2++(Y..Y)):
# the first symbol is the abscissa, the second the dependent variable
_VARIABLE_LIST_RE = re.compile(
    r"\(\s*([A-Za-z][A-Za-z0-9]*)\s*\+\+\s*\(\s*([A-Za-z][A-Za-z0-9]*)\s*\.\.")


def _parse_variable_list(headerline):
    '''
    Finds the variable symbols declared by a data table header, e.g.
    "(X++(R..R))" gives ("X", "R") and "(F2++(Y..Y))" gives ("F2", "Y").
    Returns (None, None) when the header declares no variable list.
    '''
    match = _VARIABLE_LIST_RE.search(headerline)
    if match is None:
        return (None, None)
    return match.group(1), match.group(2)


def _parse_xy_xy(datalines):
    '''
    Parses datalines in coordinate list format (XY..XY),
    where each line contains comma-separated X,Y pairs.
    '''
    pts = []
    xy_pair_re = re.compile(
        r"([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)\s*,\s*"
        r"([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)"
    )
    for dataline in datalines:
        for match in xy_pair_re.finditer(dataline):
            x = float(match.group(1))
            y = float(match.group(2))
            pts.append([x, y])
    return [pts]


def _parse_data(datastring):
    '''
    Creates numpy array from datalines
    '''
    datalines = datastring.split("\n")
    headerline = datalines[0]

    # the dependent variable is named by the header's variable list; headers
    # that declare none are assumed to hold the real component
    datatype = _parse_variable_list(headerline)[1]
    if datatype is None:
        datatype = "R"

    datalines = datalines[1:]  # get rid of the header line (e.g. (X++(Y..Y)))
    if not datalines:
        return None  # a table declared with no values, e.g. an empty PEAKTABLE

    # Determine the parsing strategy from the declared header format.
    # Headers like (X++(Y..Y)) or (X++(R..R)) declare AFFN data; commas in
    # such data are either decimal separators or value delimiters, never
    # XY-pair separators. Only (XY..XY) and (X..XY) headers use coordinate
    # pair semantics.
    is_affn_header = '++' in headerline
    is_xy_pair_header = headerline in ('(XY..XY)', '(X..XY)')

    if is_affn_header:
        # AFFN declared: commas are value delimiters, parse directly
        mode = _detect_format(datalines[0])
        if mode == 1:
            data = _parse_pseudo(datalines)
        else:
            data = _parse_affn_pac(datalines)
    elif is_xy_pair_header and headerline == '(XY..XY)':
        # Coordinate list: commas separate X and Y. Never apply comma-to-dot
        # normalization here — the format is intrinsically ambiguous with
        # European decimal writing, and preserving XY delimiters takes
        # priority. European decimals are handled by the (X..XY) header.
        data = _parse_xy_xy(datalines)
    elif is_xy_pair_header and headerline == '(X..XY)':
        # Mixed format: X values then XY pairs; commas may be European
        # decimal separators in the X values and XY pair data
        header_end = datastring.find('\n')
        data_part = datastring[header_end:] if header_end != -1 else datastring
        if ',' in data_part and '.' not in data_part:
            datastring = re.sub(r'(\d),(\d)', r'\1.\2', datastring)
            datalines = datastring.split("\n")[1:]
        mode = _detect_format(datalines[0])
        if mode == 2:
            data = _parse_xy_xy(datalines)
        else:
            data = _parse_affn_pac(datalines)
    else:
        # (X..XY) or undeclared format: detect and parse
        mode = _detect_format(datalines[0])
        if mode == 2 and headerline != '(X++(Y..Y))':
            data = _parse_xy_xy(datalines)
        else:
            # apply comma-to-dot for non-XY data
            header_end = datastring.find('\n')
            data_part = datastring[header_end:] if header_end != -1 else datastring
            if ',' in data_part and '.' not in data_part:
                datastring = re.sub(r'(\d),(\d)', r'\1.\2', datastring)
                datalines = datastring.split("\n")[1:]
            mode = _detect_format(datalines[0])
            if mode == 1:
                data = _parse_pseudo(datalines)
            elif mode == 0:
                data = _parse_affn_pac(datalines)
            elif mode == 2:
                data = _parse_xy_xy(datalines)
            else:
                return None

    if data is None:
        return None
    return np.asarray(data, dtype="float64"), datatype


def get_is_ntuples(dic):
    '''
    Determine data class from dic: XYDATA or NTUPLES
    '''
    is_ntuples = False  # default is XYDATA
    try:
        dataclass = dic["DATACLASS"][0]
        if dataclass.strip() == "NTUPLES":
            is_ntuples = True
    except KeyError:
        pass
    return is_ntuples


def find_factor(dic, symbol):
    '''
    Helper to find the scaling factor of the given symbol (e.g. "R", "I"
    or "Y") from the NTUPLES ##SYMBOL= and ##FACTOR= records, whose
    comma-separated entries correspond by position.
    Returns None if the factor cannot be determined.
    '''
    try:
        symbols = [s.strip() for s in dic["SYMBOL"][0].split(",")]
        factors = [s.strip() for s in dic["FACTOR"][0].split(",")]
        return float(factors[symbols.index(symbol)])
    except (KeyError, IndexError, ValueError):
        return None


def find_yfactors(dic):
    '''
    Helper to find yfactors from NTUPLES format.
    Returns YFactors in tuple with order (R,I)
    '''
    return (find_factor(dic, "R"), find_factor(dic, "I"))


def getdataarray(dic, show_all_data=False):
    '''
    Main function for data array parsing, input is the
    raw dictionary from _readrawdic

    Parameters
    ----------
    dic : dict
        Raw dictionary from _readrawdic.
    show_all_data : bool
        If True and data is NTUPLES, return all data arrays as a dict
        with keys 'real' and 'imaginary', each containing a list of arrays.
    '''

    data = None

    is_ntuples = get_is_ntuples(dic)

    if is_ntuples:  # NTUPLES
        valuelist = None
        try:
            valuelist = dic["DATATABLE"]
        except KeyError:
            is_ntuples = False
            warn("NTUPLES without DATA TABLEs. Trying XYDATA instead...")

        if valuelist:
            rdatalist = []
            idatalist = []
            for value in valuelist:
                parseret = _parse_data(value)
                if parseret is None:
                    return None
                data, datatype = parseret
                # scale by the factor of this table's own dependent
                # symbol: an (X++(I..I)) table gets I's factor, an
                # (X++(R..R)) table R's, so factors can never be
                # applied to the wrong component
                factor = find_factor(dic, datatype)
                if factor is None:
                    warn("NTUPLES: no FACTOR found for symbol %s, "
                         "data not scaled" % datatype)
                else:
                    data = data * factor
                if datatype == "I":
                    idatalist.append(data)
                else:
                    rdatalist.append(data)
            if show_all_data:
                data = {'real': rdatalist, 'imaginary': idatalist}
            else:
                if len(rdatalist) > 1:
                    warn("NTUPLES: multiple real arrays, returning first one only")
                if len(idatalist) > 1:
                    warn("NTUPLES: multiple imaginary arrays, \
                         returning first one only")
                if rdatalist:
                    if idatalist:
                        data = [rdatalist[0], idatalist[0]]
                    else:
                        data = rdatalist[0]
                else:
                    if idatalist:
                        data = [None, idatalist[0]]

    if data is None:  # XYDATA
        try:
            valuelist = dic["XYDATA"]
            if len(valuelist) > 1:
                warn("Multiple XYDATA arrays in JCAMP-DX file, \
                     returning first one only")
            parseret = _parse_data(valuelist[0])
            if parseret is None:
                return None
            data, datatype = parseret
        except KeyError:
            warn("XYDATA not found ")

    if data is None:  # PEAKTABLE
        try:
            valuelist = dic["PEAKTABLE"]
            if len(valuelist) > 1:
                warn("Multiple PEAKTABLE arrays in JCAMP-DX file, "
                     "returning first one only")
            parseret = _parse_data(valuelist[0])
            if parseret is not None:
                data, datatype = parseret
        except KeyError:
            pass

    if data is None:  # XYPOINTS
        try:
            valuelist = dic["XYPOINTS"]
            if len(valuelist) > 1:
                warn("Multiple XYPOINTS arrays in JCAMP-DX file, "
                     "returning first one only")
            parseret = _parse_data(valuelist[0])
            if parseret is not None:
                data, datatype = parseret
        except KeyError:
            pass

    if data is None:
        return None

    # apply YFACTOR to data if available
    # (NTUPLES data was already scaled per-table above)
    if not is_ntuples:
        if data.ndim == 3 and data.shape[-1] == 2:
            # (XY..XY) pairs carry their own X values, which XFACTOR scales;
            # YFACTOR scales only the Y column
            for column, factorkey in ((0, "XFACTOR"), (1, "YFACTOR")):
                try:
                    factor = float(dic[factorkey][0])
                    data[..., column] = data[..., column] * factor
                except (ValueError, IndexError):
                    warn(f"{factorkey} not applied, parsing failed")
                except KeyError:
                    pass
        else:
            try:
                yfactor = float(dic["YFACTOR"][0])
                data = data * yfactor
            except (ValueError, IndexError):
                warn("YFACTOR not applied, parsing failed")
            except KeyError:
                pass

    return data


def read(filename, show_all_data=False, read_err=None, as_complex=False):
    """
    Read JCAMP-DX file

    Parameters
    ----------
    filename : str
        File to read from.
    show_all_data : bool
        If True and data is NTUPLES, return all data arrays as a dict
        with keys 'real' and 'imaginary', each containing a list of
        numpy arrays. If False (default), return only the first real
        and imaginary arrays.
    read_err : str, optional
        Error handling for character decoding, passed to open() as the
        ``errors`` parameter. Valid values include 'strict', 'ignore',
        'replace', 'backslashreplace', etc. Defaults to None which uses
        'replace'.
    as_complex : bool, optional
        If True and data is NTUPLES with separate real and imaginary
        arrays, return a single complex128 array instead of a list
        [real, imaginary]. Default is False for backward compatibility.

    Returns
    -------
    dic : dict
        Dictionary of parameters. In the case of multiple data sections in
        file, parameters of first NMR SPECTRUM or NMR FID are read to base
        level and others are stored under _datatype_<DATATYPE> keys in the
        dictionary.
    data : ndarray or dict
        Array of NMR data, or a list of NMR data arrays in order
        [real, imaginary]. When show_all_data=True and data is NTUPLES,
        a dict with keys 'real' and 'imaginary' is returned. When
        as_complex=True and data has separate R/I, a complex128 array.
    """

    if os.path.isfile(filename) is not True:
        raise OSError("file %s does not exist" % (filename))

    # first read everything (including data array) to "raw" dictionary,
    # in which data values are read as raw strings including whitespace
    # and newlines
    dic = _readrawdic(filename, read_err)

    # select the relevant data section, taking the first section of the most
    # preferred DATATYPE that yields data. Non-typed sections are tried
    # because the DATATYPE label is sometimes missing, and multidimensional
    # spectra come last so that a file offering both a 1D and an nD spectrum
    # keeps returning the 1D one.
    data = None
    correctdic = None
    for datatype in ("NMRSPECTRUM", "NMRFID", "NA", "NDNMRSPECTRUM"):
        for subdic in dic.get("_datatype_" + datatype, []):
            data = getdataarray(subdic, show_all_data)
            if data is not None:
                correctdic = subdic
                break
        if data is not None:
            break

    if data is None:
        warn("no data found either in XYDATA or NTUPLES format")

    if correctdic is not None:
        # remove correct dic from subdic lists:
        for key, subdiclist in dic.items():
            for subdic in subdiclist:
                if subdic is correctdic:
                    subdiclist = [d for d in subdiclist if d is not correctdic]
                    dic[key] = subdiclist

        # clean correct dic:
        # remove data tables
        try:
            del correctdic["XYDATA"]
        except KeyError:
            pass
        try:
            del correctdic["DATATABLE"]
        except KeyError:
            pass

        # push correct dic entries to base level of main dic
        for key, valuelist in correctdic.items():
            dic[key] = valuelist

    # clean main dic from possible empty entries
    dic = {key: value for key, value in dic.items() if value}

    if as_complex and isinstance(data, list) and len(data) == 2:
        data = get_complex_array(data)

    return dic, data


def _find_abscissa_symbol(dic, symbols):
    '''
    Finds which of an NTUPLES variable list's symbols is the abscissa.
    One dimensional data calls it X, while multidimensional data names its
    dimensions instead. In that case the innermost, i.e. last, independent
    variable is the abscissa of every page: a file declaring (F1, F2, Y)
    stores (F2++(Y..Y)) data tables, one per value of F1.
    Returns None if it cannot be identified.
    '''
    if "X" in symbols:
        return "X"

    try:
        vartypes = [s.strip().upper() for s in dic["VARTYPE"][0].split(",")]
        independent = [symbol for symbol, vartype in zip(symbols, vartypes)
                       if vartype == "INDEPENDENT"]
        if independent:
            return independent[-1]
    except (KeyError, IndexError):
        pass

    # no VARTYPE to go on: fall back to the abscissa a data table declares,
    # available while reading but not after read() strips the tables
    try:
        return _parse_variable_list(dic["DATATABLE"][0].split("\n", 1)[0])[0]
    except (KeyError, IndexError):
        return None


def _find_firstx_lastx(dic):
    '''
    Helper for guess_udic: seeks firstx and lastx for
    sweep calculation. Also returns True/False if the
    data was in ppm.
    '''

    firstx = None
    lastx = None
    unitx = None
    isppm = False  # default to Hz

    # determine data class:
    is_ntuples = get_is_ntuples(dic)

    if is_ntuples:
        # first check which column is the abscissa:
        index_x = None
        try:
            symbols = dic["SYMBOL"][0].split(",")
            symbols = [s.strip() for s in symbols]
            index_x = symbols.index(_find_abscissa_symbol(dic, symbols))
        except (KeyError, IndexError, ValueError):
            warn("Cannot found X column on NTUPLES")
        if index_x is not None:
            try:
                firsts = dic["FIRST"][0].split(",")
                firsts = [s.strip() for s in firsts]
                firstx = float(firsts[index_x])
            except (KeyError, IndexError, ValueError):
                warn("Cannot parse FIRST (X) on NTUPLES")
            try:
                lasts = dic["LAST"][0].split(",")
                lasts = [s.strip() for s in lasts]
                lastx = float(lasts[index_x])
            except (KeyError, IndexError, ValueError):
                warn("Cannot parse LAST (X) on NTUPLES")
            try:
                units = dic["UNITS"][0].split(",")
                units = [s.strip() for s in units]
                unitx = units[index_x]
            except (KeyError, IndexError, ValueError):
                warn("Cannot parse UNITS (X) on NTUPLES")

    # XYDATA (try always if not yet found)
    if firstx is None and lastx is None:
        try:
            firstx = float(dic["FIRSTX"][0])
        except ValueError:
            warn('Cannot parse "FIRSTX"')
        except KeyError:
            warn('No "FIRSTX" in file')
        try:
            lastx = float(dic["LASTX"][0])
        except ValueError:
            warn('Cannot parse "LASTX"')
        except KeyError:
            warn('No "LASTX" in file')
    if unitx is None:
        try:
            unitx = dic["XUNITS"][0]
        except KeyError:
            warn('No "XUNITS" in file')

    # flag ppm data
    if unitx is not None:
        isppm = unitx.upper() == "PPM"

    return firstx, lastx, isppm


def get_complex_array(data):
    """
    Combine separate real and imaginary arrays into a single complex array.

    JCAMP-DX FID data are read as two separate arrays for real and imaginary
    parts. This function returns them combined as a single complex128 array.

    Parameters
    ----------
    data : list of ndarray
        List of two arrays [real, imaginary].

    Returns
    -------
    complexdata : ndarray or None
        Complex array, or None if data is not a list of two compatible arrays.
    """
    if not isinstance(data, list) or len(data) != 2:
        warn("data is not list of arrays [real, imag]")
        return None

    real, imag = data
    if (not isinstance(real, np.ndarray) or not isinstance(imag, np.ndarray)
            or real.shape != imag.shape):
        warn("data arrays must be ndarrays of the same shape")
        return None

    complexdata = np.empty(len(real), dtype='complex128')
    complexdata.real = real[:]
    complexdata.imag = imag[:]
    return complexdata


def guess_udic(dic, data):
    """
    Guess parameters of universal dictionary from dic, data pair.

    Parameters
    ----------
    dic : dict
        Dictionary of JCAMP-DX parameters.
    data : ndarray
        Array of NMR data.

    Returns
    -------
    udic : dict
        Universal dictionary of spectral parameters.
    """

    # create an empty universal dictionary
    udic = fileiobase.create_blank_udic(1)

    # the universal dictionary is one dimensional, so for multidimensional
    # data it can only describe the direct dimension
    try:
        if int(dic["NUMDIM"][0]) > 1:
            warn("Multidimensional data: udic describes the direct "
                 "dimension only")
    except (KeyError, IndexError, ValueError):
        pass

    # update default values
    # "label"
    try:
        label_value = dic[".OBSERVENUCLEUS"][0].replace("^", "")
        udic[0]["label"] = label_value
    except KeyError:
        # sometimes INSTRUMENTAL PARAMETERS is used:
        try:
            label_value = dic["INSTRUMENTALPARAMETERS"][0].replace("^", "")
            udic[0]["label"] = label_value
        except KeyError:
            pass

    # "obs"
    obs_freq = None
    try:
        obs_freq = float(dic[".OBSERVEFREQUENCY"][0])
        udic[0]["obs"] = obs_freq
    except ValueError:
        warn('Cannot parse ".OBSERVE FREQUENCY"')
    except KeyError:
        pass

    # "size"
    npoints = None
    if isinstance(data, dict):
        pages = data.get("real") or data.get("imaginary") or [None]
        data = pages[0]
    if isinstance(data, list):
        for elem in data:
            if elem is not None:
                npoints = len(elem)
                break
    elif data is not None:
        npoints = len(data)
    if npoints is not None:
        udic[0]["size"] = npoints
    else:
        warn('No data, cannot set udic size')

    # detect FID vs processed
    is_processed = None
    try:
        datatype = dic["DATATYPE"][0]
        if datatype.strip().upper().replace(" ", "") == "NMRFID":
            is_processed = False
        else:
            is_processed = True
    except KeyError:
        pass
    if is_processed is None:
        try:
            ntuples = dic["NTUPLES"][0]
            if "FID" in ntuples.strip().upper():
                is_processed = False
            else:
                is_processed = True
        except KeyError:
            pass
    if is_processed is None:
        is_processed = True

    # "sw" and "car"
    firstx, lastx, isppm = _find_firstx_lastx(dic)

    if firstx is not None and lastx is not None:
        if is_processed:
            # ppm data: convert to Hz
            if isppm:
                if obs_freq:
                    firstx = firstx * obs_freq
                    lastx = lastx * obs_freq
                else:
                    firstx, lastx = (None, None)
                    warn('Data is in ppm but base frequency is unknown, '
                         'cannot set udic spectral width')
            if firstx is not None and lastx is not None:
                udic[0]["sw"] = abs(lastx - firstx)
                udic[0]["car"] = (lastx + firstx) / 2
        else:
            # FID: sw = npoints / acquisition_time (Nyquist)
            if npoints:
                aqtime = lastx - firstx
                if aqtime > 0:
                    udic[0]["sw"] = npoints / aqtime
    else:
        warn('No data ranges found from JCAMP, cannot set udic sw')

    # "time" and "freq"
    udic[0]["freq"] = is_processed
    udic[0]["time"] = not is_processed

    # "complex" — JCAMP R&I are separate arrays, so default False
    udic[0]["complex"] = False
    if not isinstance(data, list):
        if hasattr(data, 'dtype') and data.dtype == "complex128":
            udic[0]["complex"] = True

    return udic
