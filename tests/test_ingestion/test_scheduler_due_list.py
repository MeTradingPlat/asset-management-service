from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from app.ingestion.watermark_repository import fetch_due_rows


class _FakeCursor:
    def __init__(self, rows):
        self._rows = rows

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, *a, **kw):
        pass

    def fetchall(self):
        return self._rows


class _FakeConn:
    def __init__(self, rows):
        self._rows = rows

    def cursor(self):
        return _FakeCursor(self._rows)


@contextmanager
def _fake_get_connection(rows):
    yield _FakeConn(rows)


def test_new_symbol_goes_to_backfill():
    rows = [(1, "AAPL", "D1", False, None, None)]
    with patch("app.ingestion.watermark_repository.get_connection", lambda: _fake_get_connection(rows)):
        backfill, steady = fetch_due_rows()
    assert len(backfill) == 1 and backfill[0].symbol == "AAPL"
    assert steady == []


def test_derived_timeframes_excluded_from_due_list():
    rows = [(1, "AAPL", "D2", True, None, datetime.now(timezone.utc))]
    with patch("app.ingestion.watermark_repository.get_connection", lambda: _fake_get_connection(rows)):
        backfill, steady = fetch_due_rows()
    assert backfill == [] and steady == []


def test_stale_watermark_goes_to_steady_state():
    # M1: ventana viva = 500 * 1min = 500min; 2/3 de eso = ~333min. Con
    # last_ingested_at de hace 400 minutos, ya deberia estar due.
    stale = datetime.now(timezone.utc) - timedelta(minutes=400)
    rows = [(1, "AAPL", "M1", True, None, stale)]
    with patch("app.ingestion.watermark_repository.get_connection", lambda: _fake_get_connection(rows)):
        backfill, steady = fetch_due_rows()
    assert backfill == []
    assert len(steady) == 1 and steady[0].symbol == "AAPL"


def test_fresh_watermark_not_due():
    fresh = datetime.now(timezone.utc) - timedelta(minutes=5)
    rows = [(1, "AAPL", "M1", True, None, fresh)]
    with patch("app.ingestion.watermark_repository.get_connection", lambda: _fake_get_connection(rows)):
        backfill, steady = fetch_due_rows()
    assert backfill == [] and steady == []
