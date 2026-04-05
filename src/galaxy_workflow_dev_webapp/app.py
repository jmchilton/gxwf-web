"""FastAPI application for Galaxy workflow development operations."""

import os
from contextlib import asynccontextmanager
from typing import (
    Any,
    List,
    Optional,
)

from fastapi import (
    FastAPI,
    HTTPException,
    Query,
)
from galaxy.tool_util.workflow_state.workflow_tree import (
    discover_workflows,
    WorkflowInfo,
)

from .contents import (
    delete_contents,
    is_workflow_file,
    read_contents,
    rename_contents,
    write_contents,
)
from .models import (
    ContentsModel,
    RenameRequest,
    WorkflowEntry,
    WorkflowIndex,
)
from .operations import (
    get_tool_info,
    run_clean,
    run_lint,
    run_roundtrip,
    run_to_format2,
    run_to_native,
    run_validate,
)

_tool_info = None
_directory: Optional[str] = None
_workflows: Optional[List[WorkflowInfo]] = None


def configure(directory: str):
    """Set the workflow directory before app startup."""
    global _directory
    _directory = os.path.abspath(directory)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _tool_info, _workflows
    if _directory is None:
        raise RuntimeError("No directory configured — call configure() before starting the app")
    if not os.path.isdir(_directory):
        raise RuntimeError(f"Directory does not exist: {_directory}")
    _tool_info = get_tool_info()
    _workflows = discover_workflows(_directory)
    yield


app = FastAPI(
    title="Galaxy Workflow Development API",
    description="Validate, lint, clean, and convert Galaxy workflows against tool definitions",
    version="0.1.0",
    lifespan=lifespan,
)


def _get_workflow(workflow_path: str) -> WorkflowInfo:
    assert _workflows is not None
    for wf in _workflows:
        if wf.relative_path == workflow_path:
            return wf
    raise HTTPException(404, f"Workflow not found: {workflow_path}")


@app.get("/workflows", response_model=WorkflowIndex)
async def list_workflows():
    """List all discovered workflows in the configured directory."""
    assert _workflows is not None and _directory is not None
    return WorkflowIndex(
        directory=_directory,
        workflows=[
            WorkflowEntry(
                relative_path=wf.relative_path,
                format=wf.format,
                category=wf.category,
            )
            for wf in _workflows
        ],
    )


@app.post("/workflows/refresh", response_model=WorkflowIndex)
async def refresh_workflows():
    """Re-discover workflows from the configured directory."""
    global _workflows
    assert _directory is not None
    _workflows = discover_workflows(_directory)
    return await list_workflows()


@app.get("/workflows/{workflow_path:path}/validate")
async def validate_workflow(
    workflow_path: str,
    strict: bool = False,
    connections: bool = False,
    mode: str = "pydantic",
    allow: List[str] = Query(default=[]),
    deny: List[str] = Query(default=[]),
) -> Any:
    """Validate a workflow's tool state against tool definitions."""
    wf = _get_workflow(workflow_path)
    return run_validate(
        wf,
        _tool_info,
        strict=strict,
        connections=connections,
        mode=mode,
        allow=allow,
        deny=deny,
    )


@app.get("/workflows/{workflow_path:path}/clean")
async def clean_workflow(
    workflow_path: str,
    preserve: List[str] = Query(default=[]),
    strip: List[str] = Query(default=[]),
) -> Any:
    """Report stale tool state keys in a workflow."""
    wf = _get_workflow(workflow_path)
    return run_clean(
        wf,
        _tool_info,
        preserve=preserve,
        strip=strip,
    )


@app.get("/workflows/{workflow_path:path}/to-format2")
async def to_format2(
    workflow_path: str,
) -> Any:
    """Convert a native workflow to format2 with schema-aware state."""
    wf = _get_workflow(workflow_path)
    result = run_to_format2(wf, _tool_info)
    if result is None:
        raise HTTPException(422, "Workflow skipped (legacy encoding)")
    return result.report


@app.get("/workflows/{workflow_path:path}/to-native")
async def to_native(
    workflow_path: str,
) -> Any:
    """Convert a format2 workflow to native Galaxy format with schema-aware state."""
    wf = _get_workflow(workflow_path)
    return run_to_native(wf, _tool_info)


@app.get("/workflows/{workflow_path:path}/roundtrip")
async def roundtrip_workflow(
    workflow_path: str,
) -> Any:
    """Run round-trip validation (native -> format2 -> native)."""
    wf = _get_workflow(workflow_path)
    return run_roundtrip(wf, _tool_info)


def _maybe_refresh_workflows(rel_path: str) -> None:
    """Refresh workflow cache when a workflow-shaped file was mutated."""
    global _workflows
    if _directory is not None and is_workflow_file(rel_path):
        _workflows = discover_workflows(_directory)


@app.get("/api/contents", response_model=ContentsModel)
async def read_root_contents(content: int = 1) -> ContentsModel:
    """Read configured directory root (Jupyter Contents API)."""
    assert _directory is not None
    return read_contents(_directory, "", include_content=bool(content))


@app.get("/api/contents/{path:path}", response_model=ContentsModel)
async def read_path_contents(path: str, content: int = 1) -> ContentsModel:
    """Read a file or directory by relative path."""
    assert _directory is not None
    return read_contents(_directory, path, include_content=bool(content))


@app.put("/api/contents/{path:path}", response_model=ContentsModel)
async def write_path_contents(path: str, model: ContentsModel) -> ContentsModel:
    """Save (create-or-replace) a file or create a directory."""
    assert _directory is not None
    result = write_contents(_directory, path, model)
    _maybe_refresh_workflows(path)
    return result


@app.delete("/api/contents/{path:path}", status_code=204)
async def delete_path_contents(path: str) -> None:
    """Delete a file or directory (recursive)."""
    assert _directory is not None
    delete_contents(_directory, path)
    _maybe_refresh_workflows(path)


@app.patch("/api/contents/{path:path}", response_model=ContentsModel)
async def rename_path_contents(path: str, body: RenameRequest) -> ContentsModel:
    """Rename/move a file or directory."""
    assert _directory is not None
    result = rename_contents(_directory, path, body.path)
    _maybe_refresh_workflows(path)
    _maybe_refresh_workflows(body.path)
    return result


@app.get("/workflows/{workflow_path:path}/lint")
async def lint_workflow(
    workflow_path: str,
    strict: bool = False,
    allow: List[str] = Query(default=[]),
    deny: List[str] = Query(default=[]),
) -> Any:
    """Lint a workflow (structural + tool state validation)."""
    wf = _get_workflow(workflow_path)
    return run_lint(
        wf,
        _tool_info,
        strict=strict,
        allow=allow,
        deny=deny,
    )
