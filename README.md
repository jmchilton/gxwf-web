# galaxy-workflow-development-webapp

HTTP layer over [`galaxy.tool_util.workflow_state`][wfstate] for Galaxy
workflow development tooling. A thin FastAPI shell exposing two API surfaces:

- `/workflows/{path}/{op}` — validate, clean, lint, to-format2, to-native,
  roundtrip. Each route delegates to a `*_single()` entry point in
  `workflow_state`.
- `/api/contents/...` — Jupyter Contents API-compatible CRUD over the workflow
  directory (read/write/untitled/rename/delete + checkpoints +
  `If-Unmodified-Since` conflict detection).

It's the backing service that frontend tooling — today a browser client,
tomorrow [IWC][iwc] and a VSCode extension — uses to exercise the
`workflow_state` stack over HTTP without linking to Galaxy in-process.

[wfstate]: https://github.com/galaxyproject/galaxy
[iwc]: https://github.com/galaxyproject/iwc

## Architecture at a glance

```{mermaid}
flowchart LR
    Client[Frontend / VSCode / curl]
    subgraph Webapp[galaxy-workflow-development-webapp]
        Contents[/api/contents/...]
        Ops[/workflows/path/op]
        Operations[operations.py]
    end
    WfState[galaxy.tool_util.workflow_state<br/>*_single entry points]
    ToolShed[Tool Shed 2.0<br/>ToolShedGetToolInfo]

    Client --> Contents
    Client --> Ops
    Ops --> Operations
    Operations --> WfState
    WfState --> ToolShed
```

Two surfaces, one process. `operations.py` is the only bridge into
`workflow_state`; `contents.py` is a self-contained Jupyter-compatible file
layer that does not touch `workflow_state` at all.

## API surface overview

| Endpoint | Purpose | Delegates to |
| --- | --- | --- |
| `GET /workflows/{path}/validate` | Validate tool state vs. tool definitions | `validate_single` |
| `GET /workflows/{path}/clean` | Report stale tool state keys | `clean_single` |
| `GET /workflows/{path}/lint` | Structural + tool state lint | `lint_single` |
| `GET /workflows/{path}/to-format2` | Native → format2 (schema-aware) | `export_single` |
| `GET /workflows/{path}/to-native` | format2 → native (schema-aware) | `convert_to_native_stateful` |
| `GET /workflows/{path}/roundtrip` | native → format2 → native diff | `roundtrip_single` |
| `GET /workflows` | List discovered workflows | `discover_workflows` |
| `POST /workflows/refresh` | Re-discover workflows | `discover_workflows` |
| `GET/PUT/POST/PATCH/DELETE /api/contents/{path}` | Jupyter Contents API CRUD | `contents.py` |
| `GET/POST/DELETE /api/contents/{path}/checkpoints[/{id}]` | Checkpoint snapshots | `contents.py` |

See `docs/workflow_ops.md` and `docs/contents_api.md` for per-endpoint detail.

## Install / run

```console
$ pip install galaxy-workflow-development-webapp
$ galaxy-workflow-dev /path/to/workflows
```

Serves on `http://127.0.0.1:8000`. The target directory is scanned for `.ga`
and format2 workflows on startup; `POST /workflows/refresh` rescans.

Dump the OpenAPI schema without starting the server:

```console
$ galaxy-workflow-dev --output-schema openapi.json
```

For development against a local `wf_tool_state` Galaxy worktree and gxformat2
`abstraction_applications` branch (both pinned via `[tool.uv.sources]` in
`pyproject.toml`):

```console
$ make setup-venv
```

## Development

```console
$ make setup-venv
$ make lint
$ make test
$ make docs
```

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the full contributor workflow.

## Relationship to the broader workflow_state stack

The webapp is an HTTP frontend over deliverables built on the Galaxy
`wf_tool_state` branch. Related projects:

- [`galaxy.tool_util.workflow_state`][wfstate] — the `*_single()` entry points
  this webapp wraps. Also exposes the `gxwf-*` CLI
  (`gxwf-state-validate`, `gxwf-state-clean`, `gxwf-roundtrip-validate`, ...).
- [`gxformat2`](https://github.com/galaxyproject/gxformat2) — workflow format
  definition and converters invoked by `workflow_state`.
- [`iwc`](https://github.com/galaxyproject/iwc) — the workflow corpus this
  webapp is typically pointed at.
- [Tool Shed 2.0](https://github.com/galaxyproject/tool_shed_2_0) — resolved
  tool metadata source used during validation.
