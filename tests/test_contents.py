"""Tests for the /api/contents endpoints (Jupyter Contents API shape)."""

import base64
import os

import pytest
from fastapi.testclient import TestClient

from galaxy_workflow_dev_webapp import app as app_module


@pytest.fixture
def client(tmp_path):
    app_module.configure(str(tmp_path))
    app_module._tool_info = None
    app_module._workflows = []
    with TestClient(app_module.app) as c:
        yield c


def test_read_empty_root(client):
    resp = client.get("/api/contents")
    assert resp.status_code == 200
    data = resp.json()
    assert data["type"] == "directory"
    assert data["path"] == ""
    assert data["content"] == []


def test_read_directory_with_files(client, tmp_path):
    (tmp_path / "a.txt").write_text("hello")
    (tmp_path / "b.txt").write_text("world")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "nested.txt").write_text("nested")

    resp = client.get("/api/contents")
    assert resp.status_code == 200
    data = resp.json()
    assert data["type"] == "directory"
    names = sorted(c["name"] for c in data["content"])
    assert names == ["a.txt", "b.txt", "sub"]
    # Shallow: subdirectory children have content=None
    sub_entry = next(c for c in data["content"] if c["name"] == "sub")
    assert sub_entry["type"] == "directory"
    assert sub_entry["content"] is None


def test_read_file_text(client, tmp_path):
    (tmp_path / "hello.txt").write_text("greetings")
    resp = client.get("/api/contents/hello.txt")
    assert resp.status_code == 200
    data = resp.json()
    assert data["type"] == "file"
    assert data["format"] == "text"
    assert data["content"] == "greetings"
    assert data["size"] == len("greetings")


def test_read_file_binary_base64(client, tmp_path):
    raw = b"\x00\x01\x02\xff\xfe"
    (tmp_path / "blob.bin").write_bytes(raw)
    resp = client.get("/api/contents/blob.bin")
    assert resp.status_code == 200
    data = resp.json()
    assert data["format"] == "base64"
    assert base64.b64decode(data["content"]) == raw


def test_read_content_zero_skips_body(client, tmp_path):
    (tmp_path / "x.txt").write_text("body text")
    resp = client.get("/api/contents/x.txt?content=0")
    assert resp.status_code == 200
    data = resp.json()
    assert data["content"] is None
    assert data["size"] == len("body text")


def test_read_missing_404(client):
    resp = client.get("/api/contents/does_not_exist.txt")
    assert resp.status_code == 404


def test_path_escape_403(tmp_path):
    # TestClient normalizes `..` in URLs, so test at the function level.
    from fastapi import HTTPException

    from galaxy_workflow_dev_webapp.contents import resolve_safe_path

    with pytest.raises(HTTPException) as exc:
        resolve_safe_path(str(tmp_path), "../outside")
    assert exc.value.status_code == 403

    with pytest.raises(HTTPException) as exc:
        resolve_safe_path(str(tmp_path), "sub/../../outside")
    assert exc.value.status_code == 403

    with pytest.raises(HTTPException) as exc:
        resolve_safe_path(str(tmp_path), "/etc/passwd")
    assert exc.value.status_code == 400


def test_ignored_component_403(client, tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("x")
    resp = client.get("/api/contents/.git/config")
    assert resp.status_code == 403


def test_ignored_entries_hidden_from_listing(client, tmp_path):
    (tmp_path / "keep.txt").write_text("k")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "x.pyc").write_text("")
    resp = client.get("/api/contents")
    names = [c["name"] for c in resp.json()["content"]]
    assert "keep.txt" in names
    assert "__pycache__" not in names


def test_write_new_file(client, tmp_path):
    body = {
        "name": "new.txt",
        "path": "new.txt",
        "type": "file",
        "writable": True,
        "created": "2026-01-01T00:00:00Z",
        "last_modified": "2026-01-01T00:00:00Z",
        "format": "text",
        "content": "hello world",
    }
    resp = client.put("/api/contents/new.txt", json=body)
    assert resp.status_code == 200
    assert (tmp_path / "new.txt").read_text() == "hello world"
    # Returned model has no content (include_content=False post-write)
    assert resp.json()["content"] is None
    assert resp.json()["type"] == "file"


