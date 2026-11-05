from logging.config import fileConfig

from alembic import context

from app.config import Settings, require_integration_database
from app.database import make_engine
from app.models import Base

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)
target_metadata = Base.metadata

if context.is_offline_mode():
    context.configure(
        url=Settings().database_dsn(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    provided_connection = config.attributes.get("connection")

    def run(connection):
        require_integration_database(connection.engine.url)
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()

    if provided_connection is not None:
        run(provided_connection)
    else:
        engine = make_engine(Settings())
        with engine.connect() as connection:
            run(connection)
        engine.dispose()
