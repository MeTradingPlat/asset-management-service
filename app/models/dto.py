from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CandleResponse(BaseModel):
    """Mismos nombres de campo que el CandleResponse de
    signal-processing-service/marketdata-service, para que consumirlo desde
    ahi no necesite una capa de traduccion aparte."""
    symbol: str
    timestamp: datetime
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None
    volume: Optional[float] = None
    vwap: Optional[float] = None
    source: str


class SymbolResponse(BaseModel):
    symbol: str
    market: str
    isActive: bool
    firstSeenAt: datetime


class WatermarkResponse(BaseModel):
    symbol: str
    timeframe: str
    lastIngestedAt: Optional[datetime] = None
    oldestIngestedAt: Optional[datetime] = None
    backfillComplete: bool
