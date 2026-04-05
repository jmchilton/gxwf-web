# Architecture

This page is the mental-model doc — read it first if you want to understand
why the webapp looks the way it does and how it fits into the broader
`workflow_state` stack.

## Module map

Six modules, ~850 LoC total, two disjoint API surfaces sharing one process.

```{mermaid}
flowchart TD
    subgraph App[app.py — FastAPI routes]
        WR[workflow routes<br/>/workflows/path/op]
        CR[contents routes<br/>/api/contents/...]
    end

    Ops[operations.py<br/>run_validate / run_clean / run_lint<br/>run_to_format2 / run_to_native / run_roundtrip]
    Contents[contents.py<br/>read/write/untitled/rename/delete<br/>+ checkpoints + safe-path guard]
    Models[models.py<br/>Pydantic request/response]

    WR --> Ops
    CR --> Contents
    WR -.-> Models
    CR -.-> Models

    subgraph WfState[galaxy.tool_util.workflow_state]
        Single[validate_single / clean_single / lint_single<br/>export_single / roundtrip_single<br/>convert_to_native_stateful]
        Cache[cache.build_tool_info]
        TSInfo[ToolShedGetToolInfo]
    end

    Ops --> Single
    Ops --> Cache
    Cache --> TSInfo

    TS[Tool Shed 2.0<br/>tool metadata API]
    TSInfo --> TS
```

`contents.py` is entirely self-contained and does not touch `workflow_state`.
`operations.py` is the only bridge into the `workflow_state` package — every
workflow operation route is a one-line delegation through it.

## Request flow: `GET /workflows/{path}/validate`

```{mermaid}
sequenceDiagram
    participant C as Client
    participant R as FastAPI route
    participant G as _get_workflow
    participant O as run_validate
    participant V as validate_single
    participant T as ToolShedGetToolInfo
    participant S as Tool Shed 2.0

    C->>R: GET /workflows/my-wf.ga/validate?strict=1
    R->>G: resolve workflow_path
    G-->>R: WorkflowInfo
    R->>O: run_validate(wf, tool_info, ...)
    O->>V: validate_single(path, tool_info, policy=...)
    V->>T: get_tool_info(tool_id, version)
    T->>S: HTTP GET tool metadata
    S-->>T: ToolDefinition
    T-->>V: resolved tool info
    V-->>O: SingleValidationReport
    O-->>R: report
    R-->>C: JSON(SingleValidationReport)
```

`tool_info` is built once during FastAPI's `lifespan` startup via
`build_tool_info()` and reused for every request. Discovered `WorkflowInfo`
entries are cached at startup too and refreshed via `POST /workflows/refresh`
or automatically when the Contents API mutates a workflow-shaped file.

## Request flow: Contents API write with conflict detection

```{mermaid}
sequenceDiagram
    participant C as Client
    participant R as FastAPI PUT /api/contents/path
    participant W as write_contents
    participant FS as Filesystem

    C->>R: PUT body=ContentsModel, If-Unmodified-Since: <HTTP-date>
    R->>R: parse If-Unmodified-Since
    R->>W: write_contents(dir, path, model, expected_mtime)
    W->>FS: resolve_safe_path (reject escape / ignored component)
    W->>FS: stat existing file
    alt disk_mtime > expected_mtime + 1s
        W-->>R: HTTPException(409)
        R-->>C: 409 Conflict
    else no conflict
        W->>FS: write bytes
        W->>R: read_contents (fresh model)
        R->>R: _maybe_refresh_workflows
        R-->>C: 200 ContentsModel
    end
```

## Endpoint → delegate → report model

| Endpoint | `operations.py` fn | `workflow_state` callable | Report model |
| --- | --- | --- | --- |
| `/validate` | `run_validate` | `validate_single` | `SingleValidationReport` |
| `/clean` | `run_clean` | `clean_single` | `SingleCleanReport` |
| `/lint` | `run_lint` | `lint_single` | `SingleLintReport` |
| `/to-format2` | `run_to_format2` | `export_single` | `ExportSingleResult.report` |
| `/to-native` | `run_to_native` | `convert_to_native_stateful` | `ToNativeResult` |
| `/roundtrip` | `run_roundtrip` | `roundtrip_single` | `SingleRoundTripReport` |

Every workflow route has one job: resolve the path to a `WorkflowInfo`, pass
it through `operations.py`, return the report verbatim. Most report types
live in `workflow_state._report_models`; conversion- and roundtrip-specific
types (`ExportSingleResult`, `ToNativeResult`, `SingleRoundTripReport`) are
defined in their respective submodules. The webapp adds no new types on top
of the delegated return values.

## How this fits in the workflow_state deliverables

The broader `workflow_state` project (see `PROBLEM_AND_GOAL.md` in the
project vault) defines deliverables D1–D10:

- **D1–D8** — the library-level pieces that live in
  `galaxy.tool_util.workflow_state`: validation, cleaning, export to format2,
  stateful to-native conversion, lint, roundtrip, stale-key policies, Tool
  Shed 2.0 integration.
- **D9** — VSCode extension.
- **D10** — IWC workflow development surface.

The webapp is **not itself a deliverable** — it is the HTTP surface over
D1–D8, and it enables D9 and D10 indirectly by letting a browser/VSCode
frontend drive the stack without linking Galaxy in-process.

## Relationship to the `wf_tool_state` branch

The webapp currently pins two editable sources via `[tool.uv.sources]` in
`pyproject.toml`:

- `galaxy-tool-util`, `galaxy-tool-util-models`, `galaxy-util` →
  `/Users/jxc755/projects/worktrees/galaxy/branch/wf_tool_state/packages/...`
  (the Galaxy `wf_tool_state` feature branch where `workflow_state` lives).
- `gxformat2` →
  `/Users/jxc755/projects/worktrees/gxformat2/branch/abstraction_applications`
  (the gxformat2 branch with schema-aware abstraction applications).

This is a temporary arrangement and **will go stale once both branches
merge**. When that happens, pin versioned releases from PyPI and drop this
section.
