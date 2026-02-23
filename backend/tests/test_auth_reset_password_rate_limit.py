import asyncio
from types import SimpleNamespace

from fastapi import HTTPException

from api import auth
from core.error_handler import ErrorHandler
from schemas.user_schema import ResetPasswordRequest


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
            "path": "/auth/reset-password",
            "headers": headers,
            "client": (client_ip, 12345),
            "query_string": b"",
            "scheme": "http",
            "server": ("testserver", 80),
            "http_version": "1.1",
        }
    )


def test_reset_password_unthrottled(monkeypatch):
    token = "reset-token-xyz"
    user = SimpleNamespace(id=303, reset_token=token, reset_token_used=False, password_hash="old-hash")
    db = _FakeDB(user=user)
    limiter_calls = []

    def _limit_ok(key, limit, window):
        limiter_calls.append((key, limit, window))

    monkeypatch.setattr(auth, "rate_limit_key", _limit_ok)
    monkeypatch.setattr(auth, "decode_access_token", lambda _token: "303")
    monkeypatch.setattr(auth, "hash_password", lambda _password: "new-hash")
    monkeypatch.setattr(auth, "create_access_token", lambda data: "new-access-token")

    payload = ResetPasswordRequest(token=token, new_password="StrongPass1")
    request = _build_request(client_ip="20.30.40.50")

    response = asyncio.run(auth.reset_password(payload, request, db))

    assert response.token == "new-access-token"
    assert len(limiter_calls) == 1
    key, limit, window = limiter_calls[0]
    assert key.startswith("reset_password:20.30.40.50:")
    assert limit == 10
    assert window == 3600
    assert db.execute_called is True
    assert db.commit_called is True
    assert user.password_hash == "new-hash"
    assert user.reset_token_used is True
    assert user.reset_token is None


def test_reset_password_throttled_returns_429_with_retry_after(monkeypatch):
    user = SimpleNamespace(id=404, reset_token="unused", reset_token_used=False, password_hash="old-hash")
    db = _FakeDB(user=user)

    def _limit_fail(key, limit, window):
        raise ErrorHandler.rate_limited("Too many reset attempts")

    monkeypatch.setattr(auth, "rate_limit_key", _limit_fail)

    payload = ResetPasswordRequest(token="token-blocked", new_password="StrongPass1")
    request = _build_request(client_ip="8.8.8.8", x_forwarded_for="6.6.6.6, 1.1.1.1")

    try:
        asyncio.run(auth.reset_password(payload, request, db))
        assert False, "Expected HTTPException 429"
    except HTTPException as exc:
        assert exc.status_code == 429
        assert exc.headers is not None
        assert exc.headers.get("Retry-After") == "3600"

    assert db.execute_called is False
    assert db.commit_called is False
