import threading
import time

from app.config import settings


class TokenBucket:
    """Token bucket simple, thread-safe -- HD_ALPACA_CALLS_PER_MINUTE tokens
    se recargan de forma continua (no en un solo golpe cada minuto), asi que
    el consumo se reparte parejo en vez de ráfagas."""

    def __init__(self, capacity: int | None = None):
        self.capacity = capacity or settings.alpaca_calls_per_minute
        self._tokens = float(self.capacity)
        self._refill_per_sec = self.capacity / 60.0
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()
        # Alpaca aplica, ademas del promedio/min, algun tope de rafaga corto
        # no documentado -- confirmado en vivo: varios workers pidiendo su
        # token casi al mismo milisegundo (todos con presupuesto de sobra en
        # el promedio) igual reciben 429. Cuando Alpaca lo devuelve, manda su
        # propio "Retry-After" -- blocked_until frena a TODOS los hilos que
        # comparten este limiter hasta esa hora exacta, en vez de que cada
        # uno siga reintentando por su cuenta y siga chocando con el mismo
        # tope.
        self._blocked_until: float = 0.0

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self.capacity, self._tokens + elapsed * self._refill_per_sec)
        self._last_refill = now

    def try_acquire(self, n: int = 1) -> bool:
        with self._lock:
            if time.monotonic() < self._blocked_until:
                return False
            self._refill()
            if self._tokens >= n:
                self._tokens -= n
                return True
            return False

    def penalize(self, seconds: float) -> None:
        with self._lock:
            self._blocked_until = max(self._blocked_until, time.monotonic() + seconds)

    def available(self) -> int:
        with self._lock:
            self._refill()
            return int(self._tokens)
