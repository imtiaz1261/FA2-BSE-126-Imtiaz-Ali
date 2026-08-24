"""
One-shot DB setup script:
  1. Create role aihub_user with password imtiaz123
  2. Create database ai_research_workspace owned by aihub_user
  3. Grant all privileges
  4. Enable pgcrypto (for gen_random_uuid)
"""
import asyncio
import asyncpg

SUPERUSER = "postgres"
SUPERPASS = "imtiaz123"
DB_USER   = "aihub_user"
DB_PASS   = "imtiaz123"
DB_NAME   = "ai_research_workspace"

async def setup():
    # Connect as superuser to postgres DB
    conn = await asyncpg.connect(
        host="localhost", port=5432,
        database="postgres",
        user=SUPERUSER, password=SUPERPASS,
        timeout=10
    )
    print("Connected as postgres superuser.")

    # 1. Create role if not exists
    exists = await conn.fetchval(
        "SELECT 1 FROM pg_roles WHERE rolname = $1", DB_USER
    )
    if not exists:
        await conn.execute(
            f"CREATE ROLE {DB_USER} WITH LOGIN PASSWORD '{DB_PASS}'"
        )
        print(f"Role '{DB_USER}' created.")
    else:
        # Update password in case it changed
        await conn.execute(
            f"ALTER ROLE {DB_USER} WITH PASSWORD '{DB_PASS}'"
        )
        print(f"Role '{DB_USER}' already exists — password updated.")

    # 2. Create database if not exists
    db_exists = await conn.fetchval(
        "SELECT 1 FROM pg_database WHERE datname = $1", DB_NAME
    )
    if not db_exists:
        # Can't run CREATE DATABASE inside a transaction, use autocommit
        await conn.execute(f"CREATE DATABASE {DB_NAME} OWNER {DB_USER}")
        print(f"Database '{DB_NAME}' created.")
    else:
        print(f"Database '{DB_NAME}' already exists.")

    await conn.close()

    # 3. Connect to the new DB and enable extensions
    conn2 = await asyncpg.connect(
        host="localhost", port=5432,
        database=DB_NAME,
        user=SUPERUSER, password=SUPERPASS,
        timeout=10
    )
    await conn2.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    await conn2.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    print("Extensions: pgcrypto, pg_trgm enabled.")

    # 4. Grant privileges
    await conn2.execute(f"GRANT ALL PRIVILEGES ON DATABASE {DB_NAME} TO {DB_USER}")
    await conn2.execute(f"GRANT ALL ON SCHEMA public TO {DB_USER}")
    await conn2.execute(f"ALTER SCHEMA public OWNER TO {DB_USER}")
    print(f"Granted all privileges to '{DB_USER}'.")

    await conn2.close()
    print("\nDatabase setup complete!")
    print(f"  Host:     localhost:5432")
    print(f"  Database: {DB_NAME}")
    print(f"  User:     {DB_USER}")
    print(f"  Password: {DB_PASS}")

asyncio.run(setup())
