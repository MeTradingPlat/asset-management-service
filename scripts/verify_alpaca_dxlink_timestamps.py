"""Script de verificacion manual (no parte de la suite de tests): compara
D1/D2/D3 de DxLink (via marketdata-service, ya en produccion) contra D1
nativo de Alpaca para el mismo simbolo y ventana, para detectar si alguno
de los dos cambio de convencion de timestamp/feed en silencio.

Requiere HD_ALPACA_API_KEY / HD_ALPACA_API_SECRET en el entorno, y correr
donde marketdata-service sea alcanzable por DNS interno (dentro de la red
de contenedores).

Uso: python scripts/verify_alpaca_dxlink_timestamps.py [SYMBOL] [START] [END]
"""
import json
import sys
import urllib.request

sys.path.insert(0, ".")

from app.config import settings  # noqa: E402


def get_dxlink_candles(symbol: str, timeframe: str) -> list[dict]:
    req = urllib.request.Request(
        f"{settings.marketdata_url}/marketdata/historical/batch",
        data=json.dumps({"symbols": [symbol], "timeframe": timeframe, "bars": 30}).encode(),
        headers={"Content-Type": "application/json", "X-Gateway-Passed": "true"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    return data.get("candlesPorSimbolo", {}).get(symbol, [])


def get_alpaca_bars(symbol: str, start: str, end: str) -> list[dict]:
    url = (
        f"{settings.alpaca_base_url}/v2/stocks/bars"
        f"?symbols={symbol}&timeframe=1Day&start={start}&end={end}&limit=10000&adjustment=raw&feed=iex"
    )
    req = urllib.request.Request(
        url,
        headers={"APCA-API-KEY-ID": settings.alpaca_api_key, "APCA-API-SECRET-KEY": settings.alpaca_api_secret},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    return data.get("bars", {}).get(symbol, [])


def _print_dxlink(label: str, rows: list[dict]) -> None:
    print(f"\n=== DxLink {label} ===")
    for c in rows:
        print(c.get("timestamp"), "O", c.get("open"), "H", c.get("high"), "L", c.get("low"),
              "C", c.get("close"), "V", c.get("volume"))


def main() -> None:
    symbol = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    start = sys.argv[2] if len(sys.argv) > 2 else "2026-06-01T00:00:00Z"
    end = sys.argv[3] if len(sys.argv) > 3 else "2026-06-30T00:00:00Z"

    _print_dxlink("D1", get_dxlink_candles(symbol, "D1"))
    _print_dxlink("D2", get_dxlink_candles(symbol, "D2"))
    _print_dxlink("D3", get_dxlink_candles(symbol, "D3"))

    print("\n=== Alpaca native 1Day ===")
    for b in get_alpaca_bars(symbol, start, end):
        print(b.get("t"), "O", b.get("o"), "H", b.get("h"), "L", b.get("l"), "C", b.get("c"), "V", b.get("v"))


if __name__ == "__main__":
    main()
