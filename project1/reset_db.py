"""
Reset database schema by dropping and recreating all tables.
"""
import asyncio
from sqlalchemy import text
from backend.db.session import engine
from backend.db._base import Base


async def reset_database():
    """Drop all tables and recreate from models."""
    print("[*] Resetting database schema...")
    
    try:
        # Drop all tables
        async with engine.begin() as conn:
            # Drop existing schema
            await conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
            await conn.execute(text("CREATE SCHEMA public"))
            print("[+] Dropped existing schema")
        
        # Recreate tables from models
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            print("[+] Created all tables from models")
            
        print("[OK] Database reset complete")
        
    except Exception as e:
        print(f"[ERROR] {e}")
        raise


if __name__ == "__main__":
    asyncio.run(reset_database())
