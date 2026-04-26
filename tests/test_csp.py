"""Tests for CSP header construction and application to static/SPA responses."""

import pytest
from fastapi.testclient import TestClient

from gxwf_web import app as app_module
from gxwf_web.csp import (
    build_csp_header,
    build_monaco_csp_header,
)


def test_build_csp_header_baseline():
    header = build_csp_header()
    assert "default-src 'self'" in header
    assert "script-src 'self' 'wasm-unsafe-eval'" in header
    assert "worker-src 'self' blob:" in header
    assert "frame-src 'self' blob:" in header
    assert "connect-src 'self' https://toolshed.g2.bx.psu.edu" in header
    assert "style-src 'self' 'unsafe-inline'" in header
    assert "font-src 'self' data:" in header
    assert "img-src 'self' data:" in header
    assert "'unsafe-eval'" not in header


def test_build_csp_header_extra_connect_src():
    header = build_csp_header(["https://example.invalid"])
    assert "https://example.invalid" in header
    assert "https://toolshed.g2.bx.psu.edu" in header


def test_build_monaco_csp_header_permissive():
    header = build_monaco_csp_header()
    assert "default-src 'self' blob: data:" in header
    assert "'unsafe-eval'" in header
    assert "'unsafe-inline'" in header
    assert "img-src 'self' data: blob:" in header


@pytest.fixture
def ui_client(tmp_path):
    ui = tmp_path / "ui"
    (ui / "assets").mkdir(parents=True)
    (ui / "index.html").write_text("<html></html>")
    (ui / "assets" / "app.js").write_text("/* app */")
    (ui / "monaco").mkdir()
    (ui / "monaco" / "worker.js").write_text("/* worker */")

    workspace = tmp_path / "workspace"
    workspace.mkdir()

    app_module.configure(str(workspace))
    app_module.configure_ui(str(ui))
    app_module.configure_extra_connect_src([])
    app_module._tool_info = None
    app_module._workflows = []
    with TestClient(app_module.app) as c:
        yield c


def test_spa_index_has_baseline_csp(ui_client):
    resp = ui_client.get("/")
    assert resp.status_code == 200
    csp = resp.headers.get("content-security-policy")
    assert csp is not None
    assert "'unsafe-eval'" not in csp
    assert "script-src 'self' 'wasm-unsafe-eval'" in csp


def test_monaco_asset_has_permissive_csp(ui_client):
    resp = ui_client.get("/monaco/worker.js")
    assert resp.status_code == 200
    csp = resp.headers.get("content-security-policy")
    assert csp is not None
    assert "'unsafe-eval'" in csp


def test_spa_fallback_has_baseline_csp(ui_client):
    resp = ui_client.get("/some/deep/route")
    assert resp.status_code == 200
    csp = resp.headers.get("content-security-policy")
    assert csp is not None
    assert "'unsafe-eval'" not in csp


def test_extra_connect_src_applied(ui_client):
    app_module.configure_extra_connect_src(["https://example.invalid"])
    try:
        resp = ui_client.get("/")
        csp = resp.headers.get("content-security-policy")
        assert "https://example.invalid" in csp
    finally:
        app_module.configure_extra_connect_src([])
