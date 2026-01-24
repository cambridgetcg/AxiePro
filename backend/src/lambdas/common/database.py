"""
Database Connection Management for Lambda Functions

Provides sync psycopg2 connection management with proper resource cleanup.
Designed for Lambda execution context where connections should be
short-lived and properly closed.

Environment Variables:
    DATABASE_HOST: Aurora/PostgreSQL host
    DATABASE_PORT: Database port (defaults to 5432)
    DATABASE_NAME: Database name (defaults to axiepro)
    DATABASE_SECRET_NAME: Name of the credentials secret in Secrets Manager
"""

import os
from contextlib import contextmanager
from typing import Generator, Optional

import psycopg2
from psycopg2.extensions import connection as PgConnection

from src.lambdas.common.aws import get_db_credentials


# Database configuration from environment
DATABASE_HOST = os.environ.get("DATABASE_HOST")
DATABASE_PORT = os.environ.get("DATABASE_PORT", "5432")
DATABASE_NAME = os.environ.get("DATABASE_NAME", "axiepro")


def get_db_connection(
    host: Optional[str] = None,
    port: Optional[str] = None,
    dbname: Optional[str] = None,
    sslmode: str = "require",
) -> PgConnection:
    """
    Create a database connection using credentials from Secrets Manager.

    Args:
        host: Database host (defaults to DATABASE_HOST env var)
        port: Database port (defaults to DATABASE_PORT env var or 5432)
        dbname: Database name (defaults to DATABASE_NAME env var or axiepro)
        sslmode: SSL mode (defaults to require for RDS/Aurora)

    Returns:
        psycopg2 connection object.

    Raises:
        RuntimeError: If required environment variables are not set.
        psycopg2.Error: If connection fails.

    Example:
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        finally:
            conn.close()
    """
    credentials = get_db_credentials()

    conn_host = host or DATABASE_HOST
    conn_port = port or DATABASE_PORT
    conn_dbname = dbname or DATABASE_NAME

    if not conn_host:
        raise RuntimeError("DATABASE_HOST environment variable not set")

    return psycopg2.connect(
        host=conn_host,
        port=conn_port,
        dbname=conn_dbname,
        user=credentials.get("username"),
        password=credentials.get("password"),
        sslmode=sslmode,
    )


@contextmanager
def db_connection(
    host: Optional[str] = None,
    port: Optional[str] = None,
    dbname: Optional[str] = None,
    sslmode: str = "require",
    autocommit: bool = False,
) -> Generator[PgConnection, None, None]:
    """
    Context manager for database connections with automatic cleanup.

    Ensures connections are properly closed even if exceptions occur.
    Optionally commits on successful exit.

    Args:
        host: Database host (defaults to DATABASE_HOST env var)
        port: Database port (defaults to DATABASE_PORT env var)
        dbname: Database name (defaults to DATABASE_NAME env var)
        sslmode: SSL mode (defaults to require)
        autocommit: If True, commits on successful context exit

    Yields:
        psycopg2 connection object.

    Example:
        with db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO ...")
            conn.commit()

        # Connection is automatically closed
    """
    conn = get_db_connection(host, port, dbname, sslmode)
    try:
        yield conn
        if autocommit:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def execute_query(
    query: str,
    params: tuple = (),
    fetch: bool = True,
    fetchone: bool = False,
) -> Optional[list]:
    """
    Execute a query with automatic connection management.

    Convenience function for simple queries that don't need
    explicit connection handling.

    Args:
        query: SQL query string with %s placeholders
        params: Query parameters
        fetch: If True, fetch and return results
        fetchone: If True, fetch only one row

    Returns:
        Query results as list of tuples, single tuple, or None

    Example:
        rows = execute_query(
            "SELECT * FROM price_snapshots WHERE class = %s",
            ("beast",)
        )
    """
    with db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)

            if fetch:
                if fetchone:
                    return cur.fetchone()
                return cur.fetchall()

            conn.commit()
            return None
