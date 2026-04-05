"""Request/response models for the webapp API."""

from datetime import datetime
from typing import (
    List,
    Literal,
    Optional,
    Union,
)

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


class ContentsModel(BaseModel):
    """Jupyter Contents API-shaped model for files and directories."""

    name: str
    path: str
    type: Literal["file", "directory"]
    writable: bool
    created: datetime
    last_modified: datetime
    size: Optional[int] = None
    mimetype: Optional[str] = None
    format: Optional[Literal["text", "base64"]] = None
    content: Optional[Union[str, List["ContentsModel"]]] = None


ContentsModel.model_rebuild()


class RenameRequest(BaseModel):
    """Body for PATCH /api/contents/{path} — rename/move."""

    path: str
