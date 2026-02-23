import asyncio
from types import SimpleNamespace

from fastapi import HTTPException

from api import auth
from core.error_handler import ErrorHandler
from schemas.user_schema import ForgotPasswordRequest


class _FakeResult:
    def __init__(self, user):
        self._user = user

    def scalar_one_or_none(self):
        return self._user


class _FakeDB:
    def __init__(self, user):
        self.user = user
        self.execute_called = False
        self.commit_called = False
        self.rollback_called = False

    async def execute(self, _query):
        self.execute_called = True
        return _FakeResult(self.user)

    async def commit(self):
        self.commit_called = True

    async def rollback(self):
        self.rollback_called = True


def _build_request(client_ip="127.0.0.1", x_forwarded_for=None):
    headers = []
    if x_forwarded_for is not None:
        headers.append((b"x-forwarded-for", x_forwarded_for.encode("utf-8")))

    return auth.Request(
        scope={
            "type": "http",
            "method": "POST",
            "path": "/auth/forgot-password",
            "headers": headers,
            "client": (client_ip, 12345),
            "query_string": b"",
            "scheme": "http",
            "server": ("testserver", 80),
            "http_version": "1.1",
        }
    )


def test_forgot_password_unthrottled(monkeypatch):
    user = SimpleNamespace(id=101, email="user@example.com", reset_token=None, reset_token_used=True)
    db = _FakeDB(user=user)
    limiter_calls = []

    def _limit_ok(key, limit, window):
        limiter_calls.append((key, limit, window))

    monkeypatch.setattr(auth, "rate_limit_key", _limit_ok)
    monkeypatch.setattr(auth, "create_access_token", lambda data: "reset-token-abc")
    monkeypatch.setattr(auth, "send_reset_email", lambda to, reset_token: True)

    payload = ForgotPasswordRequest(email="user@example.com")
    request = _build_request(client_ip="10.20.30.40")

    response = asyncio.run(auth.forgot_password(payload, request, db))

    assert response["message"] == "If the email exists, a reset link has been sent"
    assert limiter_calls == [("forgot_password:10.20.30.40", 5, 3600)]
    assert db.execute_called is True
    assert db.commit_called is True
    assert user.reset_token == "reset-token-abc"
    assert user.reset_token_used is False


def test_forgot_password_throttled_returns_429_and_skips_db(monkeypatch):
    user = SimpleNamespace(id=202, email="user@example.com", reset_token=None, reset_token_used=False)
    db = _FakeDB(user=user)

    def _limit_fail(key, limit, window):
        raise ErrorHandler.rate_limited("Too many requests")

    monkeypatch.setattr(auth, "rate_limit_key", _limit_fail)

    payload = ForgotPasswordRequest(email="user@example.com")
    request = _build_request(client_ip="9.9.9.9", x_forwarded_for="7.7.7.7, 1.1.1.1")

    try:
        asyncio.run(auth.forgot_password(payload, request, db))
        assert False, "Expected HTTPException 429"
    except HTTPException as exc:
        assert exc.status_code == 429

    assert db.execute_called is False
    assert db.commit_called is False
