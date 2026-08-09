from datetime import datetime, timezone
from unittest.mock import patch

from app.domain.aggregation import Bar
from app.ingestion.scheduler import Scheduler, _BACKFILL_START
from app.ingestion.watermark_repository import DueRow


def _row(symbol: str, symbol_id: int = 1, oldest_ingested_at=None, timeframe: str = "M1") -> DueRow:
    return DueRow(symbol_id=symbol_id, symbol=symbol, timeframe=timeframe,
                  backfill_complete=False, oldest_ingested_at=oldest_ingested_at)


def _bar() -> Bar:
    return Bar(ts=datetime.now(timezone.utc), open=1, high=1, low=1, close=1, volume=1)


def test_minute_backfill_splits_into_yearly_windows():
    scheduler = Scheduler()
    row = _row("AAPL", oldest_ingested_at=datetime(2021, 6, 1, tzinfo=timezone.utc))
    ranges_requested = []

    def fake_streaming(symbols, timeframe, start, end, on_page):
        ranges_requested.append((start, end))
        on_page({"AAPL": [_bar()]})

    with patch.object(scheduler._alpaca, "get_bars_streaming", side_effect=fake_streaming), \
         patch("app.ingestion.scheduler.write_bars"), \
         patch("app.ingestion.scheduler.update_watermark"):
        scheduler._fetch_and_write_batch([row], "M1", is_backfill=True)

    # 2021-06-01 -> 2018-01-01 en ventanas de 365 dias: 4 llamadas, cada una
    # mas atras en el tiempo, la ultima tocando exactamente _BACKFILL_START.
    assert len(ranges_requested) == 4
    assert ranges_requested[0][1] == datetime(2021, 6, 1, tzinfo=timezone.utc)
    assert ranges_requested[-1][0] == _BACKFILL_START
    for i in range(len(ranges_requested) - 1):
        assert ranges_requested[i][0] == ranges_requested[i + 1][1]


def test_empty_intermediate_window_does_not_mark_complete():
    scheduler = Scheduler()
    row = _row("AAPL", oldest_ingested_at=datetime(2021, 6, 1, tzinfo=timezone.utc))

    def fake_streaming(symbols, timeframe, start, end, on_page):
        pass  # ninguna ventana trae datos -- simula un simbolo suspendido/joven

    with patch.object(scheduler._alpaca, "get_bars_streaming", side_effect=fake_streaming), \
         patch("app.ingestion.scheduler.write_bars"), \
         patch("app.ingestion.scheduler.update_watermark") as mock_watermark:
        scheduler._fetch_and_write_batch([row], "M1", is_backfill=True)

    calls = mock_watermark.call_args_list
    # Ninguna llamada intermedia marca completo...
    for call in calls[:-1]:
        assert call.kwargs.get("backfill_complete") is not True
    # ...solo la ultima, que es la que de verdad llega a _BACKFILL_START.
    assert calls[-1].kwargs.get("backfill_complete") is True


def test_final_empty_window_marks_complete_and_derives_for_d1_only():
    scheduler = Scheduler()
    row = _row("AAPL", oldest_ingested_at=datetime(2018, 6, 1, tzinfo=timezone.utc))

    def fake_streaming(symbols, timeframe, start, end, on_page):
        pass

    with patch.object(scheduler._alpaca, "get_bars_streaming", side_effect=fake_streaming), \
         patch("app.ingestion.scheduler.write_bars"), \
         patch("app.ingestion.scheduler.derive_daily_aggregates") as mock_derive, \
         patch("app.ingestion.scheduler.update_watermark") as mock_watermark:
        scheduler._fetch_and_write_batch([row], "M1", is_backfill=True)

    mock_watermark.assert_called_once()
    assert mock_watermark.call_args.kwargs["backfill_complete"] is True
    mock_derive.assert_not_called()  # M1 no deriva D2/D3, solo D1


def test_non_minute_timeframe_still_uses_a_single_call():
    scheduler = Scheduler()
    row = _row("AAPL", timeframe="D1")
    calls = []

    def fake_streaming(symbols, timeframe, start, end, on_page):
        calls.append((start, end))
        on_page({"AAPL": [_bar()]})

    with patch.object(scheduler._alpaca, "get_bars_streaming", side_effect=fake_streaming), \
         patch("app.ingestion.scheduler.write_bars"), \
         patch("app.ingestion.scheduler.update_watermark"):
        scheduler._fetch_and_write_batch([row], "D1", is_backfill=True)

    assert len(calls) == 1
    assert calls[0][0] == _BACKFILL_START
