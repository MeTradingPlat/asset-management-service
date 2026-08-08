import json
import logging
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Callable

from app.alpaca.rate_limiter import TokenBucket
from app.config import settings
from app.domain.aggregation import Bar
from app.domain.timeframes import alpaca_native_string

logger = logging.getLogger(__name__)

# Alpaca no siempre manda "Retry-After" en el 429 (confirmado en vivo: a
# veces si, a veces no) -- este es el piso a usar cuando falta, tomado de su
# propia recomendacion de backoff (docs.alpaca.markets, seccion rate limits).
_DEFAULT_RETRY_AFTER_SECONDS = 3.0
_MAX_429_RETRIES = 5

# Los 401 esporadicos en data.alpaca.markets son un problema reconocido del
# lado de Alpaca, no de credenciales invalidas -- confirmado en su propio
# foro (forum.alpaca.markets/t/persistent-401-unauthorized-on-data-alpaca-
# markets-trading-api-works-fine), donde recomiendan reintentar. Antes de
# esto, un 401 tumbaba TODO el lote (hasta 100 simbolos) de una y quedaba
# marcado con error hasta el siguiente tick de backfill -- que puede tardar
# dias en volver a esa temporalidad. 5xx y errores de red/timeout entran en
# el mismo balde por la misma razon: transitorios, no un fallo real del lote.
_MAX_TRANSIENT_RETRIES = 3
_TRANSIENT_RETRY_BACKOFF_SECONDS = 2.0
_TRANSIENT_STATUS_CODES = {401, 500, 502, 503, 504}

# marketdata-service (DxLink/TastyTrade convention) marks preferred shares as
# "TICKERp" (single series) or "TICKERpX" (series X) -- confirmed live
# against Alpaca that this was silently returning zero bars for every one of
# these (384 symbols), each wrongly marked backfill_complete instead of
# erroring, because Alpaca expects "TICKER.PR"/"TICKER.PRX" instead (e.g.
# BACpE -> BAC.PRE, ETIp -> ETI.PR -- both verified live to return real
# data). The "/" -> "." rule below only covers class shares (BRK/B ->
# BRK.B), not this.
_PREFERRED_RE = re.compile(r"^([A-Z]+)p([A-Z]?)$")


def _to_alpaca_symbol(symbol: str) -> str:
    m = _PREFERRED_RE.match(symbol)
    if m:
        ticker, series = m.groups()
        return f"{ticker}.PR{series}"
    return symbol.replace("/", ".")


