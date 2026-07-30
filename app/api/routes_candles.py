from datetime import datetime

from fastapi import APIRouter, Query

from app.db.engine import get_connection
from app.models.dto import CandleResponse

router = APIRouter()


@router.get("/historical/candles", response_model=list[CandleResponse])
def get_candles(
    symbol: str, timeframe: str, bars: int = Query(default=500, le=10000),
    before: datetime | None = None,
):
    """Sin `before`, trae las N barras mas recientes. Con `before`, trae las
    N barras mas recientes ANTERIORES a esa fecha -- lo que necesita
    marketdata-service para rellenar el hueco justo donde termina la
    ventana en vivo de DxLink, sin traer barras que ya tiene."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT ts, open, high, low, close, volume, vwap, source
                FROM candles c
                JOIN tracked_symbols ts ON ts.symbol_id = c.symbol_id
                WHERE ts.symbol = %s AND c.timeframe = %s
                {"AND c.ts < %s" if before else ""}
                ORDER BY c.ts DESC
                LIMIT %s
                """,
                (symbol.upper(), timeframe, before, bars) if before
                else (symbol.upper(), timeframe, bars),
            )
            rows = cur.fetchall()

    return [
        CandleResponse(
            symbol=symbol.upper(), timestamp=row[0], open=row[1], high=row[2], low=row[3],
            close=row[4], volume=row[5], vwap=row[6], source=row[7],
        )
        for row in reversed(rows)
    ]
