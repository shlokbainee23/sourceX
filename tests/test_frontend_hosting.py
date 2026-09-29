"""Check public build serving stays separate from authenticated APIs and private files."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.frontend import mount_frontend


def test_mount_requires_a_built_frontend(tmp_path):
    with pytest.raises(RuntimeError, match="Frontend build missing"):
        mount_frontend(FastAPI(), tmp_path)


def test_only_build_files_are_public(tmp_path):
    build = tmp_path / "dist"
    build.mkdir()
    (build / "index.html").write_text('<script src="./assets/app.js"></script>')
    (build / "assets").mkdir()
    (build / "assets" / "app.js").write_text("console.log('workstation')")
    (tmp_path / "private.txt").write_text("not public")
    app = FastAPI()

    @app.get("/api/health")
    def health():
        return {"status": "HEALTHY"}

    mount_frontend(app, build)
    with TestClient(app) as client:
        assert client.get("/workstation").status_code == 200
        assert './assets/app.js' in client.get("/workstation/").text
        assert client.get("/workstation/assets/app.js").status_code == 200
        assert client.get("/api/health").json() == {"status": "HEALTHY"}
        assert client.get("/api/missing").status_code == 404
        assert client.post("/api/auth/login", json={}).status_code == 404
        for path in ("/workstation/assets/missing.js", "/workstation/private.txt",
                     "/workstation/%2e%2e/private.txt", "/workstation/%2e%2e/backend/data/sih26237.sqlite"):
            assert client.get(path).status_code == 404
