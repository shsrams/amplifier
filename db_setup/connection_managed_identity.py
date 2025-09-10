"""
Enhanced Database Connection with Managed Identity Support
Purpose: Establish PostgreSQL connection using password or managed identity
Input: DATABASE_URL or individual connection parameters from environment
Output: Active database connection
Side-effects: None
Dependencies: psycopg2, azure-identity (optional)
"""

import os

import psycopg2


def get_access_token() -> str | None:
    """
    Get Azure AD access token for PostgreSQL authentication.
    Returns None if azure-identity is not available or not in Azure environment.
    """
    try:
        from azure.identity import DefaultAzureCredential
        from azure.identity import ManagedIdentityCredential

        # Check if we're using a specific managed identity client ID
        client_id = os.environ.get("AZURE_POSTGRESQL_CLIENTID")

        if client_id:
            # Use user-assigned managed identity
            credential = ManagedIdentityCredential(client_id=client_id)
        else:
            # Use system-assigned managed identity or local dev credentials
            credential = DefaultAzureCredential()

        # Get token for Azure Database for PostgreSQL
        token = credential.get_token("https://ossrdbms-aad.database.windows.net/.default")
        return token.token

    except ImportError:
        # azure-identity not installed, fall back to password auth
        return None
    except Exception as e:
        # Not in Azure environment or managed identity not configured
        print(f"Managed identity not available: {e}")
        return None


def get_connection_params() -> dict:
    """
    Get database connection parameters from environment.
    Supports both connection string and individual parameters.
    """
    # First, try to get a complete connection string
    conn_str = (
        os.environ.get("DATABASE_URL")
        or os.environ.get("AZURE_POSTGRESQL_CONNECTIONSTRING")
        or os.environ.get("POSTGRES_CONNECTION_STRING")
    )

    if conn_str:
        # Parse connection string if we have one
        # psycopg2 will handle the parsing
        return {"dsn": conn_str}

    # Otherwise, build from individual parameters
    params = {}

    # Required parameters
    host = os.environ.get("AZURE_POSTGRESQL_HOST") or os.environ.get("PGHOST")
    database = os.environ.get("AZURE_POSTGRESQL_NAME") or os.environ.get("PGDATABASE")
    user = os.environ.get("AZURE_POSTGRESQL_USER") or os.environ.get("PGUSER")

    if not all([host, database, user]):
        raise ValueError(
            "Database connection parameters not found. "
            "Set DATABASE_URL or AZURE_POSTGRESQL_HOST/USER/NAME environment variables."
        )

    params["host"] = host
    params["database"] = database
    params["user"] = user
    params["port"] = os.environ.get("AZURE_POSTGRESQL_PORT", "5432")
    params["sslmode"] = os.environ.get("AZURE_POSTGRESQL_SSLMODE", "require")

    # Authentication: Try managed identity first, then password
    auth_method = os.environ.get("AZURE_AUTH_METHOD", "auto")

    if auth_method in ["managed_identity", "auto"]:
        token = get_access_token()
        if token:
            params["password"] = token
            print("Using managed identity authentication")
            return params
        if auth_method == "managed_identity":
            raise ValueError(
                "Managed identity authentication requested but not available. "
                "Ensure azure-identity is installed and you're running in Azure."
            )

    # Fall back to password authentication
    password = (
        os.environ.get("AZURE_POSTGRESQL_PASSWORD")
        or os.environ.get("PGPASSWORD")
        or os.environ.get("DATABASE_PASSWORD")
    )

    if not password and auth_method != "managed_identity":
        raise ValueError(
            "No authentication method available. Set AZURE_POSTGRESQL_PASSWORD or configure managed identity."
        )

    params["password"] = password
    print("Using password authentication")
    return params


def connect() -> psycopg2.extensions.connection:
    """
    Returns verified database connection.
    Automatically selects between managed identity and password authentication.
    """
    try:
        params = get_connection_params()

        if "dsn" in params:
            # Use connection string directly
            conn = psycopg2.connect(params["dsn"])
        else:
            # Use individual parameters
            conn = psycopg2.connect(**params)

        return conn

    except psycopg2.OperationalError as e:
        error_msg = str(e)

        if "could not translate host name" in error_msg:
            raise ConnectionError("Cannot connect to database server. Check your server name.") from e

        if "password authentication failed" in error_msg:
            # Check if this might be a managed identity issue
            if os.environ.get("AZURE_AUTH_METHOD") == "managed_identity":
                raise ConnectionError(
                    "Managed identity authentication failed. "
                    "Ensure the identity has been granted access to the database."
                ) from e
            raise ConnectionError("Authentication failed. Check your username and password.") from e

        if "SSL" in error_msg:
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
    """Get basic database information including authentication method."""
    with conn.cursor() as cur:
        # Get basic info
        cur.execute("""
            SELECT
                current_database() as database,
                current_user as user,
                version() as version
        """)
        result = cur.fetchone()

        if result is None:
            return {"database": "unknown", "user": "unknown", "version": "unknown"}

        info = {
            "database": result[0],
            "user": result[1],
            "version": result[2][:50] + "..." if len(result[2]) > 50 else result[2],
        }

        # Try to detect if using Microsoft Entra authentication
        try:
            cur.execute("""
                SELECT auth_method
                FROM pg_stat_activity
                WHERE pid = pg_backend_pid()
            """)
            auth_result = cur.fetchone()
            if auth_result:
                info["auth_method"] = auth_result[0]
        except Exception:
            # Column might not exist in all PostgreSQL versions
            pass

        return info


# Maintain backward compatibility
get_connection_string = get_connection_params
