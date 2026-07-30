import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.config import settings
from app.db.engine import get_connection
from app.domain.timeframes import bar_duration_minutes, is_derived

logger = logging.getLogger(__name__)


@dataclass
class DueRow:
    symbol_id: int
    symbol: str
    timeframe: str
    backfill_complete: bool
    oldest_ingested_at: datetime | None


def _dxlink_live_window(timeframe: str) -> timedelta:
    return timedelta(minutes=settings.dxlink_live_bar_count * bar_duration_minutes(timeframe))


def fetch_due_rows() -> tuple[list[DueRow], list[DueRow]]:
    """Devuelve (backfill_pendiente, refresco_incremental_pendiente). D2/D3
    quedan fuera -- nunca se piden a Alpaca directamente."""
    now = datetime.now(timezone.utc)
    backfill: list[DueRow] = []
    steady_state: list[DueRow] = []

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT ts.symbol_id, ts.symbol, w.timeframe, w.backfill_complete,
                       w.oldest_ingested_at, w.last_ingested_at
                FROM watermarks w
                JOIN tracked_symbols ts ON ts.symbol_id = w.symbol_id
                WHERE ts.is_active = TRUE
                """
            )
            for symbol_id, symbol, timeframe, backfill_complete, oldest_ingested_at, last_ingested_at in cur.fetchall():
                if is_derived(timeframe):
                    continue
                row = DueRow(symbol_id, symbol, timeframe, backfill_complete, oldest_ingested_at)
                if not backfill_complete:
                    backfill.append(row)
                    continue
                threshold = _dxlink_live_window(timeframe) * 2 / 3
                if last_ingested_at is None or now - last_ingested_at >= threshold:
                    steady_state.append(row)

    return backfill, steady_state


def update_watermark(
    symbol_id: int, timeframe: str, *, newest_ts: datetime | None, oldest_ts: datetime | None,
    backfill_complete: bool | None = None, error: str | None = None,
) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            if error:
                cur.execute(
                    """
                    UPDATE watermarks
                    SET last_checked_at = now(), last_error = %s, consecutive_errors = consecutive_errors + 1
                    WHERE symbol_id = %s AND timeframe = %s
                    """,
                    (error, symbol_id, timeframe),
                )
                return

            cur.execute(
                """
                UPDATE watermarks
                SET last_checked_at = now(),
                    last_error = NULL,
                    consecutive_errors = 0,
                    last_ingested_at = COALESCE(GREATEST(last_ingested_at, %(newest)s), %(newest)s),
                    oldest_ingested_at = COALESCE(LEAST(oldest_ingested_at, %(oldest)s), %(oldest)s),
                    backfill_complete = COALESCE(%(backfill_complete)s, backfill_complete)
                WHERE symbol_id = %(symbol_id)s AND timeframe = %(timeframe)s
                """,
                {
                    "newest": newest_ts, "oldest": oldest_ts, "backfill_complete": backfill_complete,
                    "symbol_id": symbol_id, "timeframe": timeframe,
                },
            )
