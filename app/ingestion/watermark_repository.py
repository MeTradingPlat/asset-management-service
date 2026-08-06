import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

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


# La ventana real que marketdata-service pide en vivo a DxLink por
# temporalidad esta en TastyTradeService.minLookbackFor() (3d para M1-M3,
# 7d para M5/M10, 10d para M15-M45, 14d para H1-H12, 1825d para D1+ -- cita
# la recomendacion oficial de TastyTrade en developer.tastytrade.com/
# streaming-market-data, seccion "Candle Events"). Ese es el verdadero techo
# de seguridad, no un numero generico de dxFeed -- pero con un piso de 10
# velas / techo de 1 dia (abajo), el umbral resultante nunca se acerca ni de
# lejos a esas ventanas (la mas angosta, M1-M3, es 3 dias -- 4x el techo de
# 1 dia), asi que no hace falta referenciarlas en el calculo mismo.
#
# Umbral = 10 barras de esa temporalidad, con piso de 15min (no perseguir
# M1 mas seguido que eso -- 13k+ simbolos de por medio) y techo de 1 dia
# (ni siquiera D1+ debe quedarse mas viejo que eso, aunque su ventana real
# sea de anios). Esto es lo que hace que M1 se revise cada 15min y D1 cada
# 1 dia en vez de tratarlos igual.
_REFRESH_BARS = 10
_MIN_REFRESH_INTERVAL = timedelta(minutes=15)
_MAX_REFRESH_INTERVAL = timedelta(days=1)


def _refresh_threshold(timeframe: str) -> timedelta:
    natural = timedelta(minutes=bar_duration_minutes(timeframe) * _REFRESH_BARS)
    return max(_MIN_REFRESH_INTERVAL, min(natural, _MAX_REFRESH_INTERVAL))


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
                threshold = _refresh_threshold(timeframe)
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
