import pytest

from app.config import INTEGRATION_DATABASE, Settings, require_integration_database


@pytest.mark.parametrize("name", ["skillsync", "skillsync_backend", "postgres", "other"])
def test_original_databases_cannot_be_connected(name):
    with pytest.raises(ValueError, match="Existing project databases are blocked"):
        Settings(_env_file=None, db_name=name, database_url=None).database_dsn()


def test_database_url_cannot_bypass_isolation():
    with pytest.raises(ValueError, match="Existing project databases are blocked"):
        Settings(
            _env_file=None,
            db_name=INTEGRATION_DATABASE,
            database_url="postgresql+psycopg://localhost/skillsync",
        ).database_dsn()


def test_isolated_postgresql_database_is_accepted():
    settings = Settings(_env_file=None, db_name=INTEGRATION_DATABASE, database_url=None)
    assert settings.database_dsn().database == INTEGRATION_DATABASE


def test_external_migration_connection_is_checked():
    with pytest.raises(ValueError):
        require_integration_database("postgresql+psycopg://localhost/skillsync")
