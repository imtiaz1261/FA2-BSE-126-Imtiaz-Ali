"""
Runs Alembic migrations programmatically so output isn't swallowed by PowerShell.
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from alembic.config import Config
from alembic import command

def run():
    alembic_cfg = Config("backend/alembic.ini")
    # Make sure alembic resolves script_location relative to the ini file
    alembic_cfg.set_main_option("script_location", "backend/migrations")

    print("Running: alembic upgrade head ...")
    try:
        command.upgrade(alembic_cfg, "head")
        print("SUCCESS: All migrations applied.")
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Verify tables
    import asyncio
    import asyncpg

    async def check():
        conn = await asyncpg.connect(
            host="localhost", port=5432,
            database="ai_research_workspace",
            user="aihub_user", password="imtiaz123", timeout=5
        )
        tables = await conn.fetch(
            "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
        )
        print("Tables created:")
        for t in tables:
            print(f"  ✓ {t['tablename']}")
        await conn.close()

    asyncio.run(check())

run()
