import logging

from psycopg2.extras import execute_values

from app.db.engine import get_connection
from app.domain.aggregation import Bar, group_consecutive_trading_days
from app.domain.timestamp_normalization import normalize_daily_timestamp

logger = logging.getLogger(__name__)

_UPSERT_SQL = """
    INSERT INTO candles (symbol_id, timeframe, ts, open, high, low, close, volume, trade_count, vwap, source)
    VALUES %s
    ON CONFLICT (symbol_id, timeframe, ts) DO UPDATE SET
        open = EXCLUDED.open, high = EXCLUDED.high, low = EXCLUDED.low, close = EXCLUDED.close,
        volume = EXCLUDED.volume, trade_count = EXCLUDED.trade_count, vwap = EXCLUDED.vwap
"""


def write_bars(
    symbol_id: int, timeframe: str, bars: list[Bar], source: str = "alpaca_native", derive: bool = True,
) -> None:
    """derive=False salta el recalculo de D2/D3 tras escribir D1 -- usado
    durante el backfill, donde cada batch escribe solo una porcion parcial
    del historial de un simbolo (releer y regrupar TODO el D1 acumulado en
    cada una de esas escrituras parciales es trabajo repetido que crece con
    cada tick, ver Scheduler._fetch_and_write_batch, que llama a
    derive_daily_aggregates() una sola vez cuando el backfill de ese simbolo
    de verdad termina)."""
    if not bars:
        return
    if timeframe == "D1":
        bars = [
            Bar(ts=normalize_daily_timestamp(b.ts), open=b.open, high=b.high, low=b.low, close=b.close,
                volume=b.volume, trade_count=b.trade_count, vwap=b.vwap)
            for b in bars
        ]

    rows = [
        (symbol_id, timeframe, b.ts, b.open, b.high, b.low, b.close, int(b.volume), b.trade_count, b.vwap, source)
        for b in bars
    ]
    with get_connection() as conn:
        with conn.cursor() as cur:
            execute_values(cur, _UPSERT_SQL, rows)

    if timeframe == "D1" and derive:
        derive_daily_aggregates(symbol_id)


def derive_daily_aggregates(symbol_id: int) -> None:
    """D2/D3 se calculan al escribir D1, no al leer -- una foto intermedia
    de un grupo incompleto nunca queda persistida (ver aggregation.py). Se
    relee TODO el historial D1 guardado (no solo el lote recien escrito),
    porque un grupo puede completarse a caballo entre un lote viejo y uno
    nuevo -- agrupar solo el lote actual perderia esos casos en el borde."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT ts, open, high, low, close, volume FROM candles "
                "WHERE symbol_id = %s AND timeframe = 'D1' ORDER BY ts",
                (symbol_id,),
            )
            all_d1 = [Bar(ts=row[0], open=row[1], high=row[2], low=row[3], close=row[4], volume=row[5])
                      for row in cur.fetchall()]

    for group_size, timeframe, source in ((2, "D2", "derived_d2"), (3, "D3", "derived_d3")):
        grouped = group_consecutive_trading_days(all_d1, group_size)
        if grouped:
            write_bars(symbol_id, timeframe, grouped, source=source)
