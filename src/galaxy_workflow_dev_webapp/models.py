"""Request/response models for the webapp API."""

from typing import (
    List,
    Optional,
)

from pydantic import BaseModel


class ProjectConfig(BaseModel):
    """Configuration for a GitHub project to index."""

    owner: str
    repo: str
    ref: str = "main"
    local_path: Optional[str] = None


class WorkflowEntry(BaseModel):
    """A discovered workflow file in the project."""

    relative_path: str
    format: str
    category: str


class WorkflowIndex(BaseModel):
    """Index of all workflows in a project."""

    project: str
    ref: str
    workflows: List[WorkflowEntry]


class OperationRequest(BaseModel):
    """Request to run an operation on a workflow identified by relative path."""

    populate_cache: bool = True
    tool_source: str = "shed"


class CleanRequest(OperationRequest):
    preserve: List[str] = []
    strip: List[str] = []


class ValidateRequest(OperationRequest):
    strict: bool = False
    connections: bool = False
    mode: str = "pydantic"
    allow: List[str] = []
    deny: List[str] = []


class LintRequest(OperationRequest):
    strict: bool = False
    allow: List[str] = []
    deny: List[str] = []
