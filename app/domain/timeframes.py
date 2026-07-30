# Los mismos 21 codigos unificados que ya usan marketdata-service,
# scanner-management-service y signal-processing-service. Duracion en
# minutos cruzada contra signal-processing-service's _TIMEFRAME_MINUTES via
# test (ver tests/test_domain/test_timeframes.py) para que las dos copias
# independientes no diverjan en silencio.
TIMEFRAME_MINUTES: dict[str, int] = {
    "M1": 1, "M2": 2, "M3": 3, "M5": 5, "M10": 10,
    "M15": 15, "M30": 30, "M45": 45,
    "H1": 60, "H2": 120, "H3": 180, "H4": 240, "H12": 720,
    "D1": 1440, "D2": 2880, "D3": 4320, "W1": 10080,
    "MO1": 43200, "MO3": 129600, "MO6": 259200, "Y1": 525600,
}

# D2/D3 nunca se piden a Alpaca directamente -- se derivan agrupando D1 ya
# guardado (ver domain/aggregation.py). Alpaca no soporta agregaciones de
# 2/3 dias como timeframe nativo.
DERIVED_TIMEFRAMES = {"D2", "D3"}

# Timeframes que Alpaca SI soporta nativamente, mapeados a su string de API
# (ver https://docs.alpaca.markets -- minutos 1-59, horas 1-23, dias/semanas
# solo *1*, meses solo {1,2,3,4,6,12}).
ALPACA_NATIVE_TIMEFRAME: dict[str, str] = {
    "M1": "1Min", "M2": "2Min", "M3": "3Min", "M5": "5Min", "M10": "10Min",
    "M15": "15Min", "M30": "30Min", "M45": "45Min",
    "H1": "1Hour", "H2": "2Hour", "H3": "3Hour", "H4": "4Hour", "H12": "12Hour",
    "D1": "1Day", "W1": "1Week",
    "MO1": "1Month", "MO3": "3Month", "MO6": "6Month", "Y1": "12Month",
}


def bar_duration_minutes(timeframe: str) -> int:
    return TIMEFRAME_MINUTES[timeframe]


def is_derived(timeframe: str) -> bool:
    return timeframe in DERIVED_TIMEFRAMES


def alpaca_native_string(timeframe: str) -> str:
    return ALPACA_NATIVE_TIMEFRAME[timeframe]
