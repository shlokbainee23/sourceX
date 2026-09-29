"""Serve the built workstation locally without changing any API routes or exposing data."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles


FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


def mount_frontend(app: FastAPI, directory: Path = FRONTEND_DIST) -> None:
    """Mount only the build output; hash routes remain entirely inside the browser."""
    if not (directory / "index.html").is_file():
        raise RuntimeError("Frontend build missing. Run npm ci and npm run build in frontend/ first.")
    app.mount("/workstation", StaticFiles(directory=directory, html=True), name="workstation")
