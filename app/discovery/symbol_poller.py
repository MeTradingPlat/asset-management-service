import logging

from psycopg2.extras import execute_values

from app.db.engine import get_connection
from app.discovery.marketdata_client import MarketdataClient
from app.domain.timeframes import TIMEFRAME_MINUTES, is_derived

logger = logging.getLogger(__name__)

# D2/D3 no tienen watermark propio de Alpaca -- se derivan de D1 (ver
# domain/aggregation.py), asi que no se siembran aca.
_NATIVE_TIMEFRAMES = [tf for tf in TIMEFRAME_MINUTES if not is_derived(tf)]


class SymbolPoller:
    def __init__(self):
        self._marketdata = MarketdataClient()

    def poll(self) -> None:
        live_symbols = self._marketdata.fetch_symbols()
        if not live_symbols:
            logger.warning("SymbolPoller: no symbols returned by marketdata-service, skipping this poll")
            return

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT symbol, symbol_id, is_active FROM tracked_symbols")
                existing = {row[0]: (row[1], row[2]) for row in cur.fetchall()}

                new_rows = [(sym, mkt) for sym, mkt in live_symbols.items() if sym not in existing]
                new_ids = self._insert_symbols(cur, new_rows)
                self._seed_watermarks(cur, new_ids)

                delisted_ids = [sid for sym, (sid, active) in existing.items() if sym not in live_symbols and active]
                if delisted_ids:
                    cur.execute("UPDATE tracked_symbols SET is_active = FALSE WHERE symbol_id = ANY(%s)", (delisted_ids,))

        logger.info(
            "SymbolPoller: %d live symbols, %d newly tracked, %d marked inactive",
            len(live_symbols), len(new_ids), len(delisted_ids),
        )

    def _insert_symbols(self, cur, rows: list[tuple[str, str]]) -> list[int]:
        if not rows:
            return []
        inserted = execute_values(
            cur, "INSERT INTO tracked_symbols (symbol, market) VALUES %s RETURNING symbol_id",
            rows, fetch=True, page_size=1000,
        )
        return [row[0] for row in inserted]

    def _seed_watermarks(self, cur, symbol_ids: list[int]) -> None:
        if not symbol_ids:
            return
        rows = [(sid, tf) for sid in symbol_ids for tf in _NATIVE_TIMEFRAMES]
        execute_values(
            cur,
            "INSERT INTO watermarks (symbol_id, timeframe) VALUES %s ON CONFLICT (symbol_id, timeframe) DO NOTHING",
            rows, page_size=1000,
        )
