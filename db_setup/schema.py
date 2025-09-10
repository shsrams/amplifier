"""
Brick: Schema Creation
Purpose: Create database tables and structures
Input: Database connection
Output: Success/failure status
Side-effects: Creates database objects
Dependencies: connection brick
"""

import psycopg2.extensions


def create_tables(conn: psycopg2.extensions.connection) -> bool:
    """Create the core knowledge_items table and related structures."""
    try:
        with conn.cursor() as cur:
            # Main knowledge storage table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_items (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    machine_id TEXT NOT NULL DEFAULT 'default'::text,
                    category TEXT NOT NULL,
                    key TEXT NOT NULL,
                    data JSONB NOT NULL,
                    metadata JSONB DEFAULT '{}'::jsonb,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW(),
                    CONSTRAINT unique_item UNIQUE (machine_id, category, key)
                )
            """)

            # Create indexes for performance
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_knowledge_category
                ON knowledge_items(machine_id, category)
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_knowledge_timestamps
                ON knowledge_items(created_at DESC, updated_at DESC)
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_knowledge_data
                ON knowledge_items USING GIN(data)
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_knowledge_metadata
                ON knowledge_items USING GIN(metadata)
            """)

            conn.commit()
            return True

    except Exception as e:
        conn.rollback()
        raise RuntimeError(f"Failed to create tables: {e}") from e


def create_utility_functions(conn: psycopg2.extensions.connection) -> bool:
    """Create helper functions for data management."""
    try:
        with conn.cursor() as cur:
            # Upsert function for easy data management
            cur.execute("""
                CREATE OR REPLACE FUNCTION upsert_knowledge_item(
                    p_machine_id TEXT,
                    p_category TEXT,
                    p_key TEXT,
                    p_data JSONB,
                    p_metadata JSONB DEFAULT '{}'
                ) RETURNS UUID AS $$
                DECLARE
                    v_id UUID;
                BEGIN
                    INSERT INTO knowledge_items (machine_id, category, key, data, metadata)
                    VALUES (p_machine_id, p_category, p_key, p_data, p_metadata)
                    ON CONFLICT (machine_id, category, key)
                    DO UPDATE SET
                        data = EXCLUDED.data,
                        metadata = EXCLUDED.metadata,
                        updated_at = NOW()
                    RETURNING id INTO v_id;
                    RETURN v_id;
                END;
                $$ LANGUAGE plpgsql;
            """)

            conn.commit()
            return True

    except Exception as e:
        conn.rollback()
        raise RuntimeError(f"Failed to create functions: {e}") from e


def verify_schema(conn: psycopg2.extensions.connection) -> dict:
    """Returns current schema state."""
    try:
        with conn.cursor() as cur:
            # Check tables
            cur.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)
            tables = [row[0] for row in cur.fetchall()]

            # Check functions
            cur.execute("""
                SELECT routine_name
                FROM information_schema.routines
                WHERE routine_schema = 'public'
                AND routine_type = 'FUNCTION'
                ORDER BY routine_name
            """)
            functions = [row[0] for row in cur.fetchall()]

            # Check indexes
            cur.execute("""
                SELECT indexname
                FROM pg_indexes
                WHERE schemaname = 'public'
                AND tablename = 'knowledge_items'
                ORDER BY indexname
            """)
            indexes = [row[0] for row in cur.fetchall()]

            return {"tables": tables, "functions": functions, "indexes": indexes, "valid": "knowledge_items" in tables}

    except Exception as e:
        return {"tables": [], "functions": [], "indexes": [], "valid": False, "error": str(e)}


def drop_all(conn: psycopg2.extensions.connection) -> bool:
    """Drop all database objects (USE WITH CAUTION)."""
    try:
        with conn.cursor() as cur:
            # Drop tables (CASCADE will drop dependent objects)
            cur.execute("DROP TABLE IF EXISTS knowledge_items CASCADE")

            # Drop functions
            cur.execute("DROP FUNCTION IF EXISTS upsert_knowledge_item")

            conn.commit()
            return True

    except Exception as e:
        conn.rollback()
        raise RuntimeError(f"Failed to drop schema: {e}") from e
