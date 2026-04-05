"""Basic API tests using FastAPI TestClient."""

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
