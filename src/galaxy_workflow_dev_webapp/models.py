"""Request/response models for the webapp API."""

from typing import List

from pydantic import BaseModel


class WorkflowEntry(BaseModel):
    """A discovered workflow file."""

    relative_path: str
    format: str
    category: str


class WorkflowIndex(BaseModel):
    """Index of all workflows in the target directory."""

    directory: str
    workflows: List[WorkflowEntry]


class OperationRequest(BaseModel):
    """Base request for workflow operations."""

    pass


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
