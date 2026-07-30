from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from app.discovery.symbol_poller import SymbolPoller


class _FakeCursor:
    def __init__(self, existing_rows):
        self._existing_rows = existing_rows
        self.update_calls = []

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, query, params=None):
        if "SELECT symbol, symbol_id, is_active" in query:
            self._select_result = self._existing_rows
        elif "UPDATE tracked_symbols" in query:
            self.update_calls.append(params[0])

    def fetchall(self):
        return self._select_result


class _FakeConn:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor


def _fake_get_connection(cursor):
    @contextmanager
    def _cm():
        yield _FakeConn(cursor)
    return _cm()


def test_new_symbols_get_inserted_and_watermarks_seeded():
    poller = SymbolPoller()
    poller._marketdata = MagicMock()
    poller._marketdata.fetch_symbols.return_value = {"AAPL": "NASDAQ", "MSFT": "NASDAQ"}

    cursor = _FakeCursor(existing_rows=[])
    inserted_ids = [10, 11]
    seeded_batches = []

    def fake_insert(cur, sql, rows, **kw):
        if "RETURNING symbol_id" in sql:
            return [(i,) for i in inserted_ids]
        seeded_batches.append(rows)

    with patch("app.discovery.symbol_poller.get_connection", lambda: _fake_get_connection(cursor)), \
         patch("app.discovery.symbol_poller.execute_values", side_effect=fake_insert):
        poller.poll()

    assert len(seeded_batches[0]) == len(inserted_ids) * 19


def test_delisted_symbols_are_batched_into_one_update():
    poller = SymbolPoller()
    poller._marketdata = MagicMock()
    poller._marketdata.fetch_symbols.return_value = {"AAPL": "NASDAQ"}

    cursor = _FakeCursor(existing_rows=[("AAPL", 1, True), ("OLD1", 2, True), ("OLD2", 3, True)])

    with patch("app.discovery.symbol_poller.get_connection", lambda: _fake_get_connection(cursor)), \
         patch("app.discovery.symbol_poller.execute_values"):
        poller.poll()

    assert cursor.update_calls == [[2, 3]]
