from logging.config import fileConfig

from alembic import context

from src.backend.config import settings
from src.backend.db import engine
from src.shared.db.app_models import SCHEMA, AppBase

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = AppBase.metadata
VERSION_TABLE = "alembic_version_app"


def include_name(name, type_, parent_names):
    if type_ == "schema":
        return name == SCHEMA
    return True


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        include_schemas=True,
        include_name=include_name,
        version_table=VERSION_TABLE,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
            include_name=include_name,
            version_table=VERSION_TABLE,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
