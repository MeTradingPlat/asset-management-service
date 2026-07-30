import logging
from contextlib import contextmanager

import psycopg2
from psycopg2 import pool as pg_pool

from app.config import settings

logger = logging.getLogger(__name__)

_pool: pg_pool.ThreadedConnectionPool | None = None


def init_pool(minconn: int = 1, maxconn: int = 10) -> None:
    global _pool
    if _pool is not None:
        return
    _pool = pg_pool.ThreadedConnectionPool(
        minconn,
        maxconn,
        host=settings.db_host,
        port=settings.db_port,
        dbname=settings.db_name,
        user=settings.db_user,
        password=settings.db_password,
    )
    logger.info("DB pool connected to %s:%s/%s", settings.db_host, settings.db_port, settings.db_name)


@contextmanager
def get_connection():
    if _pool is None:
        init_pool()
    assert _pool is not None
    conn = _pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _pool.putconn(conn)
