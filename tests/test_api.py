"""Basic API tests using FastAPI TestClient."""

import pytest
from fastapi.testclient import TestClient

from galaxy_workflow_dev_webapp.app import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_register_project_not_found(client):
    """Registering a non-existent project should fail gracefully."""
    resp = client.get("/projects/nonexistent/norepo")
    assert resp.status_code == 404


def test_validate_no_project(client):
    resp = client.post("/projects/nonexistent/norepo/workflows/test.ga/validate")
    assert resp.status_code == 404


def test_openapi_schema(client):
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()
    assert "Galaxy Workflow Development API" in schema["info"]["title"]
    paths = schema["paths"]
    assert "/projects" in paths
    assert "/projects/{owner}/{repo}/workflows/{workflow_path}/validate" in paths
    assert "/projects/{owner}/{repo}/workflows/{workflow_path}/clean" in paths
    assert "/projects/{owner}/{repo}/workflows/{workflow_path}/lint" in paths
    assert "/projects/{owner}/{repo}/workflows/{workflow_path}/roundtrip" in paths
    assert "/projects/{owner}/{repo}/workflows/{workflow_path}/export-format2" in paths