def test_write_overwrites_existing(client, tmp_path):
    (tmp_path / "f.txt").write_text("old")
    body = {
        "name": "f.txt",
        "path": "f.txt",
        "type": "file",
        "writable": True,
        "created": "2026-01-01T00:00:00Z",
        "last_modified": "2026-01-01T00:00:00Z",
        "format": "text",
        "content": "new",
    }
    resp = client.put("/api/contents/f.txt", json=body)
    assert resp.status_code == 200
    assert (tmp_path / "f.txt").read_text() == "new"


def test_write_creates_parent_dirs(client, tmp_path):
    body = {
        "name": "deep.txt",
        "path": "a/b/c/deep.txt",
        "type": "file",
        "writable": True,
        "created": "2026-01-01T00:00:00Z",
        "last_modified": "2026-01-01T00:00:00Z",
        "format": "text",
        "content": "x",
    }
    resp = client.put("/api/contents/a/b/c/deep.txt", json=body)
    assert resp.status_code == 200
    assert (tmp_path / "a" / "b" / "c" / "deep.txt").read_text() == "x"


def test_write_directory(client, tmp_path):
    body = {
        "name": "newdir",
        "path": "newdir",
        "type": "directory",
        "writable": True,
        "created": "2026-01-01T00:00:00Z",
        "last_modified": "2026-01-01T00:00:00Z",
    }
    resp = client.put("/api/contents/newdir", json=body)
    assert resp.status_code == 200
    assert (tmp_path / "newdir").is_dir()


def test_write_binary_base64(client, tmp_path):
    raw = b"\x00\xff\x10"
    body = {
        "name": "blob.bin",
        "path": "blob.bin",
        "type": "file",
        "writable": True,
        "created": "2026-01-01T00:00:00Z",
        "last_modified": "2026-01-01T00:00:00Z",
        "format": "base64",
        "content": base64.b64encode(raw).decode("ascii"),
    }
    resp = client.put("/api/contents/blob.bin", json=body)
    assert resp.status_code == 200
    assert (tmp_path / "blob.bin").read_bytes() == raw


def test_delete_file(client, tmp_path):
    (tmp_path / "gone.txt").write_text("x")
    resp = client.delete("/api/contents/gone.txt")
    assert resp.status_code == 204
    assert not (tmp_path / "gone.txt").exists()


def test_delete_directory_recursive(client, tmp_path):
    (tmp_path / "d").mkdir()
    (tmp_path / "d" / "f.txt").write_text("x")
    resp = client.delete("/api/contents/d")
    assert resp.status_code == 204
    assert not (tmp_path / "d").exists()


def test_delete_missing_404(client):
    resp = client.delete("/api/contents/nope.txt")
    assert resp.status_code == 404


def test_delete_root_forbidden(client):
    resp = client.delete("/api/contents/")
    # Trailing slash on root resolves to directory itself — forbidden
    assert resp.status_code in (403, 404, 405)


def test_rename_file(client, tmp_path):
    (tmp_path / "old.txt").write_text("content")
    resp = client.patch("/api/contents/old.txt", json={"path": "new.txt"})
    assert resp.status_code == 200
    assert not (tmp_path / "old.txt").exists()
    assert (tmp_path / "new.txt").read_text() == "content"
    assert resp.json()["path"] == "new.txt"


def test_rename_into_subdir(client, tmp_path):
    (tmp_path / "f.txt").write_text("x")
    resp = client.patch("/api/contents/f.txt", json={"path": "sub/f.txt"})
    assert resp.status_code == 200
    assert (tmp_path / "sub" / "f.txt").read_text() == "x"


def test_rename_conflict_409(client, tmp_path):
    (tmp_path / "a.txt").write_text("1")
    (tmp_path / "b.txt").write_text("2")
    resp = client.patch("/api/contents/a.txt", json={"path": "b.txt"})
    assert resp.status_code == 409


