# Developing

## Setup

```console
$ make setup-venv
```

## Running tests

```console
$ make test
```

## Linting

```console
$ make lint
$ make mypy
```

## Formatting

```console
$ make format
```

## Building the docs

```console
$ make docs
```

`make docs` regenerates `docs/_static/openapi.json` from the current FastAPI
app and then runs `sphinx-build -W` (warnings as errors). Use `make
docs-serve` to build and serve on `http://127.0.0.1:8001`.
