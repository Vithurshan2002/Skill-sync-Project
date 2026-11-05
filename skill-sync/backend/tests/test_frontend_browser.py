"""Opt-in browser coverage against a disposable PostgreSQL schema and SQLite session store."""

import os
import shutil
import socket
import subprocess
import threading
import time
from pathlib import Path

import httpx
import pytest
import uvicorn

from tests.helpers import PASSWORD, account


@pytest.mark.skipif(
    os.getenv("RUN_FRONTEND_BROWSER") != "1",
    reason="Set RUN_FRONTEND_BROWSER=1 to run browser integration.",
)
def test_frontend_browser_against_isolated_postgresql(api, tmp_path, real_ai_url):
    api.app.state.settings.ai_enabled = True
    api.app.state.settings.ai_base_url = real_ai_url
    frontend = Path(__file__).resolve().parents[2] / "frontend"
    php = os.getenv("PHP_BINARY") or shutil.which("php") or "C:/php/php.exe"
    npm = shutil.which("npm.cmd") or shutil.which("npm")
    assert npm, "npm is required"
    _, admin = account(api, "admin", "Integration Administrator")
    backend_socket = socket.socket()
    backend_socket.bind(("127.0.0.1", 0))
    backend_port = backend_socket.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(api.app, log_level="warning"))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [backend_socket]}, daemon=True)
    thread.start()
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        frontend_port = reservation.getsockname()[1]
    database = tmp_path / "frontend.sqlite"
    database.touch()
    frontend_url = f"http://127.0.0.1:{frontend_port}"
    backend_url = f"http://127.0.0.1:{backend_port}"
    env = {
        **os.environ,
        "APP_ENV": "testing",
        "APP_DEBUG": "false",
        "APP_URL": frontend_url,
        "DB_CONNECTION": "sqlite",
        "DB_DATABASE": str(database),
        "DB_URL": "",
        "SESSION_DRIVER": "database",
        "SESSION_DOMAIN": "",
        "SESSION_SECURE_COOKIE": "false",
        "CACHE_STORE": "array",
        "QUEUE_CONNECTION": "sync",
        "FASTAPI_BASE_URL": backend_url,
        "APP_TEST_URL": frontend_url,
        "BACKEND_TEST_URL": backend_url,
        "TEST_ADMIN_EMAIL": admin["email"],
        "TEST_ADMIN_PASSWORD": PASSWORD,
        "APP_CONFIG_CACHE": str(tmp_path / "config.php"),
        "APP_ROUTES_CACHE": str(tmp_path / "routes.php"),
    }
    process = None
    try:
        migration = subprocess.run(
            [php, "artisan", "migrate", "--force", "--no-interaction"],
            cwd=frontend,
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert migration.returncode == 0, migration.stdout + migration.stderr
        with (tmp_path / "frontend-server.log").open("w", encoding="utf-8") as log:
            process = subprocess.Popen(
                [
                    php,
                    "-S",
                    f"127.0.0.1:{frontend_port}",
                    "-t",
                    ".",
                    str(
                        frontend
                        / "vendor/laravel/framework/src/Illuminate/Foundation/resources/server.php"
                    ),
                ],
                cwd=frontend / "public",
                env=env,
                stdout=log,
                stderr=log,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            for _ in range(80):
                try:
                    if httpx.get(frontend_url + "/up", timeout=2).status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(0.25)
            else:
                pytest.fail("Frontend test server did not start.")
            browser_command = [npm, "run", "test:browser"]
            if os.getenv("PLAYWRIGHT_GREP"):
                browser_command.extend(["--", "--grep", os.environ["PLAYWRIGHT_GREP"]])
            result = subprocess.run(
                browser_command,
                cwd=frontend,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=480,
            )
            assert result.returncode == 0, result.stdout + result.stderr
            print(result.stdout)
    finally:
        if process:
            process.terminate()
            process.wait(timeout=15)
        server.should_exit = True
        thread.join(timeout=15)
        backend_socket.close()
