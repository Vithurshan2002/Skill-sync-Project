from uuid import uuid4
import os
import socket
import subprocess
import time

import httpx

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.catalog import seed_categories
from app.config import ROOT, Settings
from app.database import session_factory
from app.main import create_app


@pytest.fixture
def api():
    """Each test uses a new PostgreSQL schema; application tables are never reset."""
    settings = Settings(app_env="testing", ai_enabled=False)
    control = create_engine(settings.database_dsn())
    schema = "skillsync_test_" + uuid4().hex
    with control.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(
        settings.database_dsn(),
        isolation_level="READ COMMITTED",
        connect_args={"options": f"-csearch_path={schema}"},
    )
    try:
        with engine.begin() as connection:
            config = Config(str(ROOT / "alembic.ini"))
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
        with session_factory(engine)() as db:
            seed_categories(db)
        app = create_app(settings, engine=engine)
        with TestClient(app) as client:
            yield client
    finally:
        engine.dispose()
        with control.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        control.dispose()


@pytest.fixture(scope="session")
def real_ai_url(tmp_path_factory):
    """Use the saved models over real HTTP, with an owned process and free port."""
    ai_dir = ROOT.parents[1] / "skillsync-ai-model"
    python = ai_dir / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    url = f"http://127.0.0.1:{port}"
    with (tmp_path_factory.mktemp("ai") / "server.log").open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            [str(python), "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", str(port)],
            cwd=ai_dir,
            stdout=log,
            stderr=log,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        try:
            with httpx.Client(timeout=1, trust_env=False) as client:
                for _ in range(120):
                    if process.poll() is not None:
                        pytest.fail("AI process exited before readiness; inspect its test log.")
                    try:
                        if client.get(url + "/health").status_code == 200:
                            break
                    except httpx.HTTPError:
                        pass
                    time.sleep(0.25)
                else:
                    pytest.fail("Saved models did not become ready within the startup deadline.")
            yield url
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
