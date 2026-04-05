import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))

import galaxy_workflow_dev_webapp as project_module  # noqa: E402

# -- General configuration ---------------------------------------------

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinxarg.ext",
    "sphinx_design",
    "sphinxcontrib.mermaid",
    "sphinxcontrib.openapi",
]

myst_enable_extensions = [
    "colon_fence",
    "deflist",
]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
    "pydantic": ("https://docs.pydantic.dev/latest/", None),
    "fastapi": ("https://fastapi.tiangolo.com/", None),
}

templates_path = ["_templates"]
source_suffix = [".rst", ".md"]
master_doc = "index"

project = "galaxy-workflow-development-webapp"
copyright = "2025-2026, Galaxy Project and Community"

version = project_module.__version__
release = project_module.__version__

exclude_patterns = ["_build"]
pygments_style = "default"

# -- Options for HTML output -------------------------------------------

html_theme = "pydata_sphinx_theme"

html_theme_options = {
    "logo": {
        "text": "galaxy-workflow-development-webapp",
    },
    "header_links_before_dropdown": 6,
    "pygments_light_style": "default",
    "navbar_align": "left",
    "show_prev_next": True,
    "footer_start": ["copyright"],
    "icon_links": [
        {
            "name": "GitHub",
            "url": "https://github.com/jmchilton/galaxy-workflow-development-webapp",
            "icon": "fa-brands fa-github",
        },
        {
            "name": "Galaxy Project",
            "url": "https://galaxyproject.org",
            "icon": "fa-solid fa-globe",
        },
    ],
    "secondary_sidebar_items": ["page-toc", "sourcelink"],
    "navigation_with_keys": True,
}

html_static_path = ["_static"]
html_css_files = ["css/galaxy.css"]
html_title = "galaxy-workflow-development-webapp"
html_short_title = "workflow-dev-webapp"

htmlhelp_basename = "galaxyworkflowdevwebappdoc"
