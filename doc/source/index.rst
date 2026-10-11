nmrglue-ng documentation
========================

:Release: |version|
:Date: |today|

``nmrglue-ng`` is an independent continuation of the historical
`nmrglue <https://github.com/jjhelmus/nmrglue>`_ project for reading, writing,
converting, processing, and analysing NMR data in Python. The distribution name
is ``nmrglue-ng``; the Python import remains compatible with existing nmrglue
code:

.. code-block:: python

    import nmrglue as ng

This prototype keeps the existing reference material available while testing a
tutorial-first organization with Sphinx Book Theme and executable MyST-NB
notebooks.

Start with :doc:`getting-started/index` for installation and orientation, then
follow the :doc:`tutorials/index` for executable walkthroughs.

.. only:: not fastdocs

   Use :doc:`reference/index` for the API details behind the tutorials.

.. only:: fastdocs

   This fast documentation build omits the generated API reference. Run the full
   HTML build when API pages and links are needed.

.. toctree::
    :maxdepth: 2
    :caption: Documentation

    getting-started/index
    tutorials/index
    how-to/index
    about/index

.. only:: not fastdocs

   .. toctree::
       :maxdepth: 2
       :caption: API reference

       reference/index
