import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from api import admin


class _ScalarOneResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _ScalarsWrapper:
    def __init__(self, values):
        self._values = values

    def all(self):
        return self._values


class _ScalarsResult:
    def __init__(self, values):
        self._values = values

    def scalars(self):
        return _ScalarsWrapper(self._values)


class _FakeDB:
    def __init__(self, conversation, chats):
        self._conversation = conversation
        self._chats = chats
        self.execute_count = 0
        self.added_audits = []

    async def execute(self, _query):
        self.execute_count += 1
        if self.execute_count == 1:
            return _ScalarOneResult(self._conversation)
        return _ScalarsResult(self._chats)

    def add(self, audit):
        self.added_audits.append(audit)

    async def commit(self):
        return None

    async def refresh(self, audit):
        audit.id = 1
        if getattr(audit, "created_at", None) is None:
            audit.created_at = datetime.now(timezone.utc)


def _build_base_data():
    conversation = SimpleNamespace(id=77, user_id=9)
    chats = [
        SimpleNamespace(role="assistant", content="Older answer"),
        SimpleNamespace(role="user", content="How do I reset my password?"),
        SimpleNamespace(role="assistant", content="Go to reset page and use forgot password."),
    ]
    admin_user = SimpleNamespace(id=999, role="admin")
    body = admin.InvestigationRunRequest(
        conversation_id=77,
        instruction_intent="investigate_root_cause",
        constraints="Use grounded sources only",
        k=4,
    )
    return conversation, chats, admin_user, body


def test_admin_investigation_auth_blocked_for_non_admin():
    app = FastAPI()
    app.include_router(admin.router)

    async def _deny_admin():
        raise HTTPException(status_code=403, detail="Admin access required")

    async def _fake_db_dep():
        yield _FakeDB(conversation=None, chats=[])

    app.dependency_overrides[admin.require_admin] = _deny_admin
    app.dependency_overrides[admin.get_db] = _fake_db_dep

    client = TestClient(app)
    response = client.post(
        "/admin/investigations/run",
        json={"conversation_id": 1, "instruction_intent": "investigate_root_cause", "k": 5},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required"


def test_run_investigation_happy_path(monkeypatch):
    conversation, chats, admin_user, body = _build_base_data()
    fake_db = _FakeDB(conversation=conversation, chats=chats)

    async def _fake_ai_engine(**_kwargs):
        return (
            {
                "results_count": 2,
                "chunks": [
                    {"document_id": 101, "text_preview": "Password reset policy"},
                    {"document_id": 102, "text_preview": "Auth troubleshooting"},
                ],
            },
            {
                "critique": {
                    "llm_critique": {"overall_score": 7},
                    "hallucination_detection": {
                        "hallucination_score": 0.15,
                        "alignment_score": 0.88,
                    },
                }
            },
            None,
            "completed",
            ["debug/search-preview", "critique"],
            [],
        )

    monkeypatch.setattr(admin, "_call_ai_engine_for_investigation", _fake_ai_engine)

    response = asyncio.run(
        admin.run_investigation(body=body, db=fake_db, admin_user=admin_user)
    )

    assert response.status == "completed"
    assert response.investigation_correlation_id
    assert response.investigation_correlation_id.startswith("inv-")
    assert response.conversation_id == 77
    assert response.supporting_evidence.total_chunks_retrieved == 2
    assert sorted(response.supporting_evidence.document_ids) == [101, 102]
    assert response.quality_summary.confidence_score == 0.7
    assert response.quality_summary.hallucination_score == 0.15
    assert response.error_details == []
    assert len(fake_db.added_audits) == 1
    assert fake_db.added_audits[0].status == "completed"


def test_run_investigation_partial_failure_on_ai_engine_exception(monkeypatch):
    conversation, chats, admin_user, body = _build_base_data()
    fake_db = _FakeDB(conversation=conversation, chats=chats)

    async def _raise_ai_engine(**_kwargs):
        raise RuntimeError("ai engine unavailable")

    monkeypatch.setattr(admin, "_call_ai_engine_for_investigation", _raise_ai_engine)

    response = asyncio.run(
        admin.run_investigation(body=body, db=fake_db, admin_user=admin_user)
    )

    assert response.status == "partial"
    assert response.investigation_correlation_id
    assert response.investigation_correlation_id.startswith("inv-")
    assert response.error_details
    assert response.error_details[0]["context"] == "ai_engine"
    assert response.error_details[0]["investigation_correlation_id"] == response.investigation_correlation_id
    assert "ai engine unavailable" in response.error_details[0]["body"]
    assert response.supporting_evidence.total_chunks_retrieved == 0
    assert len(fake_db.added_audits) == 1
    assert fake_db.added_audits[0].status == "partial"


def test_investigation_request_validation_normalizes_constraints_and_limits_k():
    payload = admin.InvestigationRunRequest(
        conversation_id=123,
        instruction_intent="investigate_root_cause",
        constraints="   should be ignored for non-draft intents   ",
        k=5,
    )
    assert payload.constraints is None

    draft_payload = admin.InvestigationRunRequest(
        conversation_id=123,
        instruction_intent="draft_improved_answer",
        constraints="   Keep grounded citations   ",
        k=10,
    )
    assert draft_payload.constraints == "Keep grounded citations"

    try:
        admin.InvestigationRunRequest(
            conversation_id=123,
            instruction_intent="draft_improved_answer",
            constraints="x",
            k=0,
        )
        assert False, "Expected ValidationError for out-of-range k"
    except ValidationError:
        pass


def test_diagnosis_and_recommended_actions_reflect_risk_signals():
    quality = admin.InvestigationQualitySummary(
        confidence_score=0.3,
        hallucination_score=0.8,
        alignment_score=0.2,
    )

    diagnosis = admin._derive_diagnosis("investigate_root_cause", quality, chunks_retrieved=0)
    assert "risk signals" in diagnosis
    assert "no supporting chunks retrieved" in diagnosis
    assert "high hallucination risk" in diagnosis

    actions = admin._derive_recommended_actions("draft_improved_answer", quality, chunks_retrieved=0)
    assert "Escalate to human review due to high hallucination risk." in actions
    assert "Treat improved draft as advisory and require human approval before user-facing use." in actions
    assert "Use narrower document filters and regenerate with explicit constraints." in actions
