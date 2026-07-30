import json
import logging
import urllib.request

from app.config import settings

logger = logging.getLogger(__name__)

_MARKETS = ["NYSE", "NASDAQ"]


class MarketdataClient:
    def fetch_symbols(self) -> dict[str, str]:
        """Devuelve {symbol: market}. Mismo patron directo-por-DNS con header
        X-Gateway-Passed que ya usa signal-processing-service, sin pasar por
        el gateway ni JWT (llamada interna entre contenedores)."""
        result: dict[str, str] = {}
        for market in _MARKETS:
            req = urllib.request.Request(
                f"{settings.marketdata_url}/marketdata/symbols?markets={market}",
                headers={"X-Gateway-Passed": "true"},
            )
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    symbols = json.loads(resp.read())
                for sym in symbols:
                    result[sym] = market
            except Exception as e:
                logger.error("Failed to fetch symbols for market %s: %s", market, e)
        return result
