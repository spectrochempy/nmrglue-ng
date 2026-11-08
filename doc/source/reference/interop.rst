nmrglue.interop
===============

.. currentmodule:: nmrglue.interop

See :doc:`../tutorials/interop` for the relationship between readers, the
universal dictionary and interop, and for a worked example.

The :ref:`interop-profile-table` lists the available selectors. For array
layouts, signs, scales and calibration rules, see :doc:`interop-conventions`.

.. toctree::
    :hidden:

    interop-conventions

Result types and diagnostics
----------------------------

.. autosummary::
    :toctree: generated/

    ReadResult
    NormalizedAcquisition
    Axis
    Reference
    Component
    Diagnostic
    DIAGNOSTIC_CONTEXT_SCHEMA

Select a reader by profile
--------------------------

.. autosummary::
    :toctree: generated/

    read

.. _interop-profile-table:

Supported profiles
------------------

Pass a dataset directory for Bruker and Agilent detection. For SIMPSON,
JEOL JDF and NMRPipe, detection inspects the file header. Set
``profile=`` for an ambiguous source or to select a specific reader.
Additional keyword arguments go to that reader.

Auto-detected Bruker 1D pdata uses ``scale_data=False``. Explicit
``profile="bruker-pdata"`` and the specialized reader use ``True`` by default.
Set the option explicitly when comparing results.

The selector normally matches ``ReadResult.format``. The ``bruker-ser``
reader reports a QF or States-TPPI result profile according to the input.
``normalize()`` dispatches on the result profile and raises ``ValueError``
when no normalizer is registered.

.. list-table::
   :header-rows: 1
   :widths: 25 12 33 30

   * - Selector
     - Detection
     - Input and reader options
     - Normalization
   * - ``agilent-fid``
     - Explicit
     - Complex 1D FID
     - Yes
   * - ``agilent-fid-storage``
     - Automatic
     - Stored scalar FID traces
     - Unavailable
   * - ``agilent-states-2d``
     - Explicit
     - Descriptive 2D States traces
     - Unavailable
   * - ``bruker-fid``
     - Automatic
     - Raw 1D FID
     - Qualified QSIM/DQD. Choose whether to remove the digital filter.
   * - ``bruker-pdata``
     - Automatic
     - Processed 1D spectrum
     - Complete calibrated grid
   * - ``bruker-pdata-2d``
     - Explicit
     - Complete processed 2D spectrum
     - Qualified four-plane grid
   * - ``bruker-pdata-2d-storage``
     - Automatic
     - Stored processed 2D planes
     - Unavailable
   * - ``bruker-ser``
     - Explicit
     - Qualified QF or States-TPPI SER
     - Unavailable
   * - ``bruker-ser-storage``
     - Automatic
     - Stored scalar SER traces
     - Unavailable
   * - ``jcampdx-fid-1d``
     - Explicit
     - Complex 1D NTUPLES FID
     - Explicit ``conjugation``
   * - ``jcampdx-spectrum-1d``
     - Explicit
     - Regular real 1D XYDATA spectrum
     - Yes
   * - ``jcampdx-spectrum-2d``
     - Explicit
     - Real 2D NTUPLES spectrum
     - Yes
   * - ``jeol-2d-storage``
     - Automatic
     - Stored tiled 2D JDF sections
     - Qualified time-domain data with explicit ``conjugation``
   * - ``jeol-fid-1d``
     - Automatic
     - Complex 1D JDF FID
     - Explicit ``conjugation``
   * - ``nmrml-1d``
     - Explicit
     - Raw FID or processed 1D spectrum. See the :doc:`1D options <../nmrml_1d>`.
     - Explicit ``conjugation`` for raw data
   * - ``nmrml-2d-spectrum``
     - Explicit
     - Real processed 2D plane. Set ``shape``, ``indirect_axis``, ``storage_order`` and ``axis_endpoint``.
     - Yes
   * - ``nmrml-raw-2d``
     - Explicit
     - Raw complex 2D traces. Set ``direct_point_count``.
     - Qualified echo/anti-echo with ``indirect_dwell_s`` and ``confirm_adjacent_pairs=True``
   * - ``nmrpipe-1d``
     - Automatic
     - Complete processed 1D spectrum
     - Yes
   * - ``nmrpipe-2d``
     - Explicit
     - Complete real processed 2D spectrum
     - Yes
   * - ``nmrpipe-2d-storage``
     - Automatic
     - Stored 2D traces in file order
     - Complete supported grids. Time and mixed domains require ``confirm_time_grid=True``.
   * - ``simpson-fid-1d``
     - Automatic
     - Complex 1D TEXT or BINARY FID
     - Explicit ``conjugation``
   * - ``simpson-fid-2d``
     - Automatic
     - Complex 2D TEXT or BINARY FID
     - Explicit ``conjugation``
   * - ``simpson-spectrum-1d``
     - Automatic
     - Complex 1D TEXT or BINARY spectrum
     - Yes
   * - ``simpson-spectrum-2d``
     - Automatic
     - Complex 2D TEXT or BINARY spectrum
     - Yes

Read stored planes and traces
-----------------------------

These readers expose decoded storage and source metadata. See
:doc:`interop-conventions` for the distinction between storage and physical axes.

.. autosummary::
    :toctree: generated/

    read_bruker_pdata_2d_storage
    read_bruker_ser_storage
    read_agilent_fid_storage
    read_nmrpipe_2d_storage
    read_jeol_2d_storage

Read raw acquisitions
---------------------

.. autosummary::
    :toctree: generated/

    read_agilent_fid
    read_agilent_states_2d
    read_bruker_fid
    read_bruker_ser
    read_jeol_fid
    read_simpson_fid
    read_simpson_fid_2d
    read_jcampdx_fid

Read processed spectra and exchange files
-----------------------------------------

.. autosummary::
    :toctree: generated/

    read_bruker_pdata
    read_bruker_pdata_2d
    read_nmrpipe_1d
    read_nmrpipe_2d
    read_nmrml_1d
    read_jcampdx_1d
    read_simpson_spectrum
    read_simpson_spectrum_2d
    read_jcampdx_2d
    read_nmrml_2d
    read_nmrml_raw_2d

Normalize a supported result
----------------------------

The package attribute ``nmrglue.interop.normalize`` is the generic function.
If you previously used ``import nmrglue.interop.normalize as normalizers``
to access the submodule, import the specific functions you need from
``nmrglue.interop.normalize`` or from ``nmrglue.interop``.

.. autosummary::
    :toctree: generated/

    normalize
    normalize_agilent_fid
    normalize_bruker_fid
    normalize_jeol_fid
    normalize_simpson_fid
    normalize_simpson_fid_2d
    normalize_simpson_spectrum
    normalize_simpson_spectrum_2d
    normalize_jeol_2d
    normalize_bruker_pdata
    normalize_bruker_pdata_2d
    normalize_nmrpipe_1d
    normalize_nmrpipe_2d
    normalize_nmrml_1d
    normalize_jcampdx_1d
    normalize_jcampdx_2d
    normalize_jcampdx_fid
    normalize_nmrml_2d
    normalize_nmrml_raw_2d

Export an acquisition
---------------------

.. autosummary::
    :toctree: generated/

    write_readresult_nmrpipe
