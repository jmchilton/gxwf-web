# Workflow Operations

The `/workflows/{path}/{op}` surface is a thin HTTP skin over the
`*_single()` entry points in `galaxy.tool_util.workflow_state`. Every route
resolves `{path}` to a `WorkflowInfo` discovered at startup, delegates to a
single library function, and returns the resulting report verbatim.

`{path}` is the relative path (under the configured root) of a `.ga`,
`.gxwf.yml`, or `.gxwf.yaml` file.

## Quickstart

Validate an IWC workflow via `curl`:

```console
$ gxwf-web ~/projects/iwc &
$ curl "http://127.0.0.1:8000/workflows/workflows/variant-calling/variant-calling/variant-calling.ga/validate?strict=true"
```

The same workflow, round-tripped through format2 and back:

```console
$ curl "http://127.0.0.1:8000/workflows/workflows/variant-calling/variant-calling/variant-calling.ga/roundtrip"
```

## Endpoint reference

### `GET /workflows/{path}/validate`

Validate tool state against resolved Tool Shed tool definitions.

| Param | Type | Default | Meaning |
| --- | --- | --- | --- |
| `strict` | bool | `false` | Treat warnings as errors |
| `connections` | bool | `false` | Also validate input connections |
| `mode` | string | `"pydantic"` | Validator backend (`pydantic`, ...) |
| `allow` | list[str] | `[]` | Keys to allow despite stale-key policy |
| `deny` | list[str] | `[]` | Keys to deny (override allow list) |

Returns `SingleValidationReport`. Delegates to `validate_single`. CLI
analogue: `gxwf-state-validate`.

### `GET /workflows/{path}/clean`

Report stale tool state keys that would be removed by a clean.

| Param | Type | Default | Meaning |
| --- | --- | --- | --- |
| `preserve` | list[str] | `[]` | Keys never stripped |
| `strip` | list[str] | `[]` | Keys always stripped |

Returns `SingleCleanReport`. Delegates to `clean_single`. CLI analogue:
`gxwf-state-clean`.

### `GET /workflows/{path}/lint`

Structural + tool-state linting.

| Param | Type | Default | Meaning |
| --- | --- | --- | --- |
| `strict` | bool | `false` | Treat warnings as errors |
| `allow` | list[str] | `[]` | Stale-key allow list |
| `deny` | list[str] | `[]` | Stale-key deny list |

Returns `SingleLintReport`. Delegates to `lint_single`. CLI analogue:
`gxwf-lint`.

### `GET /workflows/{path}/to-format2`

Convert a native workflow (`.ga`) to Format 2 (YAML) with schema-aware state
promotion. Returns `ExportSingleResult.report`; **422** if the workflow uses
a legacy encoding that `export_single` declines to convert. Delegates to
`export_single`. CLI analogue: `gxwf-to-format2`.

### `GET /workflows/{path}/to-native`

Convert a Format 2 workflow to native Galaxy `.ga` representation via the
stateful converter. Returns `ToNativeResult`. Delegates to
`convert_to_native_stateful`. CLI analogue: `gxwf-to-native`.

### `GET /workflows/{path}/roundtrip`

Run a native → format2 → native roundtrip and return a diff report. Returns
`SingleRoundTripReport`. Delegates to `roundtrip_single`. CLI analogue:
`gxwf-roundtrip-validate`.

### `GET /workflows`

List all discovered workflows (no body, returns `WorkflowIndex`).

### `POST /workflows/refresh`

Re-run `discover_workflows` on the configured directory. Also triggered
automatically by any Contents API mutation that touches a workflow-shaped
file.

## Stale key policies

`allow` / `deny` / `preserve` / `strip` are all passed through to
`StaleKeyPolicy` factory methods (`for_validate` and `for_clean`). See the
`galaxy.tool_util.workflow_state.stale_keys` module for the full semantics.

## Why GET and not POST?

These routes are idempotent read operations — they never mutate the
workflow file. `POST /workflows/refresh` is the one exception because it
mutates server-side cache state.
