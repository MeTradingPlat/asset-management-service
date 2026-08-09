import concurrent.futures
import logging
import threading
from datetime import datetime, timedelta, timezone
from itertools import groupby

from app.alpaca.client import AlpacaClient
from app.alpaca.rate_limiter import TokenBucket
from app.config import settings
from app.domain.retention import retention_start
from app.domain.timeframes import bar_duration_minutes, is_minute_timeframe
from app.ingestion.candle_writer import derive_daily_aggregates, write_bars
from app.ingestion.watermark_repository import DueRow, fetch_due_rows, update_watermark

logger = logging.getLogger(__name__)


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
        def batch_size_for(timeframe: str) -> int:
            if not is_backfill:
                return settings.alpaca_symbols_per_call_steady_state
            if is_minute_timeframe(timeframe):
                return settings.alpaca_symbols_per_call_backfill_minute
            return settings.alpaca_symbols_per_call_backfill

        kind = "backfill" if is_backfill else "steady-state"
        # steady-state: mas fino primero. Con scheduler_fetch_workers=1 los
        # lotes corren de a uno -- si todas las temporalidades quedan debidas
        # al mismo tiempo (ej. arranque en frio) y se procesaran en orden
        # alfabetico, M1 (umbral de 15min) caeria detras de D1/H1/H12/H2/H3/H4
        # y, si esa vuelta tarda mas de 15min con miles de simbolos de por
        # medio, nunca alcanzaria a refrescarse a tiempo -- el umbral
        # diferenciado por temporalidad (ver watermark_repository) quedaria
        # anulado por el orden de ejecucion. El backfill no tiene ese
        # problema (no hay "deadline" de frescura), asi que se deja como
        # estaba.
        sort_key = (lambda r: r.timeframe) if is_backfill else (lambda r: bar_duration_minutes(r.timeframe))
        rows_sorted = sorted(rows, key=sort_key)
        batches = [
            (timeframe, group_rows[i:i + batch_size_for(timeframe)])
            for timeframe, group in groupby(rows_sorted, key=lambda r: r.timeframe)
            for group_rows in (list(group),)
            for i in range(0, len(group_rows), batch_size_for(timeframe))
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
        now = datetime.now(timezone.utc)

        if not is_backfill:
            self._fetch_and_write_range(batch, timeframe, now - timedelta(days=3), now,
                                         is_backfill=False, allow_complete=True)
            return

        oldest_known = min((r.oldest_ingested_at for r in batch if r.oldest_ingested_at), default=now)
        window_start = retention_start(timeframe, now)

        if oldest_known <= window_start:
            # Ya se tiene todo lo que la ventana de retencion de esta
            # temporalidad pide (ej. quedo backfilleado con una ventana mas
            # larga antes de acortarla) -- no hay nada nuevo que pedirle a
            # Alpaca, solo falta que quede marcado.
            for row in batch:
                update_watermark(row.symbol_id, timeframe, newest_ts=None, oldest_ts=None, backfill_complete=True)
            return

        # Exclusivo de la barra mas vieja que ya tenemos -- pedir con
        # end=oldest_known (inclusive) hace que Alpaca vuelva a incluirla en
        # la respuesta para siempre cuando la historia real del simbolo
        # termina justo ahi (ej. IPO reciente, cambio de ticker) en vez de
        # extenderse mas alla de toda la ventana: nunca llega un "vacio"
        # genuino, asi que nunca se marca completo (confirmado en vivo:
        # 5,284/13,132 simbolos de D1 atascados horas re-pidiendo la misma
        # barra sin avanzar).
        fetch_end = oldest_known - timedelta(microseconds=1)

        if not is_minute_timeframe(timeframe):
            self._fetch_and_write_range(batch, timeframe, window_start, fetch_end,
                                         is_backfill=True, allow_complete=True)
            return

        # Alpaca no reparte paginas por turnos entre simbolos de una llamada
        # multi-simbolo -- agota TODAS las paginas del primero con datos
        # pendientes antes de pasar al siguiente (docs.alpaca.markets/us/
        # reference/stockbars). Con ventanas de retencion cortas esto ya
        # colapsa a una sola llamada en la mayoria de los casos (ver
        # RETENTION_DAYS), pero se deja el fraccionamiento por si alguna
        # ventana crece mas alla de lo que cabe en una pagina -- cada trozo
        # es una llamada corta, asi que el worker se libera seguido en vez
        # de quedar atado a una cadena de paginacion larga.
        chunk = timedelta(days=settings.backfill_minute_chunk_days)
        chunk_end = fetch_end
        while chunk_end > window_start:
            if self._stop.is_set():
                return
            chunk_start = max(window_start, chunk_end - chunk)
            # "Completo" solo se marca en el trozo que de verdad llega hasta
            # el inicio de la ventana -- un trozo intermedio vacio (ej. el
            # simbolo tuvo una suspension de cotizacion) no significa que no
            # haya historia mas atras dentro de la ventana.
            is_final_chunk = chunk_start <= window_start
            self._fetch_and_write_range(batch, timeframe, chunk_start, chunk_end,
                                         is_backfill=True, allow_complete=is_final_chunk)
            chunk_end = chunk_start

    def _fetch_and_write_range(
        self, batch: list[DueRow], timeframe: str, start: datetime, end: datetime,
        is_backfill: bool, allow_complete: bool,
    ) -> None:
        symbols = [r.symbol for r in batch]
        by_symbol = {r.symbol: r for r in batch}

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
            self._write_page(relevant, by_symbol, timeframe, is_backfill, allow_complete, start)

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
            self._write_page(leftovers, by_symbol, timeframe, is_backfill, allow_complete, start)

    def _write_page(
        self, page_bars: dict[str, list], by_symbol: dict[str, DueRow], timeframe: str,
        is_backfill: bool, allow_complete: bool, range_start: datetime,
    ) -> None:
        # Escribir cada simbolo es espera de I/O (conexion + upsert + a
        # veces re-lectura para derivar D2/D3), no trabajo de CPU -- hacerlo
        # secuencial uno por uno desperdicia el tiempo muerto de cada espera.
        # El pool de conexiones (db_pool_max_connections) esta dimensionado
        # para cubrir scheduler_write_workers en los DOS hilos del scheduler
        # (backfill + steady-state) a la vez, mas margen para la API HTTP.
        with concurrent.futures.ThreadPoolExecutor(max_workers=settings.scheduler_write_workers) as executor:
            futures = {
                executor.submit(self._write_symbol_result, symbol, bars, by_symbol.get(symbol), timeframe,
                                 is_backfill, allow_complete, range_start): symbol
                for symbol, bars in page_bars.items()
            }
            for future in concurrent.futures.as_completed(futures):
                symbol = futures[future]
                try:
                    future.result()
                except Exception as e:
                    logger.error("Failed to write %s bars for %s: %s", timeframe, symbol, e)

    def _write_symbol_result(
        self, symbol: str, bars: list, row: DueRow | None, timeframe: str,
        is_backfill: bool, allow_complete: bool, range_start: datetime,
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
        written = write_bars(row.symbol_id, timeframe, bars, derive=not is_backfill)
        if written:
            newest = max(b.ts for b in written)
            oldest = min(b.ts for b in written)
            update_watermark(row.symbol_id, timeframe, newest_ts=newest, oldest_ts=oldest,
                              backfill_complete=(False if is_backfill else None))
        elif is_backfill and allow_complete:
            # Pagina vacia en la ventana que llega hasta _BACKFILL_START =
            # ya no hay mas historia disponible en Alpaca para este simbolo.
            update_watermark(row.symbol_id, timeframe, newest_ts=None, oldest_ts=None, backfill_complete=True)
            if timeframe == "D1":
                derive_daily_aggregates(row.symbol_id)
        elif is_backfill:
            # Ventana intermedia vacia (fraccionamiento por anio) -- avanza
            # el watermark hasta el inicio de esta ventana para que la
            # siguiente iteracion siga mas atras en el tiempo, SIN marcar
            # completo (ver comentario en el llamador sobre por que).
            update_watermark(row.symbol_id, timeframe, newest_ts=None, oldest_ts=range_start)
