import json
import logging
import re
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

# Simbolos de prueba emitidos por las bolsas para verificar feeds de datos
# (ATEST/CTEST/NTEST/PTEST y sus sufijos /A, /B...) -- no son instrumentos
# reales, Alpaca no tiene datos para ellos ni con notacion de punto
# (confirmado en vivo). Se excluyen aca para no gastar llamadas rastreandolos.
_TEST_SYMBOL_RE = re.compile(r"^[A-Z]TEST(/|$)")


class MarketdataClient:
    def fetch_symbols(self) -> dict[str, str]:
        """Devuelve {symbol: market}. Mismo patron directo-por-DNS con header
        X-Gateway-Passed que ya usa signal-processing-service, sin pasar por
        el gateway ni JWT (llamada interna entre contenedores). La respuesta
        es una lista de objetos {"symbol": ..., ...}, no de strings sueltos.

        Los simbolos con "/" (acciones de clase "BRK/B", warrants "/WS",
        unidades "/U") SI se rastrean -- Alpaca los sirve bien, solo hay que
        pedirlos con "." en vez de "/" (confirmado en vivo: BRK.B, GME.WS,
        RAC.U devuelven datos; la traduccion pasa a AlpacaClient, aca se
        guarda el simbolo tal cual lo entrega marketdata-service)."""
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
                    if _TEST_SYMBOL_RE.match(symbol):
                        continue
                    result[symbol] = market
            except Exception as e:
                logger.error("Failed to fetch symbols for market %s: %s", market, e)
        return result
