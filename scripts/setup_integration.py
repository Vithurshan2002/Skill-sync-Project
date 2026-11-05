"""Provision only the isolated SkillSync test database and configure this checkout.

Run with project/backend/.venv/Scripts/python.exe. Existing backend .env
credentials are used only against PostgreSQL's maintenance database to create a
new restricted role and database. Original application databases are never opened.
"""
from pathlib import Path
import argparse
import base64
import getpass
import secrets
import sys

import psycopg
from psycopg import sql
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "project" / "backend"
FRONTEND = ROOT / "project" / "frontend"
DATABASE = "skillsync_integration_test"
ROLE = "skillsync_integration_app"


def update_env(path, updates):
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    result = []
    remaining = dict(updates)
    for line in lines:
        key = line.split("=", 1)[0].strip()
        if key in updates:
            if key in remaining:
                result.append(f"{key}={remaining.pop(key)}")
        else:
            result.append(line)
    result.extend(f"{key}={value}" for key, value in remaining.items())
    path.write_text("\n".join(result) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--admin-user", help="PostgreSQL administrator; prompts for password")
    args = parser.parse_args()
    values = dotenv_values(BACKEND / ".env")
    host = values.get("DB_HOST") or "127.0.0.1"
    port = int(values.get("DB_PORT") or 5432)
    already_configured = (
        values.get("DB_NAME") == DATABASE and values.get("DB_USER") == ROLE
    )
    if already_configured and not args.admin_user:
        password = values.get("DB_PASSWORD") or ""
        with psycopg.connect(host=host, port=port, user=ROLE, password=password,
                             dbname=DATABASE, connect_timeout=5) as connection:
            current = connection.execute("SELECT current_database(), current_user").fetchone()
            if current != (DATABASE, ROLE):
                raise RuntimeError("Unexpected database identity; setup stopped.")
        print("Isolated PostgreSQL database already configured; existing data preserved.")
    else:
        admin_user = args.admin_user or values.get("DB_USER") or "postgres"
        admin_password = (
            getpass.getpass("PostgreSQL administrator password: ")
            if args.admin_user else values.get("DB_PASSWORD") or ""
        )
        password = secrets.token_urlsafe(32)
        with psycopg.connect(host=host, port=port, user=admin_user, password=admin_password,
                             dbname="postgres", connect_timeout=5, autocommit=True) as connection:
            database_exists = connection.execute(
                "SELECT 1 FROM pg_database WHERE datname=%s", (DATABASE,)
            ).fetchone()
            role_exists = connection.execute(
                "SELECT 1 FROM pg_roles WHERE rolname=%s", (ROLE,)
            ).fetchone()
            if database_exists or role_exists:
                raise RuntimeError(
                    "The integration database or role already exists but this checkout is not "
                    "configured for it. Setup refuses to replace data or reset credentials."
                )
            connection.execute(sql.SQL(
                "CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION"
            ).format(sql.Identifier(ROLE), sql.Literal(password)))
            connection.execute(sql.SQL("CREATE DATABASE {} OWNER {}").format(
                sql.Identifier(DATABASE), sql.Identifier(ROLE)
            ))
        print(f"Created isolated PostgreSQL database {DATABASE} and restricted application role.")
    update_env(BACKEND / ".env", {
        "APP_ENV": "local", "DB_HOST": host, "DB_PORT": port,
        "DB_NAME": DATABASE, "DB_USER": ROLE, "DB_PASSWORD": password,
        "DATABASE_URL": "", "AI_ENABLED": "true",
        "AI_BASE_URL": "http://127.0.0.1:8102", "AI_TIMEOUT_SECONDS": "15",
    })
    frontend_values = dotenv_values(FRONTEND / ".env")
    isolated_sqlite = FRONTEND / "database" / "integration-testing.sqlite"
    isolated_sqlite.touch(exist_ok=True)
    updates = {
        "APP_NAME": '"SkillSync Testing"', "APP_URL": "http://127.0.0.1:8100",
        "DB_CONNECTION": "sqlite", "DB_DATABASE": f'"{isolated_sqlite.as_posix()}"',
        "DB_URL": "", "SESSION_COOKIE": "skillsync_integration_test_session",
        "FASTAPI_BASE_URL": "http://127.0.0.1:8101", "SKILLSYNC_API_TIMEOUT": "25",
        "SKILLSYNC_API_CONNECT_TIMEOUT": "3",
    }
    if (frontend_values.get("SESSION_COOKIE") != "skillsync_integration_test_session"
            or not frontend_values.get("APP_KEY")):
        updates["APP_KEY"] = "base64:" + base64.b64encode(secrets.token_bytes(32)).decode()
    update_env(FRONTEND / ".env", updates)
    print("Frontend configured with its own SQLite identity/session store and cookie.")
    print("Next: migrate backend and frontend, then run start-skillsync.ps1.")


if __name__ == "__main__":
    try:
        main()
    except psycopg.Error:
        print("PostgreSQL setup failed. Check service, credentials, and creation privileges. "
              "Credentials were not displayed.", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
