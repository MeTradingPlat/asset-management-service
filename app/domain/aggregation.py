from dataclasses import dataclass
from datetime import date, datetime


@dataclass
class Bar:
    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    trade_count: int | None = None
    vwap: float | None = None


# Confirmado en vivo contra AAPL (ver scripts/verify_alpaca_dxlink_timestamps.py):
# DxLink arranca un grupo D2 nuevo en 2026-06-18 y un grupo D3 nuevo en
# 2026-06-15, saltandose correctamente el feriado de Juneteenth
# (2026-06-19) al emparejar. La paridad (que dia exacto arranca un grupo,
# no solo "cada 2/3 dias habiles") es arbitraria salvo que se ancle a un
# punto real observado -- por eso no se adivina desde el inicio del
# historial de Alpaca, se ancla a estas fechas confirmadas y se extiende
# hacia atras/adelante desde ahi.
D2_ANCHOR = date(2026, 6, 18)
D3_ANCHOR = date(2026, 6, 15)

_ANCHOR_BY_GROUP_SIZE = {2: D2_ANCHOR, 3: D3_ANCHOR}


def group_consecutive_trading_days(bars: list[Bar], group_size: int) -> list[Bar]:
    """Agrupa barras D1 ya ordenadas (sin huecos -- Alpaca solo devuelve dias
    de trading reales, asi que la adyacencia en el arreglo ya salta fines de
    semana y feriados correctamente) en grupos de group_size, anclados a la
    paridad real observada en DxLink. Un grupo incompleto al final (todavia
    no llegan suficientes dias) nunca se devuelve -- su watermark se
    actualiza cuando el siguiente D1 lo completa."""
    if not bars or group_size not in _ANCHOR_BY_GROUP_SIZE:
        return []

    anchor = _ANCHOR_BY_GROUP_SIZE[group_size]
    anchor_idx = next((i for i, b in enumerate(bars) if b.ts.date() == anchor), None)
    start_idx = anchor_idx % group_size if anchor_idx is not None else 0

    grouped: list[Bar] = []
    for i in range(start_idx, len(bars) - group_size + 1, group_size):
        chunk = bars[i:i + group_size]
        grouped.append(Bar(
            ts=chunk[0].ts,
            open=chunk[0].open,
            high=max(c.high for c in chunk),
            low=min(c.low for c in chunk),
            close=chunk[-1].close,
            volume=sum(c.volume for c in chunk),
        ))
    return grouped
