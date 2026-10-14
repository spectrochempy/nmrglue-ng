import sys, os
from datetime import date

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.mathjax',
    'numpydoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.intersphinx',
    'myst_nb',
    'sphinx_design',
]

# Numpy autodoc attributes
numpydoc_show_class_members = False

intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'numpy': ('https://numpy.org/doc/stable/', None),
    'scipy': ('https://docs.scipy.org/doc/scipy/', None),
    'matplotlib': ('https://matplotlib.org/stable/', None),
    'ipython': ('https://ipython.readthedocs.io/en/stable/', None),
}

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'myst-nb',
}

# Keep English as the source language. The French build uses the gettext
# catalogs under ``locale/`` and selects the language with ``-D language=fr``.
language = 'en'
locale_dirs = ['locale/']
gettext_compact = False

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = 'nmrglue-ng'
copyright = '2010-%s, Jonathan J. Helmus and contributors' % date.today().year

# The default replacements for |version| and |release|, also used in various
# other places throughout the built documents.
import nmrglue
version = nmrglue.__version__
# The full version, including alpha/beta/rc tags.
release = version

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = []
if tags.has('fastdocs'):
    exclude_patterns.extend(['reference/**'])
    suppress_warnings = ['toc.excluded', 'ref.doc', 'ref.ref']

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'sphinx_book_theme'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
html_theme_options = {
    'repository_url': 'https://github.com/spectrochempy/nmrglue-ng',
    'use_repository_button': True,
    'use_issues_button': True,
    'home_page_in_toc': False,
    'show_navbar_depth': 2,
    'collapse_navbar': True,
    'navbar_start': ['global-brand.html'],
    'navbar_center': ['navbar-nav'],
    'navbar_end': ['global-actions.html'],
    'header_links_before_dropdown': 5,
    'article_header_end': [],
    'footer_content_items': [
        'copyright.html',
        'last-updated.html',
        'extra-footer.html',
    ],
}

html_context = {
    'rtd_layout': os.environ.get('READTHEDOCS') == 'True',
}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
html_title = 'nmrglue-ng documentation'

# A shorter title for the navigation bar.  Default is the same as html_title.
html_short_title = 'nmrglue-ng'

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']
html_css_files = ['nmrglue-ng.css']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
html_sidebars = {
    'index': [],
    '**': [
        'icon-links.html',
        'sbt-sidebar-nav.html',
    ],
}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'nmrgluedoc'

# Execute MyST-NB tutorials during normal documentation builds and reuse the
# jupyter-cache result when the notebook source and dependencies are unchanged.
nb_execution_mode = 'cache'
nb_execution_cache_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', 'build', '.jupyter_cache')
)
nb_execution_timeout = 120

if os.environ.get('READTHEDOCS') == 'True':
    nb_execution_excludepatterns = [
        'examples/agilent2pipe_3d.md',
        'examples/bruker2pipe_3d.md',
        'examples/process_pipe_3d.md',
    ]


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'nmrglue.tex', 'nmrglue Documentation',
   'Jonathan J. Helmus', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'nmrglue', 'nmrglue Documentation',
     ['Jonathan J. Helmus'], 1)
]

# ----------------
# Autosummary
#-----------------

import glob

#autosummary_generate = glob.glob("reference/*.rst")
autosummary_generate = not tags.has('fastdocs')

# -----------------------------------------------------------------------------
# Source code links
# -----------------------------------------------------------------------------

import inspect
from os.path import relpath, dirname

for name in ['sphinx.ext.linkcode', 'linkcode', 'numpydoc.linkcode']:
    try:
        __import__(name)
        extensions.append(name)
        break
    except ImportError:
        pass
else:
    print("NOTE: linkcode extension not found -- no links to source generated")

def linkcode_resolve(domain, info):
    """
    Determine the URL corresponding to Python object
    """
    if domain != 'py':
        return None

    modname = info['module']
    fullname = info['fullname']

    submod = sys.modules.get(modname)
    if submod is None:
        return None

    obj = submod
    for part in fullname.split('.'):
        try:
            obj = getattr(obj, part)
        except:
            return None

    try:
        fn = inspect.getsourcefile(obj)
    except:
        fn = None
    if not fn:
        return None

    try:
        source, lineno = inspect.findsource(obj)
    except:
        lineno = None

    if lineno:
        linespec = "#L%d" % (lineno + 1)
    else:
        linespec = ""

    fn = relpath(fn, start=dirname(nmrglue.__file__))

    return f"https://github.com/spectrochempy/nmrglue-ng/blob/master/nmrglue/{fn}{linespec}"
