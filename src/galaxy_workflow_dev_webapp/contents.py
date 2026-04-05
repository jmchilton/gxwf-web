"""File CRUD operations mirroring the Jupyter Contents API shape.

Pure functions, no FastAPI app state — takes the target directory as an argument.
"""

import base64
import mimetypes
import os
import shutil
from datetime import (
    datetime,
    timezone,
)
from typing import (
    List,
    Optional,
    Tuple,
)

from fastapi import HTTPException

from .models import ContentsModel

IGNORE_NAMES = frozenset({".git", "__pycache__", ".venv", ".ruff_cache", ".pytest_cache", ".mypy_cache", ".tox"})
IGNORE_SUFFIXES = (".pyc", ".pyo")

WORKFLOW_SUFFIXES = (".ga", ".gxwf.yml", ".gxwf.yaml")


def is_ignored(name: str) -> bool:
    if name in IGNORE_NAMES:
        return True
    return name.endswith(IGNORE_SUFFIXES)


def is_workflow_file(rel_path: str) -> bool:
    return rel_path.endswith(WORKFLOW_SUFFIXES)


def resolve_safe_path(directory: str, rel_path: str) -> str:
    """Resolve rel_path under directory, rejecting escapes."""
    directory = os.path.abspath(directory)
    if rel_path in ("", "/"):
        return directory
    if os.path.isabs(rel_path):
        raise HTTPException(400, "Path must be relative")
    joined = os.path.abspath(os.path.join(directory, rel_path))
    if joined != directory and not joined.startswith(directory + os.sep):
        raise HTTPException(403, "Path escapes configured directory")
    # Symlink escape check — only if target exists (else realpath == joined)
    real_joined = os.path.realpath(joined)
    real_dir = os.path.realpath(directory)
    if real_joined != real_dir and not real_joined.startswith(real_dir + os.sep):
        raise HTTPException(403, "Path escapes configured directory via symlink")
    for part in rel_path.replace("\\", "/").split("/"):
        if part and is_ignored(part):
            raise HTTPException(403, f"Path contains ignored component: {part}")
    return joined


def _stat_times(abs_path: str) -> Tuple[datetime, datetime, int]:
    st = os.stat(abs_path)
    last_modified = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc)
    created = datetime.fromtimestamp(st.st_ctime, tz=timezone.utc)
    return created, last_modified, st.st_size


def _read_file_body(abs_path: str) -> Tuple[str, str, str]:
    """Return (format, content, mimetype) for a file on disk."""
    with open(abs_path, "rb") as f:
        raw = f.read()
    guessed = mimetypes.guess_type(abs_path)[0]
    try:
        text = raw.decode("utf-8")
        return "text", text, guessed or "text/plain"
    except UnicodeDecodeError:
        return "base64", base64.b64encode(raw).decode("ascii"), guessed or "application/octet-stream"


def read_contents(directory: str, rel_path: str, include_content: bool = True) -> ContentsModel:
    abs_path = resolve_safe_path(directory, rel_path)
    if not os.path.exists(abs_path):
        raise HTTPException(404, f"Not found: {rel_path}")
    name = os.path.basename(abs_path) or os.path.basename(os.path.abspath(directory))
    writable = os.access(abs_path, os.W_OK)
    created, last_modified, size = _stat_times(abs_path)

    if os.path.isdir(abs_path):
        children: Optional[List[ContentsModel]] = None
        if include_content:
            children = []
            for entry in sorted(os.listdir(abs_path)):
                if is_ignored(entry):
                    continue
                child_rel = f"{rel_path}/{entry}" if rel_path else entry
                children.append(read_contents(directory, child_rel, include_content=False))
        return ContentsModel(
            name=name,
            path=rel_path,
            type="directory",
            writable=writable,
            created=created,
            last_modified=last_modified,
            size=None,
            mimetype=None,
            format=None,
            content=children,
        )

    fmt: Optional[str] = None
    content_val: Optional[str] = None
    mimetype = mimetypes.guess_type(abs_path)[0]
    if include_content:
        fmt, content_val, mimetype = _read_file_body(abs_path)
    return ContentsModel(
        name=name,
        path=rel_path,
        type="file",
        writable=writable,
        created=created,
        last_modified=last_modified,
        size=size,
        mimetype=mimetype,
        format=fmt,  # type: ignore[arg-type]
        content=content_val,
    )


def write_contents(directory: str, rel_path: str, model: ContentsModel) -> ContentsModel:
    abs_path = resolve_safe_path(directory, rel_path)
    parent = os.path.dirname(abs_path)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)

    if model.type == "directory":
        os.makedirs(abs_path, exist_ok=True)
    else:
        fmt = model.format or "text"
        if fmt == "text":
            raw_content = model.content if isinstance(model.content, str) else ""
            data = raw_content.encode("utf-8")
        elif fmt == "base64":
            raw_content = model.content if isinstance(model.content, str) else ""
            data = base64.b64decode(raw_content)
        else:
            raise HTTPException(400, f"Unsupported format: {fmt}")
        with open(abs_path, "wb") as f:
            f.write(data)

    return read_contents(directory, rel_path, include_content=False)


def delete_contents(directory: str, rel_path: str) -> None:
    abs_path = resolve_safe_path(directory, rel_path)
    if not os.path.exists(abs_path):
        raise HTTPException(404, f"Not found: {rel_path}")
    if abs_path == os.path.abspath(directory):
        raise HTTPException(403, "Cannot delete configured root directory")
    if os.path.isdir(abs_path):
        shutil.rmtree(abs_path)
    else:
        os.remove(abs_path)


def rename_contents(directory: str, rel_path: str, new_rel_path: str) -> ContentsModel:
    src = resolve_safe_path(directory, rel_path)
    dst = resolve_safe_path(directory, new_rel_path)
    if not os.path.exists(src):
        raise HTTPException(404, f"Not found: {rel_path}")
    if os.path.exists(dst):
        raise HTTPException(409, f"Destination exists: {new_rel_path}")
    parent = os.path.dirname(dst)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)
    os.rename(src, dst)
    return read_contents(directory, new_rel_path, include_content=False)
