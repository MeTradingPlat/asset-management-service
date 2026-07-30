from app.domain.timeframes import (
    ALPACA_NATIVE_TIMEFRAME,
    DERIVED_TIMEFRAMES,
    TIMEFRAME_MINUTES,
    is_derived,
)

# Misma tabla que _TIMEFRAME_MINUTES en
# signal-processing-service/app/scanner/timeframe.py -- si alguna vez
# divergen en silencio, este test debe fallar.
_SIGNAL_PROCESSING_MINUTES = {
    "M1": 1, "M2": 2, "M3": 3, "M5": 5, "M10": 10,
    "M15": 15, "M30": 30, "M45": 45,
    "H1": 60, "H2": 120, "H3": 180, "H4": 240, "H12": 720,
    "D1": 1440, "D2": 2880, "D3": 4320, "W1": 10080,
    "MO1": 43200, "MO3": 129600, "MO6": 259200, "Y1": 525600,
}


def test_matches_signal_processing_service_minutes_table():
    assert TIMEFRAME_MINUTES == _SIGNAL_PROCESSING_MINUTES


def test_21_unified_codes_present():
    assert len(TIMEFRAME_MINUTES) == 21


def test_d2_d3_flagged_derived_not_native():
    assert DERIVED_TIMEFRAMES == {"D2", "D3"}
    assert is_derived("D2") and is_derived("D3")
    assert "D2" not in ALPACA_NATIVE_TIMEFRAME
    assert "D3" not in ALPACA_NATIVE_TIMEFRAME


def test_19_native_timeframes_map_to_alpaca():
    native = set(TIMEFRAME_MINUTES) - DERIVED_TIMEFRAMES
    assert native == set(ALPACA_NATIVE_TIMEFRAME)
    assert len(native) == 19
