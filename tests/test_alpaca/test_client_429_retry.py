import json
import urllib.error
from unittest.mock import MagicMock, patch

from app.alpaca.client import AlpacaClient
from app.alpaca.rate_limiter import TokenBucket


def _http_error(code: int, retry_after: str | None) -> urllib.error.HTTPError:
    headers = {"Retry-After": retry_after} if retry_after else {}
    return urllib.error.HTTPError("https://data.alpaca.markets/v2/stocks/bars", code, "err", headers, None)


def _ok_response(body: dict) -> MagicMock:
    resp = MagicMock()
    resp.__enter__.return_value = resp
    resp.__exit__.return_value = False
    resp.read.return_value = json.dumps(body).encode()
    return resp


def test_429_retries_and_succeeds_using_retry_after_header():
    bucket = TokenBucket(capacity=200)
    client = AlpacaClient(bucket)
    with patch("app.alpaca.client.urllib.request.urlopen",
               side_effect=[_http_error(429, "0.01"), _ok_response({"bars": {}})]) as mock_urlopen, \
         patch("app.alpaca.client.time.sleep") as mock_sleep, \
         patch("app.alpaca.client.random.uniform", return_value=0.0):
        result = client.get_bars(["AAPL"], "D1", __import__("datetime").datetime(2020, 1, 1), __import__("datetime").datetime(2020, 1, 2))

    assert result == {"AAPL": []}
    assert mock_urlopen.call_count == 2
    mock_sleep.assert_called_once_with(0.01)


def test_429_retry_wait_has_jitter_so_workers_desync():
    bucket = TokenBucket(capacity=200)
    client = AlpacaClient(bucket)
    with patch("app.alpaca.client.urllib.request.urlopen",
               side_effect=[_http_error(429, "1"), _ok_response({"bars": {}})]), \
         patch("app.alpaca.client.time.sleep") as mock_sleep, \
         patch("app.alpaca.client.random.uniform", return_value=0.7) as mock_uniform:
        client.get_bars(["AAPL"], "D1", __import__("datetime").datetime(2020, 1, 1), __import__("datetime").datetime(2020, 1, 2))

    mock_uniform.assert_called_once_with(0, 1.5)
    mock_sleep.assert_called_once_with(1.7)


def test_429_without_retry_after_header_uses_default():
    bucket = TokenBucket(capacity=200)
    client = AlpacaClient(bucket)
    with patch("app.alpaca.client.urllib.request.urlopen",
               side_effect=[_http_error(429, None), _ok_response({"bars": {}})]), \
         patch("app.alpaca.client.time.sleep") as mock_sleep:
        client.get_bars(["AAPL"], "D1", __import__("datetime").datetime(2020, 1, 1), __import__("datetime").datetime(2020, 1, 2))

    mock_sleep.assert_called_once()
    assert mock_sleep.call_args.args[0] > 0


def test_429_penalizes_shared_rate_limiter_so_other_threads_back_off_too():
    bucket = TokenBucket(capacity=200)
    client = AlpacaClient(bucket)
    with patch("app.alpaca.client.urllib.request.urlopen",
               side_effect=[_http_error(429, "5"), _ok_response({"bars": {}})]), \
         patch("app.alpaca.client.time.sleep"):
        client.get_bars(["AAPL"], "D1", __import__("datetime").datetime(2020, 1, 1), __import__("datetime").datetime(2020, 1, 2))

    assert not bucket.try_acquire()


def test_non_transient_http_error_is_not_retried():
    bucket = TokenBucket(capacity=200)
    client = AlpacaClient(bucket)
    with patch("app.alpaca.client.urllib.request.urlopen", side_effect=_http_error(404, None)) as mock_urlopen:
        try:
            client.get_bars(["AAPL"], "D1", __import__("datetime").datetime(2020, 1, 1), __import__("datetime").datetime(2020, 1, 2))
            assert False, "expected HTTPError to propagate"
        except urllib.error.HTTPError as e:
            assert e.code == 404

    assert mock_urlopen.call_count == 1


def test_transient_http_error_retries_and_succeeds():
    bucket = TokenBucket(capacity=200)
    client = AlpacaClient(bucket)
    with patch("app.alpaca.client.urllib.request.urlopen",
               side_effect=[_http_error(401, None), _ok_response({"bars": {}})]) as mock_urlopen, \
         patch("app.alpaca.client.time.sleep") as mock_sleep:
        result = client.get_bars(["AAPL"], "D1", __import__("datetime").datetime(2020, 1, 1), __import__("datetime").datetime(2020, 1, 2))

    assert result == {"AAPL": []}
    assert mock_urlopen.call_count == 2
    mock_sleep.assert_called_once()


def test_transient_http_error_gives_up_after_max_retries():
    bucket = TokenBucket(capacity=200)
    client = AlpacaClient(bucket)
    errors = [_http_error(500, None)] * 10
    with patch("app.alpaca.client.urllib.request.urlopen", side_effect=errors) as mock_urlopen, \
         patch("app.alpaca.client.time.sleep"):
        try:
            client.get_bars(["AAPL"], "D1", __import__("datetime").datetime(2020, 1, 1), __import__("datetime").datetime(2020, 1, 2))
            assert False, "expected HTTPError to propagate after exhausting retries"
        except urllib.error.HTTPError as e:
            assert e.code == 500

    from app.alpaca.client import _MAX_TRANSIENT_RETRIES
    assert mock_urlopen.call_count == _MAX_TRANSIENT_RETRIES + 1


def test_429_gives_up_after_max_retries():
    bucket = TokenBucket(capacity=200)
    client = AlpacaClient(bucket)
    errors = [_http_error(429, "0.01")] * 10
    with patch("app.alpaca.client.urllib.request.urlopen", side_effect=errors) as mock_urlopen, \
         patch("app.alpaca.client.time.sleep"):
        try:
            client.get_bars(["AAPL"], "D1", __import__("datetime").datetime(2020, 1, 1), __import__("datetime").datetime(2020, 1, 2))
            assert False, "expected HTTPError to propagate after exhausting retries"
        except urllib.error.HTTPError as e:
            assert e.code == 429

    from app.alpaca.client import _MAX_429_RETRIES
    assert mock_urlopen.call_count == _MAX_429_RETRIES + 1
