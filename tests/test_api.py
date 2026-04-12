"""Basic API tests using FastAPI TestClient."""

import json
import os
import shutil

import pytest
from fastapi.testclient import TestClient

from gxwf_web import app as app_module

FIXTURE_DIR = os.path.join(
    os.path.dirname(__file__),
    "..",
    "src",
    "gxwf_web",
    # resolved below
)

_GALAXY_FIXTURES = os.path.normpath(
    os.path.join(
        os.path.dirname(__file__),
        # walk up to repo root, then into the galaxy worktree fixtures
        "..",
        "..",
        "..",
        "worktrees",
        "galaxy",
        "branch",
        "wf_tool_state",
        "packages",
        "tool_util",
        "tests",
        "tool_util",
        "workflow_state",
        "fixtures",
    )
)

_NATIVE_FIXTURE = os.path.join(_GALAXY_FIXTURES, "synthetic-cat1-stale.ga")
_FORMAT2_FIXTURE = os.path.join(_GALAXY_FIXTURES, "synthetic-cat1.gxwf.yml")


@pytest.fixture
def client(tmp_path):
    app_module.configure(str(tmp_path))
    app_module._tool_info = None
    app_module._workflows = []
    with TestClient(app_module.app) as c:
        yield c


@pytest.fixture
def workflow_client(tmp_path):
    """Client with real tool_info and workflow fixtures copied to tmp_path."""
    from galaxy.tool_util.workflow_state.cache import build_tool_info
    from galaxy.tool_util.workflow_state.workflow_tree import discover_workflows

    shutil.copy(_NATIVE_FIXTURE, tmp_path / "synthetic-cat1-stale.ga")
    shutil.copy(_FORMAT2_FIXTURE, tmp_path / "synthetic-cat1.gxwf.yml")

    app_module.configure(str(tmp_path))
    app_module._tool_info = build_tool_info()
    app_module._workflows = discover_workflows(str(tmp_path))
    with TestClient(app_module.app) as c:
        yield c


def test_list_workflows_empty(client):
    resp = client.get("/workflows")
    assert resp.status_code == 200
    data = resp.json()
    assert data["workflows"] == []


def test_validate_not_found(client):
    resp = client.post("/workflows/nonexistent.ga/validate")
    assert resp.status_code == 404


def test_openapi_schema(client):
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()
    assert "Galaxy Workflow Development API" in schema["info"]["title"]
    paths = schema["paths"]
    assert "/workflows" in paths
    assert "/workflows/{workflow_path}/validate" in paths
    assert "/workflows/{workflow_path}/clean" in paths
    assert "/workflows/{workflow_path}/lint" in paths
    assert "/workflows/{workflow_path}/roundtrip" in paths
    assert "/workflows/{workflow_path}/export" in paths
    assert "/workflows/{workflow_path}/convert" in paths
    # old GET-only endpoints removed
    assert "/workflows/{workflow_path}/to-format2" not in paths
    assert "/workflows/{workflow_path}/to-native" not in paths


def test_workflow_endpoints_have_typed_response_schemas(client):
    """All workflow operation endpoints must declare $ref response schemas (no title-only schemas)."""
    resp = client.get("/openapi.json")
    schema = resp.json()
    operation_paths = [
        "/workflows/{workflow_path}/validate",
        "/workflows/{workflow_path}/clean",
        "/workflows/{workflow_path}/lint",
        "/workflows/{workflow_path}/roundtrip",
        "/workflows/{workflow_path}/export",
        "/workflows/{workflow_path}/convert",
    ]
    for path in operation_paths:
        response_schema = schema["paths"][path]["post"]["responses"]["200"]["content"]["application/json"]["schema"]
        assert "$ref" in response_schema, f"{path} response schema has no $ref (got: {response_schema})"


def test_clean_dry_run_does_not_modify_file(workflow_client, tmp_path):
    """POST clean with dry_run=true returns report, file unchanged."""
    wf_path = tmp_path / "synthetic-cat1-stale.ga"
    original_content = wf_path.read_text()

    resp = workflow_client.post("/workflows/synthetic-cat1-stale.ga/clean?dry_run=true")
    assert resp.status_code == 200
    assert wf_path.read_text() == original_content


