from datetime import datetime, timedelta

# Cuanto tiempo hacia atras se mantiene cada temporalidad en `candles`. Las
# finas pesan ordenes de magnitud mas por vela (390 velas/dia de sesion para
# M1 vs ~1 para D1) -- ventanas cortas ahi, largas donde es barato. Si en
# algun momento se necesita mas profundidad para un simbolo puntual, se
# puede pedir bajo demanda a Alpaca -- este servicio no tiene por que
# mantener cargados los 13k simbolos a full profundidad de minuto de forma
# proactiva (confirmado con el usuario: 7.5 anios de minuto para todo el
# universo de simbolos no cabe en ningun disco razonable).
RETENTION_DAYS: dict[str, int] = {
    "M1": 60, "M2": 60, "M3": 60, "M5": 60,
    "M10": 180, "M15": 180, "M30": 180, "M45": 180,
    "H1": 730, "H2": 730, "H3": 730, "H4": 730, "H12": 730,
    "D1": 1825, "D2": 1825, "D3": 1825,
    "W1": 1825, "MO1": 1825, "MO3": 1825, "MO6": 1825, "Y1": 1825,
}


def retention_start(timeframe: str, now: datetime) -> datetime:
    return now - timedelta(days=RETENTION_DAYS[timeframe])
