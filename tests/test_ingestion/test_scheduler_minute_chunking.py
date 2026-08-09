from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from app.domain.aggregation import Bar
from app.domain.retention import RETENTION_DAYS
from app.ingestion.scheduler import Scheduler
from app.ingestion.watermark_repository import DueRow


def _row(symbol: str, symbol_id: int = 1, oldest_ingested_at=None, timeframe: str = "M1") -> DueRow:
    return DueRow(symbol_id=symbol_id, symbol=symbol, timeframe=timeframe,
                  backfill_complete=False, oldest_ingested_at=oldest_ingested_at)


def _bar() -> Bar:
    return Bar(ts=datetime.now(timezone.utc), open=1, high=1, low=1, close=1, volume=1)


def test_minute_backfill_stays_within_the_retention_window():
    scheduler = Scheduler()
    now = datetime.now(timezone.utc)
    row = _row("AAPL", oldest_ingested_at=now)
    ranges_requested = []

    def fake_streaming(symbols, timeframe, start, end, on_page):
        ranges_requested.append((start, end))
        on_page({"AAPL": [_bar()]})

    with patch.object(scheduler._alpaca, "get_bars_streaming", side_effect=fake_streaming), \
         patch("app.ingestion.scheduler.write_bars", side_effect=lambda symbol_id, timeframe, bars, **kw: bars), \
         patch("app.ingestion.scheduler.update_watermark"):
        scheduler._fetch_and_write_batch([row], "M1", is_backfill=True)

    # M1 solo guarda RETENTION_DAYS["M1"] dias, no 7.5 anios completos.
    assert len(ranges_requested) == 1
    oldest_requested = ranges_requested[0][0]
    assert now - oldest_requested <= timedelta(days=RETENTION_DAYS["M1"] + 1)


def test_symbol_already_within_retention_window_skips_alpaca_entirely():
    scheduler = Scheduler()
    now = datetime.now(timezone.utc)
    # Ya tiene datos mas atras de lo que la ventana de retencion pide (ej.
    # quedo de una ventana vieja mas larga) -- no hace falta pedir nada.
    row = _row("AAPL", oldest_ingested_at=now - timedelta(days=RETENTION_DAYS["M1"] + 10))

    with patch.object(scheduler._alpaca, "get_bars_streaming") as mock_streaming, \
         patch("app.ingestion.scheduler.update_watermark") as mock_watermark:
        scheduler._fetch_and_write_batch([row], "M1", is_backfill=True)

    mock_streaming.assert_not_called()
    mock_watermark.assert_called_once()
    assert mock_watermark.call_args.kwargs["backfill_complete"] is True


def test_empty_intermediate_chunk_does_not_mark_complete():
    scheduler = Scheduler()
    now = datetime.now(timezone.utc)
    row = _row("AAPL", oldest_ingested_at=now)

    def fake_streaming(symbols, timeframe, start, end, on_page):
        pass  # ningun trozo trae datos -- simula un simbolo suspendido/joven

    with patch.object(scheduler._alpaca, "get_bars_streaming", side_effect=fake_streaming), \
         patch("app.ingestion.scheduler.write_bars", side_effect=lambda symbol_id, timeframe, bars, **kw: bars), \
         patch("app.config.settings.backfill_minute_chunk_days", 20), \
         patch("app.ingestion.scheduler.update_watermark") as mock_watermark:
        scheduler._fetch_and_write_batch([row], "M1", is_backfill=True)

    calls = mock_watermark.call_args_list
    assert len(calls) > 1  # con trozos de 20 dias, 60 dias de ventana se parte en varios
    for call in calls[:-1]:
        assert call.kwargs.get("backfill_complete") is not True
    assert calls[-1].kwargs.get("backfill_complete") is True


def test_re_fetch_excludes_already_known_oldest_bar():
    # Bug real observado en produccion: si el rango pedido incluye
    # (inclusive) la barra mas vieja que ya se tiene, y la historia real del
    # simbolo termina justo ahi (IPO reciente, cambio de ticker), Alpaca
    # vuelve a devolver esa misma barra para siempre -- nunca llega un
    # "vacio" genuino y el simbolo se queda pegado sin avanzar (confirmado
    # en vivo: 5,284/13,132 simbolos de D1 atascados horas re-pidiendo la
    # misma barra). El end pedido a Alpaca debe ser estrictamente anterior
    # a la barra mas vieja ya conocida.
    scheduler = Scheduler()
    known_oldest = datetime(2021, 8, 11, 4, 0, tzinfo=timezone.utc)
    row = _row("AAPL", oldest_ingested_at=known_oldest, timeframe="D1")

    def fake_streaming(symbols, timeframe, start, end, on_page):
        assert end < known_oldest

    with patch.object(scheduler._alpaca, "get_bars_streaming", side_effect=fake_streaming), \
         patch("app.ingestion.scheduler.update_watermark") as mock_watermark:
        scheduler._fetch_and_write_batch([row], "D1", is_backfill=True)

    # Respuesta genuinamente vacia (nada antes de known_oldest) -- ahora si
    # se marca completo en vez de quedar pegado reintentando lo mismo.
    mock_watermark.assert_called_once()
    assert mock_watermark.call_args.kwargs["backfill_complete"] is True


def test_non_minute_timeframe_still_uses_a_single_call():
    scheduler = Scheduler()
    now = datetime.now(timezone.utc)
    row = _row("AAPL", oldest_ingested_at=now, timeframe="D1")
    calls = []

    def fake_streaming(symbols, timeframe, start, end, on_page):
        calls.append((start, end))
        on_page({"AAPL": [_bar()]})

    with patch.object(scheduler._alpaca, "get_bars_streaming", side_effect=fake_streaming), \
         patch("app.ingestion.scheduler.write_bars", side_effect=lambda symbol_id, timeframe, bars, **kw: bars), \
         patch("app.ingestion.scheduler.update_watermark"):
        scheduler._fetch_and_write_batch([row], "D1", is_backfill=True)

    assert len(calls) == 1
    assert now - calls[0][0] <= timedelta(days=RETENTION_DAYS["D1"] + 1)