def test_clean_writes_back_file(workflow_client, tmp_path):
    """POST clean with dry_run=false (default) modifies file on disk."""
    wf_path = tmp_path / "synthetic-cat1-stale.ga"
    original_content = wf_path.read_text()

    resp = workflow_client.post("/workflows/synthetic-cat1-stale.ga/clean")
    assert resp.status_code == 200
    # File should have been written back (content may differ from original)
    new_content = wf_path.read_text()
    # after_content is populated and was written back
    data = resp.json()
    assert data["after_content"] is not None
    assert wf_path.read_text() == data["after_content"]


def test_export_native_to_format2(workflow_client, tmp_path):
    """POST export on a native workflow writes a .gxwf.yml alongside it."""
    resp = workflow_client.post("/workflows/synthetic-cat1-stale.ga/export")
    assert resp.status_code == 200
    data = resp.json()
    assert data["source_format"] == "native"
    assert data["target_format"] == "format2"
    output_path = tmp_path / "synthetic-cat1-stale.gxwf.yml"
    assert output_path.exists(), "Expected output .gxwf.yml to be written"
    assert (tmp_path / "synthetic-cat1-stale.ga").exists(), "Original .ga should still exist"


def test_export_format2_to_native(workflow_client, tmp_path):
    """POST export on a format2 workflow writes a .ga alongside it."""
    resp = workflow_client.post("/workflows/synthetic-cat1.gxwf.yml/export")
    assert resp.status_code == 200
    data = resp.json()
    assert data["source_format"] == "format2"
    assert data["target_format"] == "native"
    output_path = tmp_path / "synthetic-cat1.ga"
    assert output_path.exists(), "Expected output .ga to be written"
    assert (tmp_path / "synthetic-cat1.gxwf.yml").exists(), "Original .gxwf.yml should still exist"


def test_export_dry_run_returns_content_without_writing(workflow_client, tmp_path):
    """POST export with dry_run=true returns content but does not write a file."""
    resp = workflow_client.post("/workflows/synthetic-cat1-stale.ga/export?dry_run=true")
    assert resp.status_code == 200
    data = resp.json()
    assert data["content"] is not None
    assert data["dry_run"] is True
    output_path = tmp_path / "synthetic-cat1-stale.gxwf.yml"
    assert not output_path.exists(), "dry_run should not write output file"


def test_convert_writes_and_removes_original(workflow_client, tmp_path):
    """POST convert writes new file and removes the original."""
    resp = workflow_client.post("/workflows/synthetic-cat1-stale.ga/convert")
    assert resp.status_code == 200
    data = resp.json()
    assert data["source_format"] == "native"
    output_path = tmp_path / "synthetic-cat1-stale.gxwf.yml"
    assert output_path.exists(), "Expected output .gxwf.yml to be written"
    assert not (tmp_path / "synthetic-cat1-stale.ga").exists(), "Original .ga should be removed"


def test_convert_format2_to_native(workflow_client, tmp_path):
    """POST convert on a format2 workflow writes a .ga and removes the original."""
    resp = workflow_client.post("/workflows/synthetic-cat1.gxwf.yml/convert")
    assert resp.status_code == 200
    data = resp.json()
    assert data["source_format"] == "format2"
    assert data["target_format"] == "native"
    output_path = tmp_path / "synthetic-cat1.ga"
    assert output_path.exists(), "Expected output .ga to be written"
    assert not (tmp_path / "synthetic-cat1.gxwf.yml").exists(), "Original .gxwf.yml should be removed"


def test_convert_dry_run_returns_content_without_writing(workflow_client, tmp_path):
    """POST convert with dry_run=true returns content but does not write or delete."""
    resp = workflow_client.post("/workflows/synthetic-cat1-stale.ga/convert?dry_run=true")
    assert resp.status_code == 200
    data = resp.json()
    assert data["content"] is not None
    assert data["dry_run"] is True
    assert not (tmp_path / "synthetic-cat1-stale.gxwf.yml").exists(), "dry_run should not write output"
    assert (tmp_path / "synthetic-cat1-stale.ga").exists(), "dry_run should not remove original"


def test_export_legacy_workflow_returns_422(workflow_client, tmp_path):
    """POST export on a workflow that export_single cannot process returns 422."""
    from unittest.mock import patch

    with patch("gxwf_web.operations.export_single", return_value=None):
        resp = workflow_client.post("/workflows/synthetic-cat1-stale.ga/export")
    assert resp.status_code == 422
