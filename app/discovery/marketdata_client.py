import json
import logging
import urllib.request

from app.config import settings

logger = logging.getLogger(__name__)

# marketdata-service espera codigos MIC, no el nombre de mercado tal cual
# (mismo mapeo que _MERCADO_TO_MIC en signal-processing-service).
_MARKETS = {"NYSE": "XNYS", "NASDAQ": "XNAS"}


class MarketdataClient:
    def fetch_symbols(self) -> dict[str, str]:
        """Devuelve {symbol: market}. Mismo patron directo-por-DNS con header
        X-Gateway-Passed que ya usa signal-processing-service, sin pasar por
        el gateway ni JWT (llamada interna entre contenedores). La respuesta
        es una lista de objetos {"symbol": ..., ...}, no de strings sueltos."""
        result: dict[str, str] = {}
        for market, mic in _MARKETS.items():
            req = urllib.request.Request(
                f"{settings.marketdata_url}/marketdata/symbols?markets={mic}",
                headers={"X-Gateway-Passed": "true"},
            )
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    entries = json.loads(resp.read())
                for entry in entries:
                    result[entry["symbol"]] = market
            except Exception as e:
                logger.error("Failed to fetch symbols for market %s: %s", market, e)
        return result
