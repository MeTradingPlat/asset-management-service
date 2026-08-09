from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from app.domain.aggregation import Bar
from app.ingestion.scheduler import Scheduler
from app.ingestion.watermark_repository import DueRow


def _row(symbol: str, symbol_id: int) -> DueRow:
    return DueRow(symbol_id=symbol_id, symbol=symbol, timeframe="D1",
                  backfill_complete=False, oldest_ingested_at=None)


def _bar(ts: datetime) -> Bar:
    return Bar(ts=ts, open=1, high=1, low=1, close=1, volume=1)


def _streaming(pages: list[dict[str, list]]):
    def fake_streaming(symbols, timeframe, start, end, on_page):
        for page in pages:
            on_page(page)
    return fake_streaming


def test_each_page_is_written_as_it_arrives_not_buffered():
    # El punto central del fix: nunca debe existir un momento en el que TODAS
    # las paginas ya llegaron pero write_bars todavia no se llamo ninguna vez.
    scheduler = Scheduler()
    row = _row("AAPL", 1)
    writes_seen_during_streaming = []

    def fake_streaming(symbols, timeframe, start, end, on_page):
        on_page({"AAPL": [_bar(datetime(2020, 1, 1, tzinfo=timezone.utc))]})
        writes_seen_during_streaming.append(mock_write.call_count)
        on_page({"AAPL": [_bar(datetime(2020, 1, 2, tzinfo=timezone.utc))]})
        writes_seen_during_streaming.append(mock_write.call_count)

    with patch.object(scheduler._alpaca, "get_bars_streaming", side_effect=fake_streaming), \
         patch("app.ingestion.scheduler.write_bars",
               side_effect=lambda symbol_id, timeframe, bars, **kw: bars) as mock_write, \
         patch("app.ingestion.scheduler.update_watermark"):
        scheduler._fetch_and_write_batch([row], "D1", is_backfill=True)

    assert writes_seen_during_streaming == [1, 2]


def test_watermark_range_merges_across_pages_for_the_same_symbol():
    scheduler = Scheduler()
    row = _row("AAPL", 1)
    older = datetime(2019, 1, 1, tzinfo=timezone.utc)
    newer = datetime(2021, 1, 1, tzinfo=timezone.utc)
    pages = [{"AAPL": [_bar(newer)]}, {"AAPL": [_bar(older)]}]

    with patch.object(scheduler._alpaca, "get_bars_streaming", side_effect=_streaming(pages)), \
         patch("app.ingestion.scheduler.write_bars", side_effect=lambda symbol_id, timeframe, bars, **kw: bars), \
         patch("app.ingestion.scheduler.update_watermark") as mock_watermark:
        scheduler._fetch_and_write_batch([row], "D1", is_backfill=True)

    calls = mock_watermark.call_args_list
    assert len(calls) == 2
    assert calls[0].kwargs["newest_ts"] == newer
    assert calls[1].kwargs["oldest_ts"] == older


def test_symbol_missing_from_every_page_is_treated_as_exhausted():
    scheduler = Scheduler()
    rows = [_row("AAPL", 1), _row("MSFT", 2)]
    # Solo AAPL aparece en la pagina -- MSFT nunca aparece en ninguna.
    pages = [{"AAPL": [_bar(datetime(2020, 1, 1, tzinfo=timezone.utc))]}]

    with patch.object(scheduler._alpaca, "get_bars_streaming", side_effect=_streaming(pages)), \
         patch("app.ingestion.scheduler.write_bars",
               side_effect=lambda symbol_id, timeframe, bars, **kw: bars) as mock_write, \
         patch("app.ingestion.scheduler.derive_daily_aggregates") as mock_derive, \
         patch("app.ingestion.scheduler.update_watermark"):
        scheduler._fetch_and_write_batch(rows, "D1", is_backfill=True)

    written_symbol_ids = {call.args[0] for call in mock_write.call_args_list}
    assert written_symbol_ids == {1, 2}
    mock_derive.assert_called_once_with(2)
