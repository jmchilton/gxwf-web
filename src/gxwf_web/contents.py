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

from .models import (
    CheckpointModel,
    ContentsModel,
)

# Jupyter-convention defaults for POST untitled creation
UNTITLED_FILE_STEM = "untitled"
UNTITLED_DIRECTORY_STEM = "Untitled Folder"

# Checkpoint storage — mirrored tree under <root>/.checkpoints/<rel_path>/<id>
CHECKPOINTS_DIR = ".checkpoints"
DEFAULT_CHECKPOINT_ID = "checkpoint"

IGNORE_NAMES = frozenset(
    {".git", "__pycache__", ".venv", ".ruff_cache", ".pytest_cache", ".mypy_cache", ".tox", CHECKPOINTS_DIR}
)
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


def _read_file_body(abs_path: str, format_override: Optional[str] = None) -> Tuple[str, str, str]:
    """Return (format, content, mimetype) for a file on disk.

    When format_override is 'text' the file must be utf-8 decodable (else 400).
    When 'base64', encode raw bytes regardless of contents.
    When None, auto-detect: text if utf-8 decodable, else base64.
    """
    with open(abs_path, "rb") as f:
        raw = f.read()
    guessed = mimetypes.guess_type(abs_path)[0]
    if format_override == "text":
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as e:
            raise HTTPException(400, f"File is not valid utf-8: {e}")
        return "text", text, guessed or "text/plain"
    if format_override == "base64":
        return "base64", base64.b64encode(raw).decode("ascii"), guessed or "application/octet-stream"
    if format_override is not None:
        raise HTTPException(400, f"Unsupported format: {format_override}")
    try:
        text = raw.decode("utf-8")
        return "text", text, guessed or "text/plain"
    except UnicodeDecodeError:
        return "base64", base64.b64encode(raw).decode("ascii"), guessed or "application/octet-stream"


def read_contents(
    directory: str,
    rel_path: str,
    include_content: bool = True,
    format_override: Optional[str] = None,
) -> ContentsModel:
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
        fmt, content_val, mimetype = _read_file_body(abs_path, format_override=format_override)
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


MTIME_TOLERANCE_SECONDS = 1.0


def write_contents(
    directory: str,
    rel_path: str,
    model: ContentsModel,
    expected_mtime: Optional[datetime] = None,
) -> ContentsModel:
    abs_path = resolve_safe_path(directory, rel_path)
    parent = os.path.dirname(abs_path)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)

    # Conflict detection: if caller supplied an expected mtime, refuse if disk is newer.
    if expected_mtime is not None and os.path.exists(abs_path) and os.path.isfile(abs_path):
        disk_mtime = datetime.fromtimestamp(os.stat(abs_path).st_mtime, tz=timezone.utc)
        if (disk_mtime - expected_mtime).total_seconds() > MTIME_TOLERANCE_SECONDS:
            raise HTTPException(
                409,
                f"File modified on disk since {expected_mtime.isoformat()} (disk mtime {disk_mtime.isoformat()})",
            )

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
    # Cascade: remove any checkpoints for this path.
    cp_dir = _checkpoint_dir_for(directory, rel_path)
    if os.path.isdir(cp_dir):
        shutil.rmtree(cp_dir)


def create_untitled(
    directory: str,
    parent_rel: str,
    type_: str,
    ext: Optional[str] = None,
) -> ContentsModel:
    """Create an untitled file or directory inside parent_rel, picking a unique name.

    Files: ``untitled{ext}``, ``untitled1{ext}``, ``untitled2{ext}`` …
    Directories: ``Untitled Folder``, ``Untitled Folder 1``, ``Untitled Folder 2`` …
    """
    parent_abs = resolve_safe_path(directory, parent_rel)
    if not os.path.isdir(parent_abs):
        raise HTTPException(404, f"Parent directory not found: {parent_rel}")

    if type_ == "file":
        stem = UNTITLED_FILE_STEM
        suffix = ext or ""
        if suffix and not suffix.startswith("."):
            suffix = "." + suffix
        i = 0
        while True:
            name = f"{stem}{suffix}" if i == 0 else f"{stem}{i}{suffix}"
            candidate_rel = f"{parent_rel}/{name}" if parent_rel else name
            candidate_abs = resolve_safe_path(directory, candidate_rel)
            if not os.path.exists(candidate_abs):
                with open(candidate_abs, "x"):
                    pass
                return read_contents(directory, candidate_rel, include_content=False)
            i += 1
    elif type_ == "directory":
        stem = UNTITLED_DIRECTORY_STEM
        i = 0
        while True:
            name = stem if i == 0 else f"{stem} {i}"
            candidate_rel = f"{parent_rel}/{name}" if parent_rel else name
            candidate_abs = resolve_safe_path(directory, candidate_rel)
            if not os.path.exists(candidate_abs):
                os.mkdir(candidate_abs)
                return read_contents(directory, candidate_rel, include_content=False)
            i += 1
    else:
        raise HTTPException(400, f"Unsupported type: {type_}")


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
    # Cascade: move any checkpoints for this path.
    src_cp = _checkpoint_dir_for(directory, rel_path)
    if os.path.isdir(src_cp):
        dst_cp = _checkpoint_dir_for(directory, new_rel_path)
        os.makedirs(os.path.dirname(dst_cp), exist_ok=True)
        os.rename(src_cp, dst_cp)
    return read_contents(directory, new_rel_path, include_content=False)


