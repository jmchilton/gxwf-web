"""Basic API tests using FastAPI TestClient."""

import pytest
from fastapi.testclient import TestClient

from gxwf_web import app as app_module


@pytest.fixture
def client(tmp_path):
    app_module.configure(str(tmp_path))
    app_module._tool_info = None
    app_module._workflows = []
    with TestClient(app_module.app) as c:
        yield c


def test_list_workflows_empty(client):
    resp = client.get("/workflows")
    assert resp.status_code == 200
    data = resp.json()
    assert data["workflows"] == []


def test_validate_not_found(client):
    resp = client.get("/workflows/nonexistent.ga/validate")
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
    assert "/workflows/{workflow_path}/to-format2" in paths
    assert "/workflows/{workflow_path}/to-native" in paths


def test_workflow_endpoints_have_typed_response_schemas(client):
    """All workflow operation endpoints must declare $ref response schemas (no title-only schemas)."""
    resp = client.get("/openapi.json")
    schema = resp.json()
    operation_paths = [
        "/workflows/{workflow_path}/validate",
        "/workflows/{workflow_path}/clean",
        "/workflows/{workflow_path}/lint",
        "/workflows/{workflow_path}/roundtrip",
        "/workflows/{workflow_path}/to-format2",
        "/workflows/{workflow_path}/to-native",
    ]
    for path in operation_paths:
        response_schema = schema["paths"][path]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
        assert "$ref" in response_schema, f"{path} response schema has no $ref (got: {response_schema})"
