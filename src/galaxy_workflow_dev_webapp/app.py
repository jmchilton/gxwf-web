"""FastAPI application for Galaxy workflow development operations."""

from contextlib import asynccontextmanager
from typing import Any

from fastapi import (
    FastAPI,
    HTTPException,
    Path,
)

from .models import (
    CleanRequest,
    LintRequest,
    OperationRequest,
    ProjectConfig,
    ValidateRequest,
    WorkflowIndex,
)
from .operations import (
    get_tool_info,
    run_clean,
    run_export_format2,
    run_lint,
    run_roundtrip,
    run_validate,
)
from .project import (
    Project,
    ProjectRegistry,
)


registry = ProjectRegistry()
_tool_info = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _tool_info
    _tool_info = get_tool_info()
    yield


app = FastAPI(
    title="Galaxy Workflow Development API",
    description="Validate, lint, clean, and convert Galaxy workflows against tool definitions",
    version="0.1.0",
    lifespan=lifespan,
)


def _get_project(owner: str, repo: str) -> Project:
    project = registry.get(owner, repo)
    if project is None:
        raise HTTPException(404, f"Project {owner}/{repo} not registered")
    return project


def _get_workflow(project: Project, workflow_path: str):
    wf = project.get_workflow(workflow_path)
    if wf is None:
        raise HTTPException(404, f"Workflow not found: {workflow_path}")
    return wf


def _ensure_tool_info(req: OperationRequest):
    if req.populate_cache:
        from galaxy.tool_util.workflow_state.cache import populate_cache
        populate_cache(_tool_info, _get_project.__name__, source=req.tool_source)
    return _tool_info


@app.post("/projects", response_model=WorkflowIndex)
async def register_project(config: ProjectConfig):
    """Register a GitHub project and index its workflows."""
    project = registry.add(config)
    project.ensure_cloned()
    return project.index()


@app.get("/projects/{owner}/{repo}", response_model=WorkflowIndex)
async def get_project_index(owner: str, repo: str):
    """Get the workflow index for a registered project."""
    project = _get_project(owner, repo)
    return project.index()


@app.post("/projects/{owner}/{repo}/refresh", response_model=WorkflowIndex)
async def refresh_project(owner: str, repo: str):
    """Re-fetch and re-index a project."""
    project = _get_project(owner, repo)
    project.ensure_cloned()
    return project.index()


@app.post("/projects/{owner}/{repo}/workflows/{workflow_path:path}/validate")
async def validate_workflow(
    owner: str,
    repo: str,
    workflow_path: str = Path(..., description="Relative path to workflow file"),
    body: ValidateRequest = ValidateRequest(),
) -> Any:
    """Validate a workflow's tool state against tool definitions."""
    project = _get_project(owner, repo)
    wf = _get_workflow(project, workflow_path)
    return run_validate(
        wf, _tool_info,
        strict=body.strict,
        connections=body.connections,
        mode=body.mode,
        allow=body.allow,
        deny=body.deny,
    )


@app.post("/projects/{owner}/{repo}/workflows/{workflow_path:path}/clean")
async def clean_workflow(
    owner: str,
    repo: str,
    workflow_path: str = Path(..., description="Relative path to workflow file"),
    body: CleanRequest = CleanRequest(),
) -> Any:
    """Clean stale tool state keys from a workflow."""
    project = _get_project(owner, repo)
    wf = _get_workflow(project, workflow_path)
    return run_clean(
        wf, _tool_info,
        preserve=body.preserve,
        strip=body.strip,
    )


@app.post("/projects/{owner}/{repo}/workflows/{workflow_path:path}/export-format2")
async def export_format2(
    owner: str,
    repo: str,
    workflow_path: str = Path(..., description="Relative path to workflow file"),
    body: OperationRequest = OperationRequest(),
) -> Any:
    """Export a native workflow to format2 with schema-aware state."""
    project = _get_project(owner, repo)
    wf = _get_workflow(project, workflow_path)
    return run_export_format2(wf, _tool_info)


@app.post("/projects/{owner}/{repo}/workflows/{workflow_path:path}/roundtrip")
async def roundtrip_workflow(
    owner: str,
    repo: str,
    workflow_path: str = Path(..., description="Relative path to workflow file"),
    body: OperationRequest = OperationRequest(),
) -> Any:
    """Run round-trip validation (native -> format2 -> native)."""
    project = _get_project(owner, repo)
    wf = _get_workflow(project, workflow_path)
    return run_roundtrip(wf, _tool_info)


@app.post("/projects/{owner}/{repo}/workflows/{workflow_path:path}/lint")
async def lint_workflow(
    owner: str,
    repo: str,
    workflow_path: str = Path(..., description="Relative path to workflow file"),
    body: LintRequest = LintRequest(),
) -> Any:
    """Lint a workflow (structural + tool state validation)."""
    project = _get_project(owner, repo)
    wf = _get_workflow(project, workflow_path)
    return run_lint(
        wf, _tool_info,
        strict=body.strict,
        allow=body.allow,
        deny=body.deny,
    )
