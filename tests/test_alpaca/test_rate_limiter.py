from app.alpaca.rate_limiter import TokenBucket


def test_acquire_consumes_tokens():
    bucket = TokenBucket(capacity=5)
    for _ in range(5):
        assert bucket.try_acquire()
    assert not bucket.try_acquire()


def test_available_reports_remaining():
    bucket = TokenBucket(capacity=10)
    bucket.try_acquire(4)
    assert bucket.available() == 6
