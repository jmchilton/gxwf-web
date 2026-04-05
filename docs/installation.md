# Installation

## From PyPI

```console
$ pip install galaxy-workflow-development-webapp
```

## From source (development)

```console
$ git clone https://github.com/jmchilton/galaxy-workflow-development-webapp
$ cd galaxy-workflow-development-webapp
$ make setup-venv
```

`make setup-venv` uses `uv sync` when available, otherwise falls back to a
plain `python3 -m venv .venv` + editable install.

## Running against a workflow corpus

The webapp scans a directory for `.ga`, `.gxwf.yml`, and `.gxwf.yaml` files
on startup. Point it at any directory — a clone of
[IWC](https://github.com/galaxyproject/iwc) is the typical target:

```console
$ galaxy-workflow-dev ~/projects/repositories/iwc
```

Re-scan after external edits with `POST /workflows/refresh` (mutations via
the Contents API re-scan automatically).

## Tool cache

Validation resolves tool definitions via
`galaxy.tool_util.workflow_state.cache.build_tool_info`, which caches Tool
Shed 2.0 responses. Pass `cache_dir` to `build_tool_info` (or set the
environment variable respected by that module) to control cache location.

## Local Galaxy / gxformat2 pinning

During active development on the `wf_tool_state` Galaxy branch and the
gxformat2 `abstraction_applications` branch, `[tool.uv.sources]` in
`pyproject.toml` pins editable installs from worktree paths:

```toml
[tool.uv.sources]
galaxy-tool-util = { path = "/path/to/galaxy/branch/wf_tool_state/packages/tool_util", editable = true }
galaxy-tool-util-models = { path = "...", editable = true }
galaxy-util = { path = "...", editable = true }
gxformat2 = { path = "/path/to/gxformat2/branch/abstraction_applications", editable = true }
```

Update or remove these entries once the upstream branches merge.
