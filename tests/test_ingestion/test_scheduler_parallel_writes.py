from datetime import datetime, timezone
from unittest.mock import patch

from app.domain.aggregation import Bar
from app.ingestion.scheduler import Scheduler
from app.ingestion.watermark_repository import DueRow


def _row(symbol: str, symbol_id: int) -> DueRow:
    return DueRow(symbol_id=symbol_id, symbol=symbol, timeframe="D1",
                  backfill_complete=False, oldest_ingested_at=None)


def _bar() -> Bar:
    return Bar(ts=datetime.now(timezone.utc), open=1, high=1, low=1, close=1, volume=1)


def test_all_symbols_in_batch_get_written():
    scheduler = Scheduler()
    rows = [_row(sym, i) for i, sym in enumerate(["AAPL", "MSFT", "TSLA"])]
    bars_by_symbol = {sym: [_bar()] for sym in ["AAPL", "MSFT", "TSLA"]}
    with patch.object(scheduler._alpaca, "get_bars", return_value=bars_by_symbol), \
         patch("app.ingestion.scheduler.write_bars") as mock_write, \
         patch("app.ingestion.scheduler.update_watermark"):
        scheduler._fetch_and_write_batch(rows, "D1", is_backfill=True)

    written_symbol_ids = {call.args[0] for call in mock_write.call_args_list}
    assert written_symbol_ids == {0, 1, 2}


def test_one_symbol_failing_does_not_block_the_others():
    scheduler = Scheduler()
    rows = [_row(sym, i) for i, sym in enumerate(["AAPL", "MSFT", "TSLA"])]
    bars_by_symbol = {sym: [_bar()] for sym in ["AAPL", "MSFT", "TSLA"]}

    def flaky_write(symbol_id, *a, **kw):
        if symbol_id == 1:
            raise RuntimeError("DB write boom")

    with patch.object(scheduler._alpaca, "get_bars", return_value=bars_by_symbol), \
         patch("app.ingestion.scheduler.write_bars", side_effect=flaky_write) as mock_write, \
         patch("app.ingestion.scheduler.update_watermark") as mock_watermark:
        scheduler._fetch_and_write_batch(rows, "D1", is_backfill=True)

    written_symbol_ids = {call.args[0] for call in mock_write.call_args_list}
    assert written_symbol_ids == {0, 1, 2}
    # symbol_id=1 fallo antes de llegar a update_watermark -- los otros dos si.
    watermarked_symbol_ids = {call.args[0] for call in mock_watermark.call_args_list}
    assert watermarked_symbol_ids == {0, 2}
