nmrglue.spinsolve
=================

.. automodule:: nmrglue.fileio.spinsolve

Pass a Magritek Spinsolve experiment directory to ``ng.spinsolve.read()``
to read a 1D FID or spectrum as ``(dic, data)``. Set ``specfile`` to select
a specific file, for example ``specfile="spectrum_processed.1d"``.
Otherwise the reader selects the first available file in this order:
``nmr_fid.dx``, ``data.1d``, ``fid.1d``, ``spectrum.1d``,
``spectrum_processed.1d``.

The two ``spectrum*.1d`` files contain frequency-domain data. Use the
coordinates stored in ``dic["spectrum"]["xaxis"]`` when plotting either
spectrum. The reader accepts ``.1d`` and complex JCAMP-DX ``.dx`` data;
CSV and ``.pt1`` exports, writing, and low-memory reading are unsupported.

User Information
----------------

User Functions
^^^^^^^^^^^^^^

.. autosummary::
    :toctree: generated/

    read
    guess_udic



Developer Information
---------------------

See :ref:`developer-spinsolve-format-notes` for storage and parser details.

Developer Functions
^^^^^^^^^^^^^^^^^^^

These functions are typically not used directly by users.  Developers who want
fine control over Spinsolve files may be interested in these functions.

.. autosummary::
    :toctree: generated/

    parse_spinsolve_par_line
    get_udic_from_acqu_dict
    get_udic_from_jcamp_dict
