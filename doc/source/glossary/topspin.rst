Bruker TopSpin parameter mapping
================================

This page relates common Bruker TopSpin acquisition and processing parameters
to fields in nmrglue's universal dictionary. It is based on the current Bruker
reader implementation and TopSpin's *Processing Commands and Parameters*
manual. These mappings are specific to this format; similarly named
parameters in other formats need not have identical semantics.

Acquisition parameters are stored in ``acqus``, ``acqu2s``, etc.; processed
parameters are stored in ``procs``, ``proc2s``, etc. In nmrglue,
``udic[ndim - 1]`` is normally the direct dimension and corresponds to
``acqus``/``procs``; preceding array dimensions correspond to ``acqu2s`` /
``proc2s`` and so on.

The table summarizes the current Bruker reader mapping. The processed column
applies when processed parameters are selected (for example, with
``pdata=True`` when reading processed data). With ``pdata=None``, the reader
preserves historical behavior: acquisition parameters take priority when both
sets are present.

.. list-table:: Bruker TopSpin parameters used to infer universal dictionary fields
   :header-rows: 1
   :widths: 14 22 22 42

   * - Universal field
     - TopSpin acquisition parameters
     - TopSpin processed parameters
     - nmrglue behavior
   * - ``size``
     - ``TD`` (acquisition storage)
     - ``SI``
     - Set from actual returned array shape.
   * - ``sw`` (direct)
     - ``SW_h``
     - ``SW_p``
     - Stored in Hz.
   * - ``sw`` (indirect)
     - ``SW * SFO1``
     - ``SW_p``
     - ``SW`` is converted from ppm to Hz.
   * - ``obs``
     - ``SFO1``
     - ``SF``
     - Stored in MHz.
   * - ``car``
     - ``O1``
     - ``OFFSET``, ``SF``, ``SW_p``
     - Acquisition uses ``O1`` when no processed reference applies. For a processed axis, ``car`` is derived from the first-point offset.
   * - ``label``
     - ``NUC1``
     - ``AXNUC``
     - Nucleus or axis label.
   * - ``complex``
     - ``AQ_mod`` on direct axis
     - —
     - Acquisition mode helps identify direct-axis real or complex data.
   * - ``encoding``
     - ``FnMODE`` on indirect axes
     - —
     - Acquisition mode maps to encodings such as States or TPPI.

For a selected processed axis, TopSpin defines ``OFFSET`` as the ppm value of
the first spectral point. nmrglue converts this to the universal dictionary's
``car`` convention using ``OFFSET * SF - SW_p / 2``. Consequently, do not
interpret ``OFFSET`` as interchangeable with ``car``: the fields use different
reference conventions and units. See the Bruker reader's
:func:`nmrglue.fileio.bruker.guess_udic` documentation and the TopSpin manual
for further details.

Related guides: :doc:`../tutorials/reading`,
:doc:`../tutorials/universal-dictionaries`,
:doc:`../tutorials/unit-conversion`, and :doc:`../tutorials/processing`.
