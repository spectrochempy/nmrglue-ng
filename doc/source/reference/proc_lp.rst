.. _proc_lp:

nmrglue.proc_lp
===============

.. automodule:: nmrglue.process.proc_lp

Use ``ng.proc_lp.lp()`` to extrapolate a trace or each row of a 2D
array, ``lp2d()`` for two-dimensional extrapolation, and
``lp_model()`` to estimate signal parameters from a trace.
``cadzow()`` denoises a trace or each row of a 2D array.

User Functions
--------------

.. autosummary::
    :toctree: generated/

    lp
    lp_svd
    lp_qr
    lp_cho
    lp_tls
    lp2d
    cadzow
    lp_model



Developer Functions
-------------------

.. _notes:

See :ref:`developer-linear-prediction-notes` for algorithm references and
validation guidance for the helpers below.

.. autosummary::
    :toctree: generated/

    lp_1d
    extrapolate_2d
    make_lp2d_Dd
    cadzow_single
    root2damp
    root2freq
    cof2amp
    cof2phase
    make_D
    make_little_d
    make_Dd
    make_mirror
    find_lpc
    find_lpc_svd
    pinv_diagsvd
    find_lpc_qr
    find_lpc_cholesky
    find_lpc_tls
    find_lpc_fb
    find_lpc_bf
    find_lproots_hsvd
    find_roots
    find_coeff
    reverse_filter
    fix_roots
    extrapolate
