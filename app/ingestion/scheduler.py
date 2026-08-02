import concurrent.futures
import logging
import threading
from datetime import datetime, timedelta, timezone
from itertools import groupby

from app.alpaca.client import AlpacaClient
from app.alpaca.rate_limiter import TokenBucket
from app.config import settings
from app.ingestion.candle_writer import derive_daily_aggregates, write_bars
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
        rows_sorted = sorted(rows, key=lambda r: r.timeframe)
        batches = [
            (timeframe, group_rows[i:i + batch_size])
            for timeframe, group in groupby(rows_sorted, key=lambda r: r.timeframe)
            for group_rows in (list(group),)
            for i in range(0, len(group_rows), batch_size)
        ]
        total_batches = len(batches)
        processed = 0
        completed = 0
        progress_lock = threading.Lock()

        # Cada lote espera su propio turno en el TokenBucket compartido
        # (thread-safe, ver rate_limiter.py) antes de llamar a Alpaca, asi
        # que lanzar varios en paralelo aca no rompe el limite real de
        # 200 llamadas/min -- solo aprovecha que antes habia como maximo
        # UNA llamada en vuelo por hilo del scheduler (backfill o
        # steady-state) mientras cada una tarda ~10s, dejando el
        # presupuesto real muy por debajo del tope (una cada 0.3s
        # posibles) sin nada que lo usara.
        with concurrent.futures.ThreadPoolExecutor(max_workers=settings.scheduler_fetch_workers) as executor:
            futures: dict[concurrent.futures.Future, int] = {}
            for timeframe, batch in batches:
                if self._stop.is_set():
                    break
                futures[executor.submit(self._fetch_and_write_batch, batch, timeframe, is_backfill)] = len(batch)
            # Un solo tick puede tardar horas en workloads grandes (miles de
            # filas debidas, dominado por timeframes de minutos) -- sin
            # esto, el log de resumen al final del tick no aparecia en ese
            # tiempo, dando la falsa impresion de que no estaba pasando nada.
            for future in concurrent.futures.as_completed(futures):
                future.result()
                with progress_lock:
                    completed += 1
                    processed += futures[future]
                    if completed % 10 == 0 or completed == total_batches:
                        logger.info("Scheduler %s progress: batch %d/%d (%d filas hasta ahora)",
                                    kind, completed, total_batches, processed)
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

        # Confirmado en produccion: acumular TODAS las paginas de un backfill
        # de minutos (7 anios, cientos de paginas) en memoria antes de
        # escribir una sola fila generaba picos de RAM sin control -- con
        # varios workers cayendo en lotes grandes a la vez, tumbaba el
        # contenedor por OOM cada 10-20min pese a subir el limite de
        # memoria (el limite solo retrasaba lo inevitable, no arreglaba la
        # causa). get_bars_streaming entrega cada pagina apenas llega y
        # esta se escribe/descarta de inmediato via touched_page, sin
        # acumular nada entre paginas -- el pico de memoria pasa de "todo
        # el backfill del simbolo" a "una pagina".
        touched: set[str] = set()

        def touched_page(page_bars: dict[str, list]) -> None:
            relevant = {sym: bars for sym, bars in page_bars.items() if sym in by_symbol}
            touched.update(relevant)
            self._write_page(relevant, by_symbol, timeframe, is_backfill)

        try:
            self._alpaca.get_bars_streaming(symbols, timeframe, start, end, touched_page)
        except Exception as e:
            logger.error("Alpaca fetch failed for %s batch (%s): %s", timeframe, symbols, e)
            for row in batch:
                update_watermark(row.symbol_id, timeframe, newest_ts=None, oldest_ts=None, error=str(e))
            return

        # Simbolos que no aparecieron en NINGUNA pagina equivalen al "bars
        # vacio" del diseno anterior (ver _write_symbol_result) -- Alpaca no
        # tiene mas historia para ellos en este rango.
        leftovers = {sym: [] for sym in by_symbol if sym not in touched}
        if leftovers:
            self._write_page(leftovers, by_symbol, timeframe, is_backfill)

    def _write_page(
        self, page_bars: dict[str, list], by_symbol: dict[str, DueRow], timeframe: str, is_backfill: bool,
    ) -> None:
        # Escribir cada simbolo es espera de I/O (conexion + upsert + a
        # veces re-lectura para derivar D2/D3), no trabajo de CPU -- hacerlo
        # secuencial uno por uno desperdicia el tiempo muerto de cada espera.
        # El pool de conexiones (db_pool_max_connections) esta dimensionado
        # para cubrir scheduler_write_workers en los DOS hilos del scheduler
        # (backfill + steady-state) a la vez, mas margen para la API HTTP.
        with concurrent.futures.ThreadPoolExecutor(max_workers=settings.scheduler_write_workers) as executor:
            futures = {
                executor.submit(self._write_symbol_result, symbol, bars, by_symbol.get(symbol), timeframe, is_backfill): symbol
                for symbol, bars in page_bars.items()
            }
            for future in concurrent.futures.as_completed(futures):
                symbol = futures[future]
                try:
                    future.result()
                except Exception as e:
                    logger.error("Failed to write %s bars for %s: %s", timeframe, symbol, e)

    def _write_symbol_result(
        self, symbol: str, bars: list, row: DueRow | None, timeframe: str, is_backfill: bool,
    ) -> None:
        if row is None:
            return
        # Durante backfill cada batch trae solo una porcion parcial del
        # historial -- derivar D2/D3 aca releeria y regruparia TODO el D1
        # acumulado en cada tick, un costo que crece sin parar a medida
        # que avanza el backfill (confirmado como el cuello de botella
        # real: una llamada a Alpaca de 100 simbolos tarda ~10s, pero el
        # batch completo tardaba minutos). Se difiere a una sola vez, mas
        # abajo, cuando el backfill de ESE simbolo de verdad termina.
        write_bars(row.symbol_id, timeframe, bars, derive=not is_backfill)
        if bars:
            newest = max(b.ts for b in bars)
            oldest = min(b.ts for b in bars)
            update_watermark(row.symbol_id, timeframe, newest_ts=newest, oldest_ts=oldest,
                              backfill_complete=(False if is_backfill else None))
        elif is_backfill:
            # Pagina vacia = ya no hay mas historia disponible en Alpaca para este simbolo.
            update_watermark(row.symbol_id, timeframe, newest_ts=None, oldest_ts=None, backfill_complete=True)
            if timeframe == "D1":
                derive_daily_aggregates(row.symbol_id)
