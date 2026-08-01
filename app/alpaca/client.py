import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

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


class AlpacaClient:
    def __init__(self, rate_limiter: TokenBucket | None = None):
        self._base = settings.alpaca_base_url
        self._rate_limiter = rate_limiter or TokenBucket()

    def get_bars(
        self, symbols: list[str], timeframe: str, start: datetime, end: datetime,
    ) -> dict[str, list[Bar]]:
        """Trae barras nativas de Alpaca para varios simbolos en una sola
        llamada logica (mismo timeframe/rango), paginando via
        next_page_token. Cada pagina es una llamada HTTP real a Alpaca, asi
        que el rate limiter se consulta POR PAGINA (no una vez por lote) --
        una respuesta grande paginada igual respeta las 200 llamadas/min.
        Alpaca no soporta D2/D3 -- eso se deriva de D1 en otro lado
        (domain/aggregation.py), nunca se pide aca.

        Acciones de clase/warrants/units usan "/" en marketdata-service pero
        Alpaca solo los acepta con "." (confirmado en vivo: BRK/B falla,
        BRK.B funciona) -- se traduce aca en ambas direcciones para que el
        resto del sistema siga usando "/" de forma consistente."""
        alpaca_symbols = [sym.replace("/", ".") for sym in symbols]
        to_original = dict(zip(alpaca_symbols, symbols))
        result: dict[str, list[Bar]] = {sym: [] for sym in symbols}
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
            data = self._request_with_429_retry(req)

            for sym, bars in (data.get("bars") or {}).items():
                result.setdefault(sym, []).extend(
                    Bar(
                        ts=datetime.fromisoformat(b["t"].replace("Z", "+00:00")),
                        open=b["o"], high=b["h"], low=b["l"], close=b["c"],
                        volume=b.get("v", 0), trade_count=b.get("n"), vwap=b.get("vw"),
                    )
                    for b in bars
                )

            page_token = data.get("next_page_token")
            if not page_token:
                break

        return result

    def _request_with_429_retry(self, req: urllib.request.Request) -> dict:
        # Alpaca aplica algun tope de rafaga ademas del promedio/min (ver
        # penalize() en rate_limiter.py) -- un 429 aca frena a TODOS los
        # hilos que comparten el rate limiter via su propio Retry-After, no
        # solo reintenta esta llamada, para no seguir chocando con el mismo
        # tope desde otro hilo mientras este espera.
        for attempt in range(_MAX_429_RETRIES + 1):
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    return json.loads(resp.read())
            except urllib.error.HTTPError as e:
                if e.code != 429 or attempt == _MAX_429_RETRIES:
                    raise
                retry_after = _DEFAULT_RETRY_AFTER_SECONDS
                header = e.headers.get("Retry-After") if e.headers else None
                if header:
                    try:
                        retry_after = float(header)
                    except ValueError:
                        pass
                logger.warning("Alpaca 429, esperando %.1fs (intento %d/%d)", retry_after, attempt + 1, _MAX_429_RETRIES)
                self._rate_limiter.penalize(retry_after)
                time.sleep(retry_after)
