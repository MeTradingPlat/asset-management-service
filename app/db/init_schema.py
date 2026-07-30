import logging
from pathlib import Path

from app.db.engine import get_connection

logger = logging.getLogger(__name__)

_SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def apply_schema() -> None:
    sql = _SCHEMA_PATH.read_text()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
    logger.info("Schema applied from %s", _SCHEMA_PATH)
