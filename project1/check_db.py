import asyncio
import asyncpg

async def test():
    # Test with .env values
    try:
        conn = await asyncpg.connect(
            host='localhost', port=5432,
            database='ai_research_workspace',
            user='aihub_user', password='imtiaz123',
            timeout=5
        )
        print('Connected to ai_research_workspace as aihub_user: OK')
        tables = await conn.fetch(
            "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
        )
        print('Tables:', [r['tablename'] for r in tables])
        await conn.close()
        return
    except Exception as e:
        print('ai_research_workspace/aihub_user error:', e)

    # Test with config.py defaults
    try:
        conn = await asyncpg.connect(
            host='localhost', port=5432,
            database='aihub',
            user='aihub_user', password='aihub_password',
            timeout=5
        )
        print('Connected to aihub/aihub_user: OK')
        await conn.close()
        return
    except Exception as e:
        print('aihub/aihub_user error:', e)

    # Test as postgres superuser (no password on local Windows)
    try:
        conn = await asyncpg.connect(
            host='localhost', port=5432,
            database='postgres',
            user='postgres',
            timeout=5
        )
        print('Connected as postgres superuser: OK')
        rows = await conn.fetch(
            "SELECT datname FROM pg_database WHERE datname NOT LIKE 'template%'"
        )
        print('Existing databases:', [r['datname'] for r in rows])
        users = await conn.fetch("SELECT usename FROM pg_user")
        print('Existing users:', [r['usename'] for r in users])
        await conn.close()
    except Exception as e:
        print('postgres superuser error:', e)

asyncio.run(test())
