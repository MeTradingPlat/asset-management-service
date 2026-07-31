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
    """Backfill y refresco incremental corren en DOS HILOS INDEPENDIENTES,
    no uno detras del otro -- un backfill de velas de minuto (7 anios,
    muchisimas paginas de Alpaca) puede tardar mucho por tick, y si
    compartiera el mismo hilo secuencial con el refresco incremental, este
    ultimo se quedaria sin correr mientras tanto -- exactamente el hueco de
    datos que se queria evitar para timeframes de minutos. Ambos comparten
    el mismo rate limiter (thread-safe) para que el total combinado nunca
    pase las llamadas/min de Alpaca, sin importar cual de los dos este mas
    activo en un momento dado."""

    def __init__(self):
        self._rate_limiter = TokenBucket()
        self._alpaca = AlpacaClient(self._rate_limiter)
        self._stop = threading.Event()
        self._backfill_thread: threading.Thread | None = None
        self._steady_state_thread: threading.Thread | None = None

    def start(self) -> None:
        self._backfill_thread = threading.Thread(
            target=self._run_loop, args=("backfill",), name="hd-scheduler-backfill", daemon=True,
        )
        self._steady_state_thread = threading.Thread(
            target=self._run_loop, args=("steady_state",), name="hd-scheduler-steady-state", daemon=True,
        )
        self._backfill_thread.start()
        self._steady_state_thread.start()

    def stop(self) -> None:
        self._stop.set()
        for t in (self._backfill_thread, self._steady_state_thread):
            if t:
                t.join(timeout=5)

    def _run_loop(self, kind: str) -> None:
        while not self._stop.is_set():
            try:
                if kind == "backfill":
                    self._tick_backfill()
                else:
                    self._tick_steady_state()
            except Exception as e:
                logger.error("Scheduler (%s) tick failed: %s", kind, e)
            self._stop.wait(settings.scheduler_tick_seconds)

    def _tick_backfill(self) -> None:
        backfill, _ = fetch_due_rows()
        if not backfill:
            return
        processed = self._process_rows(backfill, is_backfill=True)
        logger.info("Scheduler backfill tick: due=%d processed=%d", len(backfill), processed)

    def _tick_steady_state(self) -> None:
        _, steady_state = fetch_due_rows()
        if not steady_state:
            return
        processed = self._process_rows(steady_state, is_backfill=False)
        logger.info("Scheduler steady-state tick: due=%d processed=%d", len(steady_state), processed)

    def _process_rows(self, rows: list[DueRow], is_backfill: bool) -> int:
        # Confirmado en vivo: Alpaca no limita simbolos/llamada, solo 10,000
        # filas/pagina. Backfill (7 anios de D1) agota esas filas con ~10-12
        # simbolos sin importar el tamano del lote pedido -- lote grande no
        # ayuda ahi. Refresco incremental (3 dias) cabe completo en una sola
        # pagina hasta con 1500 simbolos -- lote grande reduce las llamadas
        # necesarias en un orden de magnitud.
        batch_size = settings.alpaca_symbols_per_call_backfill if is_backfill \
            else settings.alpaca_symbols_per_call_steady_state
        kind = "backfill" if is_backfill else "steady-state"
        total_batches = sum(-(-len(list(g)) // batch_size) for _, g in groupby(sorted(rows, key=lambda r: r.timeframe), key=lambda r: r.timeframe))
        processed = 0
        batch_num = 0
        rows_sorted = sorted(rows, key=lambda r: r.timeframe)
        for timeframe, group in groupby(rows_sorted, key=lambda r: r.timeframe):
            group_rows = list(group)
            for i in range(0, len(group_rows), batch_size):
                if self._stop.is_set():
                    return processed
                batch = group_rows[i:i + batch_size]
                self._fetch_and_write_batch(batch, timeframe, is_backfill)
                processed += len(batch)
                batch_num += 1
                # Un solo tick puede tardar horas en workloads grandes (miles
                # de filas debidas, dominado por timeframes de minutos) --
                # sin esto, el log de resumen al final del tick no aparecia
                # en ese tiempo, dando la falsa impresion de que no estaba
                # pasando nada.
                if batch_num % 10 == 0 or batch_num == total_batches:
                    logger.info("Scheduler %s progress: batch %d/%d (%s, %d filas hasta ahora)",
                                kind, batch_num, total_batches, timeframe, processed)
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