def test_auto_refresh_on_workflow_write(client, tmp_path):
    # Write a .ga file via the contents API, then check /workflows reflects it.
    ga_content = '{"a_galaxy_workflow": "true", "steps": {}}'
    body = {
        "name": "wf.ga",
        "path": "wf.ga",
        "type": "file",
        "writable": True,
        "created": "2026-01-01T00:00:00Z",
        "last_modified": "2026-01-01T00:00:00Z",
        "format": "text",
        "content": ga_content,
    }
    resp = client.put("/api/contents/wf.ga", json=body)
    assert resp.status_code == 200

    wf_resp = client.get("/workflows")
    paths = [w["relative_path"] for w in wf_resp.json()["workflows"]]
    assert "wf.ga" in paths


def test_auto_refresh_on_workflow_delete(client, tmp_path):
    (tmp_path / "wf.ga").write_text('{"a_galaxy_workflow": "true", "steps": {}}')
    # Seed cache
    client.post("/workflows/refresh")
    assert any(w["relative_path"] == "wf.ga" for w in client.get("/workflows").json()["workflows"])

    resp = client.delete("/api/contents/wf.ga")
    assert resp.status_code == 204
    paths = [w["relative_path"] for w in client.get("/workflows").json()["workflows"]]
    assert "wf.ga" not in paths


