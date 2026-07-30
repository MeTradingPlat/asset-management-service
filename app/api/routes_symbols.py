from fastapi import APIRouter

from app.db.engine import get_connection
from app.models.dto import SymbolResponse, WatermarkResponse

router = APIRouter()


@router.get("/historical/symbols", response_model=list[SymbolResponse])
def get_symbols():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT symbol, market, is_active, first_seen_at FROM tracked_symbols ORDER BY symbol")
            rows = cur.fetchall()
    return [SymbolResponse(symbol=r[0], market=r[1], isActive=r[2], firstSeenAt=r[3]) for r in rows]


@router.get("/historical/watermarks", response_model=list[WatermarkResponse])
def get_watermarks(symbol: str):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT ts.symbol, w.timeframe, w.last_ingested_at, w.oldest_ingested_at, w.backfill_complete
                FROM watermarks w
                JOIN tracked_symbols ts ON ts.symbol_id = w.symbol_id
                WHERE ts.symbol = %s
                ORDER BY w.timeframe
                """,
                (symbol.upper(),),
            )
            rows = cur.fetchall()
    return [
        WatermarkResponse(symbol=r[0], timeframe=r[1], lastIngestedAt=r[2], oldestIngestedAt=r[3], backfillComplete=r[4])
        for r in rows
    ]
