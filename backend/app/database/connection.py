"""Database Connection and Session Manager.

Demonstrates:
- Singleton Database Connection Pattern
- Multi-database support: SQLite (local development) and PostgreSQL (QA/Prod/Docker)
- SQLAlchemy 2.0 Engine & SessionFactory configuration
- Automatic Foreign Key enforcement for SQLite
- Context managers supporting ACID transactions (Atomicity & Rollback)
"""

from threading import Lock
from typing import Generator, Optional
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger()

# Declarative base for ORM models
Base = declarative_base()


class DatabaseConnectionManager:
    """Thread-safe Singleton Database Connection Manager."""

    _instance: Optional["DatabaseConnectionManager"] = None
    _lock: Lock = Lock()

    def __new__(cls) -> "DatabaseConnectionManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(DatabaseConnectionManager, cls).__new__(cls)
                cls._instance._setup_engine()
            return cls._instance

    def _setup_engine(self) -> None:
        settings = get_settings()
        db_url = settings.DATABASE_URL

        logger.info("Initializing database connection with type: %s", settings.DB_TYPE)

        if "sqlite" in db_url.lower():
            # SQLite configuration
            self._engine = create_engine(
                db_url,
                connect_args={"check_same_thread": False},
                echo=settings.DEBUG,
            )
            # Enforce foreign key constraints in SQLite
            @event.listens_for(self._engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()
        else:
            # PostgreSQL configuration with connection pooling
            self._engine = create_engine(
                db_url,
                pool_pre_ping=True,
                pool_size=10,
                max_overflow=20,
                echo=settings.DEBUG,
            )

        self._session_factory = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self._engine,
        )

    @property
    def engine(self):
        return self._engine

    @property
    def session_factory(self) -> sessionmaker:
        return self._session_factory

    def get_session(self) -> Session:
        """Create a new database session."""
        return self._session_factory()

    def create_tables(self) -> None:
        """Creates all registered ORM tables."""
        Base.metadata.create_all(bind=self._engine)
        logger.info("Database schemas and tables verified/created successfully.")


def get_db() -> Generator[Session, None, None]:
    """FastAPI Dependency for database session management.

    Ensures session is properly closed after request cycle completes (Durability).
    """
    manager = DatabaseConnectionManager()
    session: Session = manager.get_session()
    try:
        yield session
    except Exception as exc:
        logger.error("Database transaction rolled back due to error: %s", exc)
        session.rollback()
        raise
    finally:
        session.close()
