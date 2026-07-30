import logging
import threading
from datetime import datetime, timedelta, timezone
from itertools import groupby

from app.alpaca.client import AlpacaClient
from app.alpaca.rate_limiter import TokenBucket
from app.config import settings
from app.ingestion.candle_writer import write_bars
from app.ingestion.watermark_repository import DueRow, fetch_due_rows, update_watermark

logger = logging.getLogger(__name__)

_BACKFILL_START = datetime(2018, 1, 1, tzinfo=timezone.utc)  # ~7+ anios atras, Alpaca recorta solo si no tiene mas


class Scheduler:
    def __init__(self):
        # Un solo rate limiter compartido entre backfill y refresco
        # incremental -- el reparto de presupuesto entre los dos es solo
        # cuantos SIMBOLOS se procesan por tick de cada lado, la cuenta real
        # de llamadas/min vive en un solo lugar (AlpacaClient).
        self._rate_limiter = TokenBucket()
        self._alpaca = AlpacaClient(self._rate_limiter)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, name="hd-scheduler", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self.tick()
            except Exception as e:
                logger.error("Scheduler tick failed: %s", e)
            self._stop.wait(settings.scheduler_tick_seconds)

    def tick(self) -> None:
        backfill, steady_state = fetch_due_rows()
        if not backfill and not steady_state:
            return

        backfill_slots = int(settings.alpaca_symbols_per_call * 4 * settings.backfill_call_budget_fraction)
        steady_slots = int(settings.alpaca_symbols_per_call * 4 * (1 - settings.backfill_call_budget_fraction))

        processed_backfill = self._process_rows(backfill[:backfill_slots], is_backfill=True)
        processed_steady = self._process_rows(steady_state[:steady_slots], is_backfill=False)

        logger.info(
            "Scheduler tick: backfill due=%d processed=%d, steady-state due=%d processed=%d",
            len(backfill), processed_backfill, len(steady_state), processed_steady,
        )

    def _process_rows(self, rows: list[DueRow], is_backfill: bool) -> int:
        if not rows:
            return 0
        processed = 0
        rows_sorted = sorted(rows, key=lambda r: r.timeframe)
        for timeframe, group in groupby(rows_sorted, key=lambda r: r.timeframe):
            group_rows = list(group)
            for i in range(0, len(group_rows), settings.alpaca_symbols_per_call):
                batch = group_rows[i:i + settings.alpaca_symbols_per_call]
                self._fetch_and_write_batch(batch, timeframe, is_backfill)
                processed += len(batch)
        return processed

    def _fetch_and_write_batch(self, batch: list[DueRow], timeframe: str, is_backfill: bool) -> None:
        symbols = [r.symbol for r in batch]
        by_symbol = {r.symbol: r for r in batch}
        now = datetime.now(timezone.utc)

        if is_backfill:
            oldest_known = min((r.oldest_ingested_at for r in batch if r.oldest_ingested_at), default=now)
            start, end = _BACKFILL_START, oldest_known
        else:
            start, end = now - timedelta(days=3), now

        try:
            bars_by_symbol = self._alpaca.get_bars(symbols, timeframe, start, end)
        except Exception as e:
            logger.error("Alpaca fetch failed for %s batch (%s): %s", timeframe, symbols, e)
            for row in batch:
                update_watermark(row.symbol_id, timeframe, newest_ts=None, oldest_ts=None, error=str(e))
            return

        for symbol, bars in bars_by_symbol.items():
            row = by_symbol.get(symbol)
            if row is None:
                continue
            write_bars(row.symbol_id, timeframe, bars)
            if bars:
                newest = max(b.ts for b in bars)
                oldest = min(b.ts for b in bars)
                update_watermark(row.symbol_id, timeframe, newest_ts=newest, oldest_ts=oldest,
                                  backfill_complete=(False if is_backfill else None))
            elif is_backfill:
                # Pagina vacia = ya no hay mas historia disponible en Alpaca para este simbolo.
                update_watermark(row.symbol_id, timeframe, newest_ts=None, oldest_ts=None, backfill_complete=True)
