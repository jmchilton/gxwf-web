"""FastAPI application for Galaxy workflow development operations."""

import os
from contextlib import asynccontextmanager
from email.utils import parsedate_to_datetime
from typing import (
    List,
    Optional,
)

from fastapi import (
    FastAPI,
    Header,
    HTTPException,
    Query,
)
from galaxy.tool_util.workflow_state.workflow_tree import (
    discover_workflows,
    WorkflowInfo,
)

from .contents import (
    create_checkpoint,
    create_untitled,
    delete_checkpoint,
    delete_contents,
    is_workflow_file,
    list_checkpoints,
    read_contents,
    rename_contents,
    restore_checkpoint,
    write_contents,
)
from galaxy.tool_util.workflow_state._report_models import (
    SingleCleanReport,
    SingleLintReport,
    SingleValidationReport,
)
from galaxy.tool_util.workflow_state.export_format2 import SingleExportReport
from galaxy.tool_util.workflow_state.roundtrip import SingleRoundTripReport
from galaxy.tool_util.workflow_state.to_native_stateful import ToNativeResult

from .models import (
    CheckpointModel,
    ContentsModel,
    CreateRequest,
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
) -> SingleValidationReport:
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
) -> SingleCleanReport:
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
) -> SingleExportReport:
    """Convert a native workflow to format2 with schema-aware state."""
    wf = _get_workflow(workflow_path)
    result = run_to_format2(wf, _tool_info)
    if result is None:
        raise HTTPException(422, "Workflow skipped (legacy encoding)")
    return result.report


@app.get("/workflows/{workflow_path:path}/to-native")
async def to_native(
    workflow_path: str,
) -> ToNativeResult:
    """Convert a format2 workflow to native Galaxy format with schema-aware state."""
    wf = _get_workflow(workflow_path)
    return run_to_native(wf, _tool_info)


@app.get("/workflows/{workflow_path:path}/roundtrip")
async def roundtrip_workflow(
    workflow_path: str,
) -> SingleRoundTripReport:
    """Run round-trip validation (native -> format2 -> native)."""
    wf = _get_workflow(workflow_path)
    return run_roundtrip(wf, _tool_info)


def _maybe_refresh_workflows(rel_path: str) -> None:
    """Refresh workflow cache when a workflow-shaped file was mutated."""
    global _workflows
    if _directory is not None and is_workflow_file(rel_path):
        _workflows = discover_workflows(_directory)


@app.get("/api/contents", response_model=ContentsModel)
async def read_root_contents(
    content: int = 1,
    format: Optional[str] = None,
) -> ContentsModel:
    """Read configured directory root (Jupyter Contents API)."""
    assert _directory is not None
    return read_contents(_directory, "", include_content=bool(content), format_override=format)


# Checkpoint routes MUST come before the generic /api/contents/{path:path} routes
# so FastAPI matches the literal `/checkpoints` suffix first.


@app.get("/api/contents/{path:path}/checkpoints", response_model=List[CheckpointModel])
async def list_file_checkpoints(path: str) -> List[CheckpointModel]:
    """List checkpoints for a file (Jupyter Contents API)."""
    assert _directory is not None
    return list_checkpoints(_directory, path)


@app.post("/api/contents/{path:path}/checkpoints", response_model=CheckpointModel, status_code=201)
async def create_file_checkpoint(path: str) -> CheckpointModel:
    """Create a checkpoint snapshot of a file."""
    assert _directory is not None
    return create_checkpoint(_directory, path)


@app.post("/api/contents/{path:path}/checkpoints/{checkpoint_id}", status_code=204)
async def restore_file_checkpoint(path: str, checkpoint_id: str) -> None:
    """Restore a file from a stored checkpoint."""
    assert _directory is not None
    restore_checkpoint(_directory, path, checkpoint_id)
    _maybe_refresh_workflows(path)


@app.delete("/api/contents/{path:path}/checkpoints/{checkpoint_id}", status_code=204)
async def delete_file_checkpoint(path: str, checkpoint_id: str) -> None:
    """Delete a stored checkpoint."""
    assert _directory is not None
    delete_checkpoint(_directory, path, checkpoint_id)


@app.get("/api/contents/{path:path}", response_model=ContentsModel)
async def read_path_contents(
    path: str,
    content: int = 1,
    format: Optional[str] = None,
) -> ContentsModel:
    """Read a file or directory by relative path."""
    assert _directory is not None
    return read_contents(_directory, path, include_content=bool(content), format_override=format)


@app.post("/api/contents", response_model=ContentsModel)
async def create_root_untitled(body: CreateRequest) -> ContentsModel:
    """Create an untitled file or directory in the configured root."""
    assert _directory is not None
    result = create_untitled(_directory, "", body.type, body.ext)
    _maybe_refresh_workflows(result.path)
    return result


@app.post("/api/contents/{path:path}", response_model=ContentsModel)
async def create_path_untitled(path: str, body: CreateRequest) -> ContentsModel:
    """Create an untitled file or directory inside {path}."""
    assert _directory is not None
    result = create_untitled(_directory, path, body.type, body.ext)
    _maybe_refresh_workflows(result.path)
    return result


@app.put("/api/contents/{path:path}", response_model=ContentsModel)
async def write_path_contents(
    path: str,
    model: ContentsModel,
    if_unmodified_since: Optional[str] = Header(default=None, alias="If-Unmodified-Since"),
) -> ContentsModel:
    """Save (create-or-replace) a file or create a directory.

    Optional ``If-Unmodified-Since`` header (RFC 7232, HTTP-date) enables conflict
    detection: if the file's on-disk mtime is newer than the supplied date, the
    server returns 409 instead of overwriting.
    """
    assert _directory is not None
    expected_mtime = None
    if if_unmodified_since is not None:
        try:
            expected_mtime = parsedate_to_datetime(if_unmodified_since)
        except (TypeError, ValueError) as e:
            raise HTTPException(400, f"Invalid If-Unmodified-Since header: {e}")
    result = write_contents(_directory, path, model, expected_mtime=expected_mtime)
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
) -> SingleLintReport:
    """Lint a workflow (structural + tool state validation)."""
    wf = _get_workflow(workflow_path)
    return run_lint(
        wf,
        _tool_info,
        strict=strict,
        allow=allow,
        deny=deny,
    )
