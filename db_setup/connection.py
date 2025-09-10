"""
Brick: Database Connection
Purpose: Establish and test PostgreSQL connection
Input: DATABASE_URL from environment
Output: Active database connection
Side-effects: None
Dependencies: psycopg2
"""

import os

import psycopg2


def get_connection_string() -> str:
    """Get database connection string from environment."""
    # Try multiple possible environment variable names
    conn_str = (
        os.environ.get("DATABASE_URL")
        or os.environ.get("PERSONAL_POSTGRESQL_CONNECTION_STRING")
        or os.environ.get("POSTGRES_CONNECTION_STRING")
    )

    if not conn_str:
        raise ValueError("No database connection string found. Please set DATABASE_URL in your .env file")

    return conn_str


def connect() -> psycopg2.extensions.connection:
    """Returns verified database connection or raises clear error."""
    try:
        conn_str = get_connection_string()
        conn = psycopg2.connect(conn_str)
        return conn
    except psycopg2.OperationalError as e:
        if "could not translate host name" in str(e):
            raise ConnectionError(
                "Cannot connect to database server. Check your server name in the connection string."
            ) from e
        if "password authentication failed" in str(e):
            raise ConnectionError("Authentication failed. Check your username and password.") from e
        if "SSL" in str(e):
            raise ConnectionError("SSL connection required. Add '?sslmode=require' to your connection string.") from e
        raise ConnectionError(f"Database connection failed: {e}") from e


def test_connection(conn: psycopg2.extensions.connection) -> bool:
    """Validates connection is working."""
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            result = cur.fetchone()
            return result is not None and result[0] == 1
    except Exception:
        return False


def get_database_info(conn: psycopg2.extensions.connection) -> dict:
    """Get basic database information."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT
                current_database() as database,
                current_user as user,
                version() as version
        """)
        result = cur.fetchone()
        if result is None:
            return {"database": "unknown", "user": "unknown", "version": "unknown"}
        return {
            "database": result[0],
            "user": result[1],
            "version": result[2][:50] + "..." if len(result[2]) > 50 else result[2],
        }
