# Contents API

The webapp exposes a [Jupyter Contents API][jupyter]-compatible file surface
at `/api/contents/...`. It is the least obvious part of the codebase and
nothing in the source tree explains it in isolation — this page is that
explanation.

[jupyter]: https://jupyter-server.readthedocs.io/en/latest/developers/contents.html

## Path shape

`{path}` in every route is a filesystem-relative path under the configured
workflow root directory. It is URL-encoded, may contain `/`, and must not
escape the root (`..` traversal and symlink escapes both return 403).

Certain components are always refused (403 `Path contains ignored
component`): `.git`, `__pycache__`, `.venv`, `.ruff_cache`, `.pytest_cache`,
`.mypy_cache`, `.tox`, and the reserved `.checkpoints` directory used by the
checkpoint subsystem. Files ending in `.pyc` or `.pyo` are also silently
filtered from directory listings.

## Content + format query params

`GET /api/contents/{path}` accepts two optional query parameters:

| Param | Default | Meaning |
| --- | --- | --- |
| `content` | `1` | `0` returns metadata only (no `content` field populated) |
| `format` | auto | `text` forces utf-8 decode (400 if not valid utf-8); `base64` forces raw-bytes encoding; omitted auto-picks text-if-decodable, else base64 |

Directory reads always set `type=directory` and populate `content` with a
shallow list of child `ContentsModel` entries (no recursion, no content for
children). Ignored names are filtered from directory listings.

## Untitled creation (`POST /api/contents/{path}`)

`POST` with body `{"type": "file", "ext": ".ga"}` creates a new file under
`{path}` with a Jupyter-style unique name:

- Files: `untitled{ext}`, `untitled1{ext}`, `untitled2{ext}`, …
- Directories: `Untitled Folder`, `Untitled Folder 1`, `Untitled Folder 2`, …

`ext` is normalized to include a leading `.` if omitted. `POST /api/contents`
(no path) creates inside the configured root.

## Write + conflict detection (`PUT /api/contents/{path}`)

Body is a full `ContentsModel`. Parent directories are created on demand.
Writes accept an optional `If-Unmodified-Since` header (RFC 7232, HTTP-date):

- If supplied and the on-disk mtime is newer than the supplied date by more
  than ~1 second (filesystem timestamp tolerance), the server returns `409
  Conflict` without touching the file.
- If omitted, writes are unconditional (last-write-wins).

This is the single concession to multi-client editing. Clients that care
about lost updates should always send `If-Unmodified-Since` using the
`last_modified` value they received from the most recent `GET`.

## Checkpoints

Checkpoints are mirrored under `<root>/.checkpoints/<rel_path>/<id>`. The
default id is `checkpoint` — `create_checkpoint` overwrites in place, so you
always have exactly one checkpoint per file unless you manually create
additional ids on disk.

| Route | Semantics |
| --- | --- |
| `GET /api/contents/{path}/checkpoints` | List checkpoints for a file (empty list if none) |
| `POST /api/contents/{path}/checkpoints` | Snapshot file → `.checkpoints/{path}/checkpoint` (201) |
| `POST /api/contents/{path}/checkpoints/{id}` | Restore file from checkpoint (204) |
| `DELETE /api/contents/{path}/checkpoints/{id}` | Remove stored checkpoint (204) |

Checkpoint cascade:

- `DELETE /api/contents/{path}` recursively drops the corresponding
  `.checkpoints/{path}` tree.
- `PATCH /api/contents/{path}` (rename) moves the `.checkpoints` mirror along
  with the file.

## Safety guarantees

- **Path escape** — `resolve_safe_path` normalizes the join and rejects any
  result not under the absolute root (plain `..` or symlink).
- **Ignored components** — the ignore list applies to *every* path segment,
  not just the final one.
- **Root deletion** — `DELETE` on the empty path is refused with 403.
- **Workflow cache refresh** — any mutation of a path ending in a workflow
  suffix (`.ga`, `.gxwf.yml`, `.gxwf.yaml`) triggers `discover_workflows` so
  `/workflows` stays in sync with disk.

## Routes summary

| Method | Path | Status | Semantics |
| --- | --- | --- | --- |
| GET | `/api/contents` | 200 | Read configured root (directory) |
| GET | `/api/contents/{path}` | 200 / 404 | Read file or directory |
| PUT | `/api/contents/{path}` | 200 / 400 / 409 | Create-or-replace file or create directory; `If-Unmodified-Since` conflict detection |
| POST | `/api/contents` | 200 | Create untitled in root |
| POST | `/api/contents/{path}` | 200 | Create untitled inside `{path}` |
| PATCH | `/api/contents/{path}` | 200 / 404 / 409 | Rename / move (409 if destination exists) |
| DELETE | `/api/contents/{path}` | 204 / 403 / 404 | Delete file or directory (recursive) |
| GET | `/api/contents/{path}/checkpoints` | 200 | List checkpoints |
| POST | `/api/contents/{path}/checkpoints` | 201 | Create checkpoint |
| POST | `/api/contents/{path}/checkpoints/{id}` | 204 | Restore checkpoint |
| DELETE | `/api/contents/{path}/checkpoints/{id}` | 204 / 404 | Delete checkpoint |
