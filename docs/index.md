# galaxy-workflow-development-webapp

**galaxy-workflow-development-webapp** is a thin FastAPI shell over
`galaxy.tool_util.workflow_state`. It exposes two HTTP surfaces — a workflow
operations API (validate, clean, lint, to-format2, to-native, roundtrip) and a
Jupyter Contents API-compatible file layer — as the HTTP backing for frontend
Galaxy workflow development tooling.

::::{grid} 2

:::{grid-item-card} Getting Started
:link: installation
:link-type: doc

Install the webapp and point it at a workflow directory.
:::

:::{grid-item-card} Architecture
:link: architecture
:link-type: doc

Module map, request flow, and where this fits in the `workflow_state` stack.
:::

:::{grid-item-card} Workflow Operations
:link: workflow_ops
:link-type: doc

validate / clean / lint / to-format2 / to-native / roundtrip reference.
:::

:::{grid-item-card} Contents API
:link: contents_api
:link-type: doc

Jupyter Contents API compatibility layer: CRUD, checkpoints, conflict
detection.
:::

:::{grid-item-card} API Reference
:link: api
:link-type: doc

Auto-generated OpenAPI reference for every endpoint.
:::

:::{grid-item-card} CLI
:link: cli
:link-type: doc

`galaxy-workflow-dev` command-line reference.
:::

::::

```{toctree}
:maxdepth: 2
:caption: User Guide
:hidden:

Installation <installation>
Architecture <architecture>
Workflow Operations <workflow_ops>
Contents API <contents_api>
CLI <cli>
```

```{toctree}
:maxdepth: 2
:caption: Reference
:hidden:

API Reference <api>
```

```{toctree}
:maxdepth: 2
:caption: Development
:hidden:

Developing <developing>
Contributing <contributing>
History <history>
```

## Galaxy ecosystem

- [Galaxy Project](https://galaxyproject.org) — open-source platform for
  data-intensive research
- [gxformat2](https://github.com/galaxyproject/gxformat2) — Format 2 reference
  library; converters invoked by `workflow_state`
- [IWC](https://iwc.galaxyproject.org) — Intergalactic Workflow Commission,
  the workflow corpus the webapp is typically pointed at
- [Planemo](https://planemo.readthedocs.io) — CLI for Galaxy tool and
  workflow development