# ---------- Checkpoints ----------


def _checkpoint_dir_for(directory: str, rel_path: str) -> str:
    """Return the absolute path of the checkpoint directory for a given file.

    Bypasses ``resolve_safe_path`` because ``.checkpoints`` is in the ignore list;
    the caller is responsible for validating ``rel_path`` via ``resolve_safe_path``
    before calling this.
    """
    directory = os.path.abspath(directory)
    return os.path.join(directory, CHECKPOINTS_DIR, rel_path)


def _checkpoint_model(cp_file: str, cp_id: str) -> CheckpointModel:
    mtime = datetime.fromtimestamp(os.stat(cp_file).st_mtime, tz=timezone.utc)
    return CheckpointModel(id=cp_id, last_modified=mtime)


def create_checkpoint(directory: str, rel_path: str) -> CheckpointModel:
    """Snapshot the file at rel_path under the default checkpoint id."""
    abs_path = resolve_safe_path(directory, rel_path)
    if not os.path.isfile(abs_path):
        raise HTTPException(404, f"File not found: {rel_path}")
    cp_dir = _checkpoint_dir_for(directory, rel_path)
    os.makedirs(cp_dir, exist_ok=True)
    cp_file = os.path.join(cp_dir, DEFAULT_CHECKPOINT_ID)
    shutil.copy2(abs_path, cp_file)
    return _checkpoint_model(cp_file, DEFAULT_CHECKPOINT_ID)


def list_checkpoints(directory: str, rel_path: str) -> List[CheckpointModel]:
    """List checkpoints for a file. Empty list if none."""
    abs_path = resolve_safe_path(directory, rel_path)
    if not os.path.isfile(abs_path):
        raise HTTPException(404, f"File not found: {rel_path}")
    cp_dir = _checkpoint_dir_for(directory, rel_path)
    if not os.path.isdir(cp_dir):
        return []
    result = []
    for entry in sorted(os.listdir(cp_dir)):
        cp_file = os.path.join(cp_dir, entry)
        if os.path.isfile(cp_file):
            result.append(_checkpoint_model(cp_file, entry))
    return result


def restore_checkpoint(directory: str, rel_path: str, checkpoint_id: str) -> None:
    """Restore the file at rel_path from a stored checkpoint."""
    abs_path = resolve_safe_path(directory, rel_path)
    if not os.path.isfile(abs_path):
        raise HTTPException(404, f"File not found: {rel_path}")
    cp_dir = _checkpoint_dir_for(directory, rel_path)
    cp_file = os.path.join(cp_dir, checkpoint_id)
    if not os.path.isfile(cp_file):
        raise HTTPException(404, f"Checkpoint not found: {checkpoint_id}")
    shutil.copy2(cp_file, abs_path)


def delete_checkpoint(directory: str, rel_path: str, checkpoint_id: str) -> None:
    """Remove a stored checkpoint."""
    resolve_safe_path(directory, rel_path)  # validation only
    cp_dir = _checkpoint_dir_for(directory, rel_path)
    cp_file = os.path.join(cp_dir, checkpoint_id)
    if not os.path.isfile(cp_file):
        raise HTTPException(404, f"Checkpoint not found: {checkpoint_id}")
    os.remove(cp_file)
    # Clean up empty checkpoint dir tree.
    try:
        os.removedirs(cp_dir)
    except OSError:
        pass
