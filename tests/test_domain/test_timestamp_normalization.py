from datetime import datetime, timezone

from app.domain.timestamp_normalization import normalize_daily_timestamp

# Valores reales capturados contra AAPL (ver
# scripts/verify_alpaca_dxlink_timestamps.py) el 2026-07-30: DxLink marca la
# barra diaria a medianoche UTC exacta; Alpaca la marca a medianoche hora de
# Nueva York expresada en UTC. Si esto alguna vez cambia silenciosamente de
# cualquiera de los dos lados, este test debe fallar en vez de corromper
# datos calladamente.
_REAL_SAMPLES = [
    # (alpaca_timestamp_iso, expected_normalized_iso)
    ("2026-06-17T04:00:00+00:00", "2026-06-17T00:00:00+00:00"),  # EDT (verano)
    ("2026-06-18T04:00:00+00:00", "2026-06-18T00:00:00+00:00"),
    ("2026-06-22T04:00:00+00:00", "2026-06-22T00:00:00+00:00"),
]


def test_normalize_matches_dxlink_convention_edt():
    for alpaca_iso, expected_iso in _REAL_SAMPLES:
        alpaca_ts = datetime.fromisoformat(alpaca_iso)
        expected = datetime.fromisoformat(expected_iso)
        assert normalize_daily_timestamp(alpaca_ts) == expected


def test_normalize_handles_est_winter_offset():
    # En invierno (EST, UTC-5) medianoche NY es 05:00 UTC, no 04:00 -- el
    # offset se resuelve via zoneinfo (no un timedelta fijo), asi que debe
    # seguir devolviendo la fecha correcta.
    winter_ts = datetime(2026, 1, 15, 5, 0, 0, tzinfo=timezone.utc)
    assert normalize_daily_timestamp(winter_ts) == datetime(2026, 1, 15, 0, 0, 0, tzinfo=timezone.utc)
