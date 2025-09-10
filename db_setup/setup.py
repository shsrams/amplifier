#!/usr/bin/env python3
"""
Database setup orchestrator - runs bricks in sequence
Following the modular design philosophy, this orchestrator
simply connects the bricks together in the right order.
"""

import argparse
import sys

# Load environment variables from .env file
from dotenv import load_dotenv

from db_setup import connection
from db_setup import schema

load_dotenv()


def main(reset: bool = False, validate_only: bool = False, status_only: bool = False) -> int:
    """Simple orchestrator that runs setup bricks in sequence."""
    conn = None
    try:
        # Step 1: Connect
        print("📡 Connecting to database...")
        conn = connection.connect()

        if status_only:
            # Just show connection status
            info = connection.get_database_info(conn)
            print(f"✅ Connected to: {info['database']}")
            print(f"   User: {info['user']}")
            print(f"   Version: {info['version']}")
            return 0

        if validate_only:
            # Validate current schema
            print("🔍 Validating schema...")
            state = schema.verify_schema(conn)
            if state["valid"]:
                print("✅ Schema is valid")
                print(f"   Tables: {', '.join(state['tables'])}")
                print(f"   Functions: {', '.join(state['functions'])}")
                print(f"   Indexes: {len(state['indexes'])} indexes")
            else:
                print("❌ Schema validation failed")
                if "error" in state:
                    print(f"   Error: {state['error']}")
            return 0 if state["valid"] else 1

        if reset:
            # Reset database (with confirmation)
            print("⚠️  WARNING: This will DELETE all data!")
            response = input("Type 'yes' to continue: ")
            if response.lower() != "yes":
                print("❌ Reset cancelled")
                return 1
            print("🗑️  Resetting database...")
            schema.drop_all(conn)

        # Step 2: Create schema
        print("📝 Creating tables...")
        schema.create_tables(conn)

        # Step 3: Create utility functions
        print("🔧 Creating utility functions...")
        schema.create_utility_functions(conn)

        # Step 4: Validate
        print("✅ Validating setup...")
        state = schema.verify_schema(conn)
        if not state["valid"]:
            print("❌ Validation failed: Schema is incomplete")
            return 1

        print("🎉 Database setup complete!")
        print(f"   Tables created: {', '.join(state['tables'])}")
        print(f"   Functions created: {', '.join(state['functions'])}")
        print(f"   Indexes created: {len(state['indexes'])}")

        return 0

    except ConnectionError as e:
        print(f"❌ Connection failed: {e}")
        print("\nTroubleshooting:")
        print("  1. Check your DATABASE_URL in .env file")
        print("  2. Verify your Azure PostgreSQL server is running")
        print("  3. Check firewall rules in Azure Portal")
        return 1

    except Exception as e:
        print(f"❌ Setup failed: {e}")
        return 1

    finally:
        if conn is not None:
            conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Setup Azure PostgreSQL database")
    parser.add_argument("--reset", action="store_true", help="Reset database (deletes all data!)")
    parser.add_argument("--validate", action="store_true", help="Validate current schema")
    parser.add_argument("--status", action="store_true", help="Show connection status")

    args = parser.parse_args()

    exit_code = main(reset=args.reset, validate_only=args.validate, status_only=args.status)

    sys.exit(exit_code)