class AlpacaClient:
    def __init__(self, rate_limiter: TokenBucket | None = None):
        self._base = settings.alpaca_base_url
        self._rate_limiter = rate_limiter or TokenBucket()

    def get_bars(
        self, symbols: list[str], timeframe: str, start: datetime, end: datetime,
    ) -> dict[str, list[Bar]]:
        """Conveniencia sobre get_bars_streaming() para llamadores que
        quieren el resultado completo de una sola vez -- solo apta para
        pedidos chicos/acotados (ej. pruebas). El scheduler de backfill NO
        usa esto: un backfill de minutos con 7 anios de historia son
        cientos de paginas, y acumular todo eso en un dict antes de
        devolver nada es exactamente el pico de memoria sin control que
        get_bars_streaming evita (ver su docstring)."""
        result: dict[str, list[Bar]] = {sym: [] for sym in symbols}

        def collect(page_bars: dict[str, list[Bar]]) -> None:
            for sym, bars in page_bars.items():
                result.setdefault(sym, []).extend(bars)

        self.get_bars_streaming(symbols, timeframe, start, end, collect)
        return result

    def get_bars_streaming(
        self, symbols: list[str], timeframe: str, start: datetime, end: datetime,
        on_page: Callable[[dict[str, list[Bar]]], None],
    ) -> None:
        """Trae barras nativas de Alpaca para varios simbolos en una sola
        peticion logica (mismo timeframe/rango), paginando via
        next_page_token. Cada pagina es una llamada HTTP real a Alpaca, asi
        que el rate limiter se consulta POR PAGINA (no una vez por lote) --
        una respuesta grande paginada igual respeta las 200 llamadas/min.
        Alpaca no soporta D2/D3 -- eso se deriva de D1 en otro lado
        (domain/aggregation.py), nunca se pide aca.

        A diferencia de una version que acumule todas las paginas y
        devuelva el resultado al final, esta invoca on_page() con cada
        pagina apenas llega y la descarta -- confirmado en produccion que
        un backfill de minutos (7 anios, cientos de paginas por lote) con
        varios workers en paralelo cayendo en lotes grandes a la vez
        generaba picos de memoria sin control, tumbando el contenedor por
        OOM cada 10-20min pese a subir el limite de memoria del
        contenedor (el limite solo retrasaba el choque, no arreglaba la
        causa).

        Acciones de clase/warrants/units usan "/" en marketdata-service pero
        Alpaca solo los acepta con "." (confirmado en vivo: BRK/B falla,
        BRK.B funciona), y preferentes usan "TICKERp"/"TICKERpX" en vez del
        "TICKER.PR"/"TICKER.PRX" de Alpaca (ver _to_alpaca_symbol) -- ambos
        se traducen aca en ambas direcciones para que el resto del sistema
        siga usando la convencion de marketdata-service de forma
        consistente."""
        alpaca_symbols = [_to_alpaca_symbol(sym) for sym in symbols]
        to_original = dict(zip(alpaca_symbols, symbols))
        page_token = None
        tf = alpaca_native_string(timeframe)

        while True:
            while not self._rate_limiter.try_acquire():
                time.sleep(0.5)
            params = {
                "symbols": ",".join(alpaca_symbols),
                "timeframe": tf,
                "start": start.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
                "end": end.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
                "limit": "10000",
                "adjustment": "raw",
                "feed": "iex",
            }
            if page_token:
                params["page_token"] = page_token

            url = f"{self._base}/v2/stocks/bars?{urllib.parse.urlencode(params)}"
            req = urllib.request.Request(
                url,
                headers={
                    "APCA-API-KEY-ID": settings.alpaca_api_key,
                    "APCA-API-SECRET-KEY": settings.alpaca_api_secret,
                },
            )
            data = self._request_with_retry(req)

            page_bars: dict[str, list[Bar]] = {}
            for sym, bars in (data.get("bars") or {}).items():
                page_bars.setdefault(to_original.get(sym, sym), []).extend(
                    Bar(
                        ts=datetime.fromisoformat(b["t"].replace("Z", "+00:00")),
                        open=b["o"], high=b["h"], low=b["l"], close=b["c"],
                        volume=b.get("v", 0), trade_count=b.get("n"), vwap=b.get("vw"),
                    )
                    for b in bars
                )
            if page_bars:
                on_page(page_bars)

            page_token = data.get("next_page_token")
            if not page_token:
                break

    def _request_with_retry(self, req: urllib.request.Request) -> dict:
        # Alpaca aplica algun tope de rafaga ademas del promedio/min (ver
        # penalize() en rate_limiter.py) -- un 429 aca frena a TODOS los
        # hilos que comparten el rate limiter via su propio Retry-After, no
        # solo reintenta esta llamada, para no seguir chocando con el mismo
        # tope desde otro hilo mientras este espera. Los 401/5xx/red usan un
        # balde de reintentos aparte (ver _MAX_TRANSIENT_RETRIES arriba).
        burst_attempt = 0
        transient_attempt = 0
        while True:
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    return json.loads(resp.read())
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    if burst_attempt == _MAX_429_RETRIES:
                        raise
                    burst_attempt += 1
                    retry_after = _DEFAULT_RETRY_AFTER_SECONDS
                    header = e.headers.get("Retry-After") if e.headers else None
                    if header:
                        try:
                            retry_after = float(header)
                        except ValueError:
                            pass
                    logger.warning("Alpaca 429, esperando %.1fs (intento %d/%d)", retry_after, burst_attempt, _MAX_429_RETRIES)
                    self._rate_limiter.penalize(retry_after)
                    time.sleep(retry_after)
                    continue
                if e.code in _TRANSIENT_STATUS_CODES and transient_attempt < _MAX_TRANSIENT_RETRIES:
                    transient_attempt += 1
                    logger.warning("Alpaca %d, reintentando en %.1fs (intento %d/%d)",
                                    e.code, _TRANSIENT_RETRY_BACKOFF_SECONDS, transient_attempt, _MAX_TRANSIENT_RETRIES)
                    time.sleep(_TRANSIENT_RETRY_BACKOFF_SECONDS)
                    continue
                raise
            except (urllib.error.URLError, TimeoutError) as e:
                if transient_attempt == _MAX_TRANSIENT_RETRIES:
                    raise
                transient_attempt += 1
                logger.warning("Alpaca request fallo (%s), reintentando en %.1fs (intento %d/%d)",
                                e, _TRANSIENT_RETRY_BACKOFF_SECONDS, transient_attempt, _MAX_TRANSIENT_RETRIES)
                time.sleep(_TRANSIENT_RETRY_BACKOFF_SECONDS)