def test_post_untitled_file(client, tmp_path):
    resp = client.post("/api/contents", json={"type": "file"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "untitled"
    assert data["type"] == "file"
    assert (tmp_path / "untitled").exists()


def test_post_untitled_file_with_ext(client, tmp_path):
    resp = client.post("/api/contents", json={"type": "file", "ext": ".ga"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "untitled.ga"
    assert (tmp_path / "untitled.ga").exists()


def test_post_untitled_file_with_ext_no_dot(client, tmp_path):
    resp = client.post("/api/contents", json={"type": "file", "ext": "txt"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "untitled.txt"


def test_post_untitled_file_collision_suffix(client, tmp_path):
    (tmp_path / "untitled.ga").write_text("existing")
    resp = client.post("/api/contents", json={"type": "file", "ext": ".ga"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "untitled1.ga"
    (tmp_path / "untitled1.ga").write_text("also existing")
    resp = client.post("/api/contents", json={"type": "file", "ext": ".ga"})
    assert resp.json()["name"] == "untitled2.ga"


def test_post_untitled_directory(client, tmp_path):
    resp = client.post("/api/contents", json={"type": "directory"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Untitled Folder"
    assert data["type"] == "directory"
    assert (tmp_path / "Untitled Folder").is_dir()


def test_post_untitled_directory_collision(client, tmp_path):
    (tmp_path / "Untitled Folder").mkdir()
    resp = client.post("/api/contents", json={"type": "directory"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Untitled Folder 1"


def test_post_untitled_in_subdir(client, tmp_path):
    (tmp_path / "sub").mkdir()
    resp = client.post("/api/contents/sub", json={"type": "file", "ext": ".txt"})
    assert resp.status_code == 200
    assert resp.json()["path"] == "sub/untitled.txt"
    assert (tmp_path / "sub" / "untitled.txt").exists()


def test_post_untitled_missing_parent_404(client):
    resp = client.post("/api/contents/does_not_exist", json={"type": "file"})
    assert resp.status_code == 404


def test_post_untitled_refreshes_workflows(client, tmp_path):
    resp = client.post("/api/contents", json={"type": "file", "ext": ".ga"})
    assert resp.status_code == 200
    # Newly created empty .ga isn't a valid workflow, but the refresh hook
    # should still run without error and /workflows should be callable.
    wf_resp = client.get("/workflows")
    assert wf_resp.status_code == 200


def test_format_override_base64_on_text(client, tmp_path):
    (tmp_path / "hello.txt").write_text("greetings")
    resp = client.get("/api/contents/hello.txt?format=base64")
    assert resp.status_code == 200
    data = resp.json()
    assert data["format"] == "base64"
    assert base64.b64decode(data["content"]) == b"greetings"


def test_format_override_text_on_binary_400(client, tmp_path):
    (tmp_path / "blob.bin").write_bytes(b"\x00\x01\xff")
    resp = client.get("/api/contents/blob.bin?format=text")
    assert resp.status_code == 400


def test_format_override_invalid_400(client, tmp_path):
    (tmp_path / "f.txt").write_text("x")
    resp = client.get("/api/contents/f.txt?format=json")
    assert resp.status_code == 400


def test_put_if_unmodified_since_stale_409(client, tmp_path):
    # Create a file on disk with a recent mtime.
    (tmp_path / "f.txt").write_text("original")
    body = {
        "name": "f.txt",
        "path": "f.txt",
        "type": "file",
        "writable": True,
        "created": "2026-01-01T00:00:00Z",
        "last_modified": "2026-01-01T00:00:00Z",
        "format": "text",
        "content": "new",
    }
    # Supply a stale HTTP-date (year 2000): disk mtime is far newer.
    resp = client.put(
        "/api/contents/f.txt",
        json=body,
        headers={"If-Unmodified-Since": "Sat, 01 Jan 2000 00:00:00 GMT"},
    )
    assert resp.status_code == 409
    # File is untouched
    assert (tmp_path / "f.txt").read_text() == "original"


def test_put_if_unmodified_since_fresh_ok(client, tmp_path):
    # When the header is from the future, disk mtime is older → write succeeds.
    (tmp_path / "f.txt").write_text("original")
    body = {
        "name": "f.txt",
        "path": "f.txt",
        "type": "file",
        "writable": True,
        "created": "2026-01-01T00:00:00Z",
        "last_modified": "2026-01-01T00:00:00Z",
        "format": "text",
        "content": "new",
    }
    resp = client.put(
        "/api/contents/f.txt",
        json=body,
        headers={"If-Unmodified-Since": "Sun, 01 Jan 2099 00:00:00 GMT"},
    )
    assert resp.status_code == 200
    assert (tmp_path / "f.txt").read_text() == "new"


def test_put_if_unmodified_since_invalid_400(client, tmp_path):
    body = {
        "name": "f.txt",
        "path": "f.txt",
        "type": "file",
        "writable": True,
        "created": "2026-01-01T00:00:00Z",
        "last_modified": "2026-01-01T00:00:00Z",
        "format": "text",
        "content": "x",
    }
    resp = client.put(
        "/api/contents/f.txt",
        json=body,
        headers={"If-Unmodified-Since": "not a date"},
    )
    assert resp.status_code == 400


def test_put_no_conflict_check_overwrites(client, tmp_path):
    # Without the header, stale body last_modified is ignored (phase 1 behavior).
    (tmp_path / "f.txt").write_text("original")
    body = {
        "name": "f.txt",
        "path": "f.txt",
        "type": "file",
        "writable": True,
        "created": "2026-01-01T00:00:00Z",
        "last_modified": "2026-01-01T00:00:00Z",
        "format": "text",
        "content": "new",
    }
    resp = client.put("/api/contents/f.txt", json=body)
    assert resp.status_code == 200
    assert (tmp_path / "f.txt").read_text() == "new"


def test_create_checkpoint(client, tmp_path):
    (tmp_path / "f.txt").write_text("original")
    resp = client.post("/api/contents/f.txt/checkpoints")
    assert resp.status_code == 201
    data = resp.json()
    assert data["id"] == "checkpoint"
    assert "last_modified" in data
    assert (tmp_path / ".checkpoints" / "f.txt" / "checkpoint").read_text() == "original"


def test_create_checkpoint_missing_file_404(client):
    resp = client.post("/api/contents/nope.txt/checkpoints")
    assert resp.status_code == 404


def test_list_checkpoints_empty(client, tmp_path):
    (tmp_path / "f.txt").write_text("x")
    resp = client.get("/api/contents/f.txt/checkpoints")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_checkpoints_after_create(client, tmp_path):
    (tmp_path / "f.txt").write_text("x")
    client.post("/api/contents/f.txt/checkpoints")
    resp = client.get("/api/contents/f.txt/checkpoints")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == "checkpoint"


def test_restore_checkpoint(client, tmp_path):
    (tmp_path / "f.txt").write_text("original")
    client.post("/api/contents/f.txt/checkpoints")
    (tmp_path / "f.txt").write_text("edited")
    resp = client.post("/api/contents/f.txt/checkpoints/checkpoint")
    assert resp.status_code == 204
    assert (tmp_path / "f.txt").read_text() == "original"


def test_restore_checkpoint_missing_404(client, tmp_path):
    (tmp_path / "f.txt").write_text("x")
    resp = client.post("/api/contents/f.txt/checkpoints/nope")
    assert resp.status_code == 404


def test_delete_checkpoint(client, tmp_path):
    (tmp_path / "f.txt").write_text("x")
    client.post("/api/contents/f.txt/checkpoints")
    resp = client.delete("/api/contents/f.txt/checkpoints/checkpoint")
    assert resp.status_code == 204
    assert client.get("/api/contents/f.txt/checkpoints").json() == []
    # Cleanup: empty checkpoint dir removed too
    assert not (tmp_path / ".checkpoints" / "f.txt").exists()


def test_delete_checkpoint_missing_404(client, tmp_path):
    (tmp_path / "f.txt").write_text("x")
    resp = client.delete("/api/contents/f.txt/checkpoints/nope")
    assert resp.status_code == 404


def test_checkpoints_dir_hidden_from_listing(client, tmp_path):
    (tmp_path / "f.txt").write_text("x")
    client.post("/api/contents/f.txt/checkpoints")
    resp = client.get("/api/contents")
    names = [c["name"] for c in resp.json()["content"]]
    assert "f.txt" in names
    assert ".checkpoints" not in names


def test_checkpoints_path_forbidden(client, tmp_path):
    (tmp_path / "f.txt").write_text("x")
    client.post("/api/contents/f.txt/checkpoints")
    # User cannot reach the .checkpoints tree via the contents API
    resp = client.get("/api/contents/.checkpoints/f.txt/checkpoint")
    assert resp.status_code == 403


def test_delete_file_cascades_checkpoints(client, tmp_path):
    (tmp_path / "f.txt").write_text("x")
    client.post("/api/contents/f.txt/checkpoints")
    assert (tmp_path / ".checkpoints" / "f.txt" / "checkpoint").exists()
    resp = client.delete("/api/contents/f.txt")
    assert resp.status_code == 204
    assert not (tmp_path / ".checkpoints" / "f.txt").exists()


def test_rename_file_cascades_checkpoints(client, tmp_path):
    (tmp_path / "old.txt").write_text("x")
    client.post("/api/contents/old.txt/checkpoints")
    resp = client.patch("/api/contents/old.txt", json={"path": "new.txt"})
    assert resp.status_code == 200
    assert not (tmp_path / ".checkpoints" / "old.txt").exists()
    assert (tmp_path / ".checkpoints" / "new.txt" / "checkpoint").read_text() == "x"
    # Checkpoint is still usable under the new name
    resp = client.get("/api/contents/new.txt/checkpoints")
    assert len(resp.json()) == 1


def test_delete_directory_cascades_nested_checkpoints(client, tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "f.txt").write_text("x")
    client.post("/api/contents/sub/f.txt/checkpoints")
    assert (tmp_path / ".checkpoints" / "sub" / "f.txt" / "checkpoint").exists()
    resp = client.delete("/api/contents/sub")
    assert resp.status_code == 204
    assert not (tmp_path / ".checkpoints" / "sub").exists()


def test_checkpoint_on_directory_404(client, tmp_path):
    (tmp_path / "d").mkdir()
    resp = client.post("/api/contents/d/checkpoints")
    assert resp.status_code == 404


def test_symlink_escape_forbidden(client, tmp_path):
    outside = tmp_path.parent / "outside_target"
    outside.mkdir()
    (outside / "secret.txt").write_text("leak")
    os.symlink(str(outside), str(tmp_path / "link"))
    resp = client.get("/api/contents/link/secret.txt")
    assert resp.status_code == 403
