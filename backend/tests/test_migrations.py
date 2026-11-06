import io
import os
from pathlib import Path
import subprocess
import sys
import unittest
from datetime import date, datetime, timedelta
from unittest.mock import patch
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import MetaData, Table, create_engine, inspect, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateSchema, DropSchema

from app.core.config import settings
from app.db.base import Base
from app.db.url import parse_database_url
from app.models.user import User
from app.models.post import Post, PostCategory, PostStatus
from app.models.housing import HousingPost
from app.schemas.housing import HousingContent, HousingSearch
from app.api.housing import search_housing


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
        self.assertEqual(sql.count("CONSTRAINT post_category CHECK"), 6)
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
                command.upgrade(config, "0001")
                user_id = uuid4()
                post_id = uuid4()
                with Session(connection) as session:
                    session.add(User(
                        id=user_id, email="migration@example.test", name="Migration test",
                        provider="test", provider_id=str(user_id),
                    ))
                    session.flush()
                    session.execute(text(
                        "INSERT INTO posts (id, user_id, title, description, category, post_type, "
                        "location_id, location, country_code, postal_code, state, city, latitude, longitude, h3_cell_id, created_at) "
                        "VALUES (:id, :user_id, 'Community game', 'Weekend sports', 'GENERAL', 'DISCUSSION', "
                        "'test', 'Fremont', 'US', '94538', 'CA', 'Fremont', 37.55, -121.98, 'test', CURRENT_TIMESTAMP)"
                    ), {"id": post_id, "user_id": user_id})
                    session.commit()
                with self.assertRaises(IntegrityError):
                    with connection.begin_nested():
                        connection.execute(text("UPDATE posts SET category = 'SPORTS'"))
                connection.commit()
                command.upgrade(config, "0002")
                connection.execute(text("UPDATE posts SET category = 'RIDES'"))
                connection.commit()
                command.upgrade(config, "0011")
                housing_id = uuid4()
                connection.execute(Table("housing_posts", MetaData(), autoload_with=connection).insert().values(
                        id=housing_id, owner_id=user_id, city="Fremont", country_code="US",
                        created_at=datetime.now(),
                        **HousingContent(
                            title="Migration housing", description="Housing migration retention test",
                            kind="LISTING", room_type="PRIVATE", arrangement="HOUSEHOLD",
                            stay_type="LONG_TERM", area="Central",
                            amount=950, currency="USD", price_period="MONTH",
                            available_from=date.today(),
                        ).model_dump(exclude={"household_languages"}),
                        expires_at=datetime.now() + timedelta(days=30),
                ))
                connection.commit()
                command.upgrade(config, "head")
                self.assertEqual(connection.scalar(select(HousingPost.title)), "Migration housing")
                self.assertEqual(connection.scalar(select(HousingPost.amount)), 950)
                self.assertIsNone(connection.scalar(select(HousingPost.location_id)))
                connection.commit()
                command.downgrade(config, "0007")
                self.assertNotIn("location_id", {column["name"] for column in inspect(connection).get_columns("housing_posts")})
                self.assertEqual(connection.scalar(text("SELECT title FROM housing_posts WHERE id=:id"), {"id": housing_id}), "Migration housing")
                connection.commit()
                command.upgrade(config, "head")
                with self.assertRaises(DBAPIError):
                    command.downgrade(config, "0006")
                connection.rollback()
                self.assertEqual(connection.scalar(select(HousingPost.id)), housing_id)
                self.assertEqual(connection.scalar(text("SELECT version_num FROM alembic_version")), "0015")
                self.assertIsNone(connection.scalar(select(HousingPost.location_id)))
                self.assertIn("ix_housing_posts_h3_cell_id", {index["name"] for index in inspect(connection).get_indexes("housing_posts")})
                with self.assertRaises(IntegrityError):
                    with connection.begin_nested():
                        connection.execute(text("UPDATE housing_posts SET location_id='partial'"))
                connection.execute(text(
                    "UPDATE housing_posts SET location_id='test', location='Fremont', latitude=37.55, "
                    "longitude=-121.98, h3_cell_id='8828342a07fffff', state='CA', postal_code='94538'"
                ))
                connection.commit()
                with self.assertRaises(DBAPIError):
                    command.downgrade(config, "0007")
                connection.rollback()
                self.assertEqual(connection.scalar(select(HousingPost.location_id)), "test")
                for assignment in ("latitude=91", "longitude=-181", "postal_code=NULL"):
                    with self.subTest(assignment=assignment), self.assertRaises(IntegrityError):
                        with connection.begin_nested():
                            connection.execute(text(f"UPDATE housing_posts SET {assignment}"))
                with self.assertRaises(IntegrityError):
                    with connection.begin_nested():
                        connection.execute(text("UPDATE housing_posts SET amount = -1"))
                connection.execute(HousingPost.__table__.delete())
                connection.commit()
                self.assertEqual(
                    set(inspect(connection).get_table_names()),
                    set(Base.metadata.tables) | {"alembic_version"},
                )
                self.assertEqual(
                    connection.scalar(text("SELECT version_num FROM alembic_version")),
                    "0015",
                )
                self.assertEqual(connection.scalar(select(Post.status)), PostStatus.ACTIVE)
                connection.commit()
                with self.assertRaises(IntegrityError):
                    with connection.begin_nested():
                        connection.execute(text("UPDATE posts SET status = 'CLOSED'"))
                connection.commit()
                connection.execute(text("UPDATE posts SET post_type = 'OFFER', status = 'CLOSED'"))
                connection.commit()
                with self.assertRaises(DBAPIError):
                    command.downgrade(config, "0004")
                connection.rollback()
                self.assertEqual(connection.scalar(select(Post.status)), PostStatus.CLOSED)
                self.assertEqual(connection.scalar(text("SELECT version_num FROM alembic_version")), "0015")
                connection.execute(text("UPDATE posts SET status = 'ACTIVE'"))
                connection.commit()
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
                self.assertEqual(connection.scalar(select(Post.category)), PostCategory.TRAVEL)
                self.assertEqual(connection.scalar(select(Post.id)), post_id)
                connection.execute(text("UPDATE posts SET category = 'RIDES_CARPOOL'"))
                connection.commit()
                with self.assertRaises(DBAPIError):
                    command.downgrade(config, "0008")
                connection.rollback()
                self.assertEqual(connection.scalar(select(Post.category)), PostCategory.RIDES_CARPOOL)
                self.assertEqual(connection.scalar(text("SELECT version_num FROM alembic_version")), "0015")
                connection.execute(text("UPDATE posts SET category = 'HOUSEHOLD_HELP'"))
                connection.commit()
                with self.assertRaises(DBAPIError):
                    command.downgrade(config, "0012")
                connection.rollback()
                self.assertEqual(connection.scalar(select(Post.category)), PostCategory.HOUSEHOLD_HELP)
                connection.execute(text("UPDATE posts SET category = 'GENERAL'"))
                connection.commit()
                with self.assertRaises(IntegrityError):
                    with connection.begin_nested():
                        connection.execute(text("UPDATE posts SET category = 'RIDES'"))
                connection.commit()
                connection.execute(text("UPDATE posts SET category = 'PARKING'"))
                connection.commit()
                self.assertEqual(connection.scalar(select(Post.category)), PostCategory.PARKING)
                self.assertEqual(connection.scalar(select(Post.id)), post_id)
                connection.commit()
                with self.assertRaises(IntegrityError):
                    command.downgrade(config, "0003")
                connection.rollback()
                self.assertEqual(
                    connection.scalar(text("SELECT version_num FROM alembic_version")), "0015"
                )
                self.assertEqual(connection.scalar(select(Post.category)), PostCategory.PARKING)
                connection.execute(text("UPDATE posts SET category = 'TRAVEL'"))
                connection.commit()
                command.downgrade(config, "0003")
                self.assertEqual(connection.scalar(select(Post.id)), post_id)
                connection.commit()
                command.downgrade(config, "0002")
                self.assertEqual(
                    connection.scalar(text("SELECT category FROM posts WHERE id = :id"), {"id": post_id}),
                    "RIDES",
                )
                self.assertEqual(connection.scalar(select(Post.id)), post_id)
                connection.commit()
                command.upgrade(config, "head")
                self.assertEqual(connection.scalar(select(Post.category)), PostCategory.TRAVEL)
                connection.execute(text("UPDATE posts SET category = 'SPORTS'"))
                connection.commit()
                command.upgrade(config, "head")
                self.assertEqual(connection.scalar(select(User.id)), user_id)
                command.check(config)
                connection.commit()
                with self.assertRaises(IntegrityError):
                    command.downgrade(config, "0001")
                connection.rollback()
                self.assertEqual(
                    connection.scalar(text("SELECT version_num FROM alembic_version")), "0015"
                )
                self.assertEqual(connection.scalar(select(Post.category)), PostCategory.SPORTS)
                connection.execute(text("UPDATE posts SET category = 'GENERAL'"))
                connection.commit()
                command.downgrade(config, "0001")
                self.assertEqual(connection.scalar(select(Post.id)), post_id)
                connection.commit()
                command.upgrade(config, "head")
                command.downgrade(config, "base")
                self.assertEqual(inspect(connection).get_table_names(), ["alembic_version"])
                connection.commit()
                command.upgrade(config, "head")
                command.check(config)
                connection.commit()
        finally:
            with engine.begin() as connection:
                connection.execute(DropSchema(schema, cascade=True))

    def test_household_languages_upgrade_search_and_guarded_downgrade(self):
        engine = create_engine(parse_database_url(settings.DATABASE_URL))
        self.addCleanup(engine.dispose)
        schema = "migration_test_" + uuid4().hex
        with engine.begin() as connection:
            connection.execute(CreateSchema(schema))
        try:
            with engine.connect() as connection:
                connection.execute(text(f'SET search_path TO "{schema}"'))
                connection.commit()
                config = migration_config()
                config.attributes["connection"] = connection
                command.upgrade(config, "0013")
                user_id, old_id = uuid4(), uuid4()
                with Session(connection) as db:
                    db.add(User(id=user_id, email="languages@example.test", name="Languages test",
                                provider="test", provider_id=str(user_id)))
                    db.commit()
                content = HousingContent(
                    title="Existing household", description="Languages migration retention test",
                    kind="LISTING", room_type="PRIVATE", arrangement="HOUSEHOLD",
                    stay_type="LONG_TERM", amount=950, currency="USD", price_period="MONTH",
                    available_from=date.today(), kitchen="VEGETARIAN",
                ).model_dump(exclude={"household_languages"})
                old_table = Table("housing_posts", MetaData(), autoload_with=connection)
                connection.execute(old_table.insert().values(
                    id=old_id, owner_id=user_id, city="Fremont", country_code="US", **content,
                    created_at=datetime.now(),
                    expires_at=datetime.now() + timedelta(days=30),
                ))
                connection.commit()
                command.upgrade(config, "head")
                self.assertEqual(connection.scalar(select(HousingPost.household_languages)), [])
                self.assertEqual(connection.scalar(select(HousingPost.title)), "Existing household")
                connection.commit()
                command.upgrade(config, "head")
                command.check(config)
                connection.commit()
                with Session(connection) as db:
                    user = db.get(User, user_id)
                    assert user is not None
                    first = HousingPost(
                        owner_id=user_id, city="Fremont", country_code="US", **content,
                        household_languages=["en", "gu"],
                        created_at=datetime.now() - timedelta(seconds=2),
                        expires_at=datetime.now() + timedelta(days=30),
                    )
                    second = HousingPost(
                        owner_id=user_id, city="Fremont", country_code="US", **content,
                        household_languages=["te"],
                        created_at=datetime.now() - timedelta(seconds=1),
                        expires_at=datetime.now() + timedelta(days=30),
                    )
                    private = HousingPost(
                        owner_id=user_id, city="Fremont", country_code="US",
                        **{**content, "is_private": True}, household_languages=["gu"],
                        expires_at=datetime.now() + timedelta(days=30),
                    )
                    db.add_all([first, second, private])
                    db.commit()
                    all_results = search_housing(HousingSearch(), db, user)
                    self.assertEqual({row.id for row in all_results.items}, {old_id, first.id, second.id})
                    filters = {"household_languages": ["gu", "te"], "kitchen": "VEGETARIAN", "limit": 1}
                    page1 = search_housing(HousingSearch(**filters), db, user)
                    page2 = search_housing(HousingSearch(**filters, offset=1), db, user)
                    self.assertEqual([row.id for row in page1.items], [second.id])
                    self.assertTrue(page1.has_more)
                    self.assertEqual([row.id for row in page2.items], [first.id])
                    self.assertFalse(page2.has_more)
                    self.assertEqual(search_housing(HousingSearch(household_languages=["kn"]), db, user).items, [])
                    self.assertEqual(search_housing(HousingSearch(household_languages=["gu"], kitchen="UNRESTRICTED"), db, user).items, [])
                connection.commit()
                with self.assertRaises(DBAPIError):
                    command.downgrade(config, "0013")
                connection.rollback()
                self.assertEqual(connection.scalar(text("SELECT version_num FROM alembic_version")), "0015")
                self.assertEqual(connection.scalar(text("SELECT count(*) FROM housing_posts WHERE household_languages::jsonb <> '[]'::jsonb")), 3)
                connection.execute(text("UPDATE housing_posts SET household_languages = '[]'"))
                connection.commit()
                command.downgrade(config, "0013")
                self.assertNotIn("household_languages", {column["name"] for column in inspect(connection).get_columns("housing_posts")})
                self.assertEqual(connection.scalar(text("SELECT count(*) FROM housing_posts")), 4)
                connection.commit()
                command.upgrade(config, "head")
                command.check(config)
                connection.commit()
        finally:
            with engine.begin() as connection:
                connection.execute(DropSchema(schema, cascade=True))

    def test_hall_space_upgrade_retention_search_and_guarded_downgrade(self):
        engine = create_engine(parse_database_url(settings.DATABASE_URL))
        self.addCleanup(engine.dispose)
        schema = "migration_test_" + uuid4().hex
        with engine.begin() as connection:
            connection.execute(CreateSchema(schema))
        try:
            with engine.connect() as connection:
                connection.execute(text(f'SET search_path TO "{schema}"'))
                connection.commit()
                config = migration_config()
                config.attributes["connection"] = connection
                command.upgrade(config, "0014")
                user_id = uuid4()
                with Session(connection) as db:
                    user = User(id=user_id, email="hall@example.test", name="Hall test",
                                provider="test", provider_id=str(user_id))
                    db.add(user)
                    db.commit()
                    content = HousingContent(
                        title="Existing private room", description="Hall migration retention test",
                        kind="LISTING", room_type="PRIVATE", arrangement="HOUSEHOLD",
                        stay_type="LONG_TERM", amount=950, currency="USD", price_period="MONTH",
                        available_from=date.today(), bedroom_count=2, household_languages=["es"],
                    ).model_dump()
                    original = HousingPost(
                        owner_id=user_id, city="Fremont", country_code="US", **content,
                        expires_at=datetime.now() + timedelta(days=30),
                    )
                    db.add(original)
                    db.commit()
                    original_id = original.id
                with self.assertRaises(IntegrityError):
                    with connection.begin_nested():
                        connection.execute(text("UPDATE housing_posts SET room_type='HALL'"))
                connection.commit()
                command.upgrade(config, "head")
                command.upgrade(config, "head")
                command.check(config)
                connection.commit()
                with Session(connection) as db:
                    user = db.get(User, user_id)
                    assert user is not None
                    retained = db.get(HousingPost, original_id)
                    assert retained is not None
                    self.assertEqual(retained.room_type, "PRIVATE")
                    self.assertEqual(retained.bedroom_count, 2)
                    self.assertEqual(retained.household_languages, ["es"])
                    hall = HousingPost(
                        owner_id=user_id, city="Fremont", country_code="US",
                        **{**content, "room_type": "HALL"},
                        expires_at=datetime.now() + timedelta(days=30),
                    )
                    db.add(hall)
                    db.commit()
                    self.assertEqual(
                        [row.id for row in search_housing(HousingSearch(room_type="HALL", min_bedrooms=2), db, user).items],
                        [hall.id],
                    )
                    hall.is_private = True
                    hall.status = "ARCHIVED"
                    db.commit()
                connection.commit()
                with self.assertRaises(DBAPIError):
                    command.downgrade(config, "0014")
                connection.rollback()
                self.assertEqual(connection.scalar(text("SELECT version_num FROM alembic_version")), "0015")
                self.assertEqual(connection.scalar(text("SELECT count(*) FROM housing_posts WHERE room_type='HALL'")), 1)
                connection.execute(text("UPDATE housing_posts SET room_type='SHARED' WHERE room_type='HALL'"))
                connection.commit()
                command.downgrade(config, "0014")
                self.assertEqual(connection.scalar(text("SELECT count(*) FROM housing_posts")), 2)
                self.assertEqual(connection.scalar(text("SELECT bedroom_count FROM housing_posts WHERE id=:id"), {"id": original_id}), 2)
                with self.assertRaises(IntegrityError):
                    with connection.begin_nested():
                        connection.execute(text("UPDATE housing_posts SET room_type='HALL'"))
                connection.commit()
                command.upgrade(config, "head")
                command.check(config)
                connection.commit()
        finally:
            with engine.begin() as connection:
                connection.execute(DropSchema(schema, cascade=True))
