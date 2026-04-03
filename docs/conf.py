import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))

import galaxy_workflow_dev_webapp as project_module  # noqa: E402

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinxarg.ext",
]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
    "pydantic": ("https://docs.pydantic.dev/latest/", None),
}

templates_path = ["_templates"]
source_suffix = [".rst", ".md"]
master_doc = "index"

project = "galaxy-workflow-development-webapp"
copyright = "2025-2026, Galaxy Project and Community"

version = project_module.__version__
release = project_module.__version__

exclude_patterns = ["_build"]
pygments_style = "sphinx"

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
htmlhelp_basename = "galaxyworkflowdevwebappdoc"
