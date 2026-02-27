"""Tests for the AI service circuit breaker."""
import time


from app.services.ai_service import (
    CircuitBreakerOpenError,
    _CircuitBreaker,
)


class TestCircuitBreaker:
    def test_starts_closed(self):
        cb = _CircuitBreaker(threshold=3, recovery=10)
        assert cb.allow_request() is True

    def test_opens_after_threshold_failures(self):
        cb = _CircuitBreaker(threshold=3, recovery=10)
        cb.record_failure()
        cb.record_failure()
        assert cb.allow_request() is True  # still closed at 2
        cb.record_failure()
        assert cb.allow_request() is False  # opened at 3

    def test_success_resets_count(self):
        cb = _CircuitBreaker(threshold=3, recovery=10)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        cb.record_failure()
        cb.record_failure()
        assert cb.allow_request() is True  # only 2 consecutive failures

    def test_half_open_after_recovery(self):
        cb = _CircuitBreaker(threshold=2, recovery=1)
        cb.record_failure()
        cb.record_failure()
        assert cb.allow_request() is False  # open, recovery not yet elapsed
        # Simulate time passing by backdating the last failure
        cb._last_failure_time = time.monotonic() - 2
        assert cb.allow_request() is True  # recovery elapsed → half_open probe

    def test_success_in_half_open_closes(self):
        cb = _CircuitBreaker(threshold=2, recovery=1)
        cb.record_failure()
        cb.record_failure()
        cb._last_failure_time = time.monotonic() - 2
        assert cb.allow_request() is True  # half_open probe
        cb.record_success()
        assert cb.allow_request() is True  # back to closed

    def test_failure_in_half_open_reopens(self):
        cb = _CircuitBreaker(threshold=2, recovery=1)
        cb.record_failure()
        cb.record_failure()
        cb._last_failure_time = time.monotonic() - 2
        cb.allow_request()  # transition to half_open
        cb.record_failure()  # probe failed → reopens
        assert cb.allow_request() is False  # reopened, recovery not yet elapsed

    def test_circuit_breaker_open_exception(self):
        exc = CircuitBreakerOpenError()
        assert "temporarily unavailable" in str(exc)
