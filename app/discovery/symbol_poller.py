import logging

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

                new_count = 0
                for symbol, market in live_symbols.items():
                    if symbol in existing:
                        continue
                    cur.execute(
                        "INSERT INTO tracked_symbols (symbol, market) VALUES (%s, %s) RETURNING symbol_id",
                        (symbol, market),
                    )
                    symbol_id = cur.fetchone()[0]
                    for tf in _NATIVE_TIMEFRAMES:
                        cur.execute(
                            "INSERT INTO watermarks (symbol_id, timeframe) VALUES (%s, %s) "
                            "ON CONFLICT (symbol_id, timeframe) DO NOTHING",
                            (symbol_id, tf),
                        )
                    new_count += 1

                delisted_count = 0
                for symbol, (symbol_id, is_active) in existing.items():
                    if symbol not in live_symbols and is_active:
                        cur.execute(
                            "UPDATE tracked_symbols SET is_active = FALSE WHERE symbol_id = %s",
                            (symbol_id,),
                        )
                        delisted_count += 1

        logger.info(
            "SymbolPoller: %d live symbols, %d newly tracked, %d marked inactive",
            len(live_symbols), new_count, delisted_count,
        )
