from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from app.domain.aggregation import Bar
from app.ingestion.scheduler import Scheduler
from app.ingestion.watermark_repository import DueRow


def _row(symbol: str, symbol_id: int = 1) -> DueRow:
    return DueRow(symbol_id=symbol_id, symbol=symbol, timeframe="D1",
                  backfill_complete=False, oldest_ingested_at=None)


def _bar() -> Bar:
    return Bar(ts=datetime.now(timezone.utc), open=1, high=1, low=1, close=1, volume=1)


def _streaming(pages: list[dict[str, list]]):
    def fake_streaming(symbols, timeframe, start, end, on_page):
        for page in pages:
            on_page(page)
    return fake_streaming


def test_backfill_batch_skips_derive_while_still_receiving_bars():
    scheduler = Scheduler()
    row = _row("AAPL")
    with patch.object(scheduler._alpaca, "get_bars_streaming", side_effect=_streaming([{"AAPL": [_bar()]}])), \
         patch("app.ingestion.scheduler.write_bars") as mock_write, \
         patch("app.ingestion.scheduler.derive_daily_aggregates") as mock_derive, \
         patch("app.ingestion.scheduler.update_watermark"):
        scheduler._fetch_and_write_batch([row], "D1", is_backfill=True)

    mock_write.assert_called_once()
    assert mock_write.call_args.kwargs["derive"] is False
    mock_derive.assert_not_called()


def test_backfill_batch_derives_once_when_symbol_history_is_exhausted():
    scheduler = Scheduler()
    row = _row("AAPL")
    with patch.object(scheduler._alpaca, "get_bars_streaming", side_effect=_streaming([])), \
         patch("app.ingestion.scheduler.write_bars") as mock_write, \
         patch("app.ingestion.scheduler.derive_daily_aggregates") as mock_derive, \
         patch("app.ingestion.scheduler.update_watermark"):
        scheduler._fetch_and_write_batch([row], "D1", is_backfill=True)

    mock_derive.assert_called_once_with(row.symbol_id)


def test_steady_state_batch_still_derives_every_time():
    scheduler = Scheduler()
    row = _row("AAPL")
    with patch.object(scheduler._alpaca, "get_bars_streaming", side_effect=_streaming([{"AAPL": [_bar()]}])), \
         patch("app.ingestion.scheduler.write_bars") as mock_write, \
         patch("app.ingestion.scheduler.derive_daily_aggregates") as mock_derive, \
         patch("app.ingestion.scheduler.update_watermark"):
        scheduler._fetch_and_write_batch([row], "D1", is_backfill=False)

    mock_write.assert_called_once()
    assert mock_write.call_args.kwargs["derive"] is True
    mock_derive.assert_not_called()
