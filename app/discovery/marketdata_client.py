import json
import logging
import urllib.request

from app.config import settings

logger = logging.getLogger(__name__)

# marketdata-service espera codigos MIC, no el nombre de mercado tal cual
# (mismo mapeo _MERCADO_TO_MIC que signal-processing-service -- solo NYSE y
# NASDAQ dejaba fuera ~4400 simbolos de AMEX/ETF/OTC que si estan en DxLink).
_MARKETS = {
    "NYSE": "XNYS",
    "NASDAQ": "XNAS",
    "AMEX": "XASE",
    "ETF": "ARCX",
    "OTC": "OTC",
}


class MarketdataClient:
    def fetch_symbols(self) -> dict[str, str]:
        """Devuelve {symbol: market}. Mismo patron directo-por-DNS con header
        X-Gateway-Passed que ya usa signal-processing-service, sin pasar por
        el gateway ni JWT (llamada interna entre contenedores). La respuesta
        es una lista de objetos {"symbol": ..., ...}, no de strings sueltos.

        Simbolos con "/" (acciones de clase "BIO/B", warrants "/WS",
        unidades "/U", derechos "/R") se excluyen aca -- Alpaca los rechaza
        con 400 "invalid symbol", y confirmado en vivo que UN SOLO simbolo
        invalido en un lote de varios simbolos tumba la respuesta ENTERA
        (ni siquiera los simbolos validos del mismo lote se salvan). No
        vale la pena rastrearlos: no hay forma de traer su historial desde
        Alpaca. Al no aparecer aca, el mecanismo de "deslistado" ya
        existente en SymbolPoller los marca is_active=false solo si ya
        estaban rastreados de antes."""
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
                    symbol = entry["symbol"]
                    if "/" in symbol:
                        continue
                    result[symbol] = market
            except Exception as e:
                logger.error("Failed to fetch symbols for market %s: %s", market, e)
        return result
