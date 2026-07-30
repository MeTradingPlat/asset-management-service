from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.api.server import create_app


class _FakeCursor:
    def __init__(self, rows):
        self._rows = rows
        self.last_query = None
        self.last_params = None

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, query, params):
        self.last_query = query
        self.last_params = params

    def fetchall(self):
        return self._rows


class _FakeConn:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor


def test_before_param_adds_filter_and_is_passed_to_query():
    ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
    cursor = _FakeCursor([(ts, 1, 2, 0.5, 1.5, 100, 1.1, "alpaca_native")])

    @contextmanager
    def fake_get_connection():
        yield _FakeConn(cursor)

    with patch("app.api.routes_candles.get_connection", fake_get_connection):
        client = TestClient(create_app())
        resp = client.get(
            "/historical/candles",
            params={"symbol": "AAPL", "timeframe": "D1", "bars": 10, "before": "2026-01-05T00:00:00Z"},
        )

    assert resp.status_code == 200
    assert "AND c.ts < %s" in cursor.last_query
    assert cursor.last_params[2] is not None


def test_without_before_omits_filter():
    cursor = _FakeCursor([])

    @contextmanager
    def fake_get_connection():
        yield _FakeConn(cursor)

    with patch("app.api.routes_candles.get_connection", fake_get_connection):
        client = TestClient(create_app())
        resp = client.get("/historical/candles", params={"symbol": "AAPL", "timeframe": "D1"})

    assert resp.status_code == 200
    assert "AND c.ts < %s" not in cursor.last_query
    assert len(cursor.last_params) == 3
