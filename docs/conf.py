# Configuration file for the Sphinx documentation builder.

project = 'ml-hpi'
copyright = '2024-2025, Matthew Ballance'
author = 'Matthew Ballance'

extensions = [
    'myst_parser',
]

source_suffix = {
    '.rst': 'restructuredtext',
    '.md':  'markdown',
}

templates_path = ['_templates']
exclude_patterns = [
    '_build',
    'Thumbs.db',
    '.DS_Store',
    'ml_hpi_whitepaper_outline.md',   # outline is not a doc page
]

html_theme = 'furo'
html_static_path = ['_static']

html_title = 'ml-hpi'

myst_enable_extensions = [
    'colon_fence',
    'deflist',
    'tasklist',
]
