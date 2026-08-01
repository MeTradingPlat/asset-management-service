import time

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


def test_penalize_blocks_acquire_even_with_tokens_available():
    bucket = TokenBucket(capacity=10)
    bucket.penalize(0.2)
    assert not bucket.try_acquire()
    time.sleep(0.25)
    assert bucket.try_acquire()


def test_penalize_never_shortens_an_existing_longer_block():
    bucket = TokenBucket(capacity=10)
    bucket.penalize(0.3)
    bucket.penalize(0.05)
    assert not bucket.try_acquire()
    time.sleep(0.1)
    assert not bucket.try_acquire()
