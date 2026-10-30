import io
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateSchema, DropSchema

from app.core.config import settings
from app.db.base import Base
from app.db.url import parse_database_url
from app.models.user import User


BACKEND = Path(__file__).resolve().parents[1]


def migration_config() -> Config:
    return Config(str(BACKEND / "alembic.ini"))


class MigrationConfigurationTests(unittest.TestCase):
    def test_neon_url_selects_installed_driver_and_preserves_credentials_and_tls(self):
        url = parse_database_url(
            "postgresql://member:p%40ss%25word@database.neon.tech/nri_platform?sslmode=require"
        )
        self.assertEqual(url.drivername, "postgresql+psycopg2")
        self.assertEqual(url.password, "p@ss%word")
        self.assertEqual(url.query["sslmode"], "require")
        self.assertEqual(url.database, "nri_platform")
        self.assertEqual(
            parse_database_url("postgresql+psycopg2://localhost/test").drivername,
            "postgresql+psycopg2",
        )
        self.assertEqual(parse_database_url("sqlite://").drivername, "sqlite")

    def test_offline_sql_requires_only_database_url(self):
        output = io.StringIO()
        config = migration_config()
        config.output_buffer = output
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://unused/unused"}, clear=True):
            command.upgrade(config, "head", sql=True)
        sql = output.getvalue()
        self.assertIn("CREATE TABLE users", sql)
        self.assertIn("CREATE TABLE ride_bookings", sql)
        self.assertIn("ix_ride_requests_pickup_h3", sql)
        self.assertIn("INSERT INTO alembic_version", sql)
        self.assertEqual(sql.count("CONSTRAINT post_category CHECK"), 1)
        self.assertEqual(sql.count("CONSTRAINT post_type CHECK"), 1)
        self.assertEqual(sql.count("CONSTRAINT post_reaction_type CHECK"), 1)

    def test_app_import_does_not_connect_or_create_tables(self):
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "from unittest.mock import patch\n"
                "with patch('sqlalchemy.engine.Engine.connect', "
                "side_effect=AssertionError('Startup must not access the database')):\n"
                "    from app.main import app\n"
                "    from sqlalchemy.orm import configure_mappers\n"
                "    configure_mappers()\n"
                "    assert app.title == 'NRI Platform'\n",
            ],
            cwd=BACKEND,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


@unittest.skipUnless(
    os.getenv("MIGRATION_TEST_POSTGRES") == "1",
    "Set MIGRATION_TEST_POSTGRES=1 to test in an isolated PostgreSQL schema",
)
class PostgreSQLMigrationTests(unittest.TestCase):
    def test_upgrade_repeat_check_and_downgrade(self):
        engine = create_engine(parse_database_url(settings.DATABASE_URL))
        self.addCleanup(engine.dispose)
        self.assertEqual(engine.dialect.name, "postgresql")
        schema = "migration_test_" + uuid4().hex
        with engine.begin() as connection:
            connection.execute(CreateSchema(schema))
        try:
            with engine.connect() as connection:
                connection.execute(text(f'SET search_path TO "{schema}"'))
                connection.commit()
                config = migration_config()
                config.attributes["connection"] = connection
                command.upgrade(config, "head")
                self.assertEqual(
                    set(inspect(connection).get_table_names()),
                    set(Base.metadata.tables) | {"alembic_version"},
                )
                self.assertEqual(
                    connection.scalar(text("SELECT version_num FROM alembic_version")),
                    "0001",
                )
                indexes = {index["name"] for index in inspect(connection).get_indexes("ride_requests")}
                self.assertIn("ix_ride_requests_pickup_h3", indexes)
                self.assertIn("ix_ride_requests_status_pickup_id", indexes)
                for table, names in (
                    ("posts", {"post_category", "post_type"}),
                    ("post_reactions", {"post_reaction_type"}),
                ):
                    constraints = inspect(connection).get_check_constraints(table)
                    for name in names:
                        self.assertEqual(sum(item["name"] == name for item in constraints), 1)
                connection.commit()
                user_id = uuid4()
                with Session(connection) as session:
                    session.add(User(
                        id=user_id, email="migration@example.test", name="Migration test",
                        provider="test", provider_id=str(user_id),
                    ))
                    session.commit()
                command.upgrade(config, "head")
                self.assertEqual(connection.scalar(select(User.id)), user_id)
                command.check(config)
                connection.commit()
                command.downgrade(config, "base")
                self.assertEqual(inspect(connection).get_table_names(), ["alembic_version"])
                connection.commit()
                command.upgrade(config, "head")
                command.check(config)
                connection.commit()
        finally:
            with engine.begin() as connection:
                connection.execute(DropSchema(schema, cascade=True))
