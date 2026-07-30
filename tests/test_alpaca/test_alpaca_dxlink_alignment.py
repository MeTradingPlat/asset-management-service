"""Version permanente y re-corrible del script de verificacion inicial --
guardia de regresion: si Alpaca o DxLink cambian de convencion de timestamp
en silencio, este test debe fallar en vez de dejar que los datos se
corrompan calladamente. Requiere Alpaca real + marketdata-service real."""
import pytest

from app.alpaca.client import AlpacaClient
from app.discovery.marketdata_client import MarketdataClient
from app.domain.timestamp_normalization import normalize_daily_timestamp

pytestmark = pytest.mark.integration


@pytest.mark.integration
def test_alpaca_d1_normalizes_to_dxlink_convention():
    import json
    import urllib.request

    from app.config import settings

    req = urllib.request.Request(
        f"{settings.marketdata_url}/marketdata/historical/batch",
        data=json.dumps({"symbols": ["AAPL"], "timeframe": "D1", "bars": 10}).encode(),
        headers={"Content-Type": "application/json", "X-Gateway-Passed": "true"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        dxlink_candles = json.loads(resp.read()).get("candlesPorSimbolo", {}).get("AAPL", [])
    assert dxlink_candles, "marketdata-service returned no D1 candles for AAPL"

    from datetime import datetime, timedelta, timezone
    latest_dxlink_ts = max(
        datetime.fromisoformat(c["timestamp"].replace("Z", "+00:00")) for c in dxlink_candles
    )

    client = AlpacaClient()
    bars = client.get_bars(
        ["AAPL"], "D1", latest_dxlink_ts - timedelta(days=1), latest_dxlink_ts + timedelta(days=1),
    )["AAPL"]
    assert bars, "Alpaca returned no D1 bars for AAPL in the matching window"

    normalized = {normalize_daily_timestamp(b.ts) for b in bars}
    assert latest_dxlink_ts in normalized, (
        f"Alpaca D1 timestamps normalized to {normalized} do not include "
        f"DxLink's {latest_dxlink_ts} -- timestamp convention may have changed"
    )
