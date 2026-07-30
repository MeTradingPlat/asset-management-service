from datetime import datetime, timezone
from zoneinfo import ZoneInfo

_NY = ZoneInfo("America/New_York")

# Verificado en vivo (AAPL, 2026-06-17): DxLink marca la barra diaria a
# medianoche UTC exacta ("2026-06-17T00:00:00Z"); Alpaca marca la misma
# barra a medianoche hora de Nueva York expresada en UTC
# ("2026-06-17T04:00:00Z" en horario de verano). El offset varia con
# EST/EDT, por eso se resuelve via zoneinfo (no un timedelta fijo) --
# convertir a la fecha de NY y volver a anclar a medianoche UTC de esa
# misma fecha reproduce la convencion de DxLink.


def normalize_daily_timestamp(alpaca_ts: datetime) -> datetime:
    ny_date = alpaca_ts.astimezone(_NY).date()
    return datetime(ny_date.year, ny_date.month, ny_date.day, tzinfo=timezone.utc)
