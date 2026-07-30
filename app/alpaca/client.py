import json
import logging
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from app.alpaca.rate_limiter import TokenBucket
from app.config import settings
from app.domain.aggregation import Bar
from app.domain.timeframes import alpaca_native_string

logger = logging.getLogger(__name__)


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
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())

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
