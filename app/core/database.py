from dotenv import load_dotenv
load_dotenv()

import os
from psycopg.rows import dict_row
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool

def get_database_url() -> str:

    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise ValueError(
            "DATABASE_URL is missing. "
            "Please add your PostgreSQL database URL to .env"
        )

    if "sslmode=" not in database_url:
        separator = "&" if "?" in database_url else "?"
        database_url = (
            f"{database_url}"
            f"{separator}"
            f"sslmode=require"
        )

    return database_url


DATABASE_URL = get_database_url()


pool = AsyncConnectionPool(
    conninfo=DATABASE_URL,
    kwargs={
        "autocommit": True,
        "row_factory": dict_row,
    },
    open=False,
)


async def get_checkpointer():

    await pool.open()

    checkpointer = AsyncPostgresSaver(pool)

    return checkpointer


async def setup_database():

    await pool.open()

    async with pool.connection() as conn:

        checkpointer = AsyncPostgresSaver(conn)

        await checkpointer.setup()

    print("✅ PostgreSQL checkpointer initialized")