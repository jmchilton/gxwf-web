================================
galaxy-workflow-development-webapp
================================

FastAPI service for Galaxy workflow validation, linting, cleaning, and format conversion.

Point the service at a directory containing Galaxy workflow files and interact with
them via a REST API backed by ``galaxy-tool-util``'s workflow state operations.

Installation
------------

::

    pip install galaxy-workflow-development-webapp

Or for development::

    make setup-venv

Usage
-----

::

    galaxy-workflow-dev /path/to/workflows

This starts a local server at ``http://127.0.0.1:8000``. The API discovers
``.ga`` workflow files in the target directory and exposes them at
``/workflows/{relative_path}/`` with the following operations:

- ``POST /workflows/{path}/validate`` — validate tool state against tool definitions
- ``POST /workflows/{path}/clean`` — clean stale tool state keys
- ``POST /workflows/{path}/lint`` — structural + tool state linting
- ``POST /workflows/{path}/export-format2`` — export native workflow to format2
- ``POST /workflows/{path}/roundtrip`` — round-trip validation (native → format2 → native)
- ``GET /workflows`` — list all discovered workflows
- ``POST /workflows/refresh`` — re-discover workflows

Development
-----------

::

    make setup-venv
    make lint
    make test

See ``CONTRIBUTING.rst`` for details.
