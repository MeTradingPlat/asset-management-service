from fastapi import APIRouter, Query

from app.db.engine import get_connection
from app.models.dto import CandleResponse

router = APIRouter()


@router.get("/historical/candles", response_model=list[CandleResponse])
def get_candles(symbol: str, timeframe: str, bars: int = Query(default=500, le=10000)):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT ts, open, high, low, close, volume, vwap, source
                FROM candles c
                JOIN tracked_symbols ts ON ts.symbol_id = c.symbol_id
                WHERE ts.symbol = %s AND c.timeframe = %s
                ORDER BY c.ts DESC
                LIMIT %s
                """,
                (symbol.upper(), timeframe, bars),
            )
            rows = cur.fetchall()

    return [
        CandleResponse(
            symbol=symbol.upper(), timestamp=row[0], open=row[1], high=row[2], low=row[3],
            close=row[4], volume=row[5], vwap=row[6], source=row[7],
        )
        for row in reversed(rows)
    ]
