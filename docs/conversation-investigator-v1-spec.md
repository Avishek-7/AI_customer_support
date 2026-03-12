# Conversation Investigator V1 Spec

Version: 1.0
Status: Phase 1 Complete
Date: 2026-03-12
Owner: AI Customer Support Team

## 1. Goal

Deliver an internal support copilot workflow that helps admins investigate weak, low-confidence, or hallucination-prone answers.

Primary outcome:

- Faster and safer diagnosis of conversation failures using existing retrieval and critique signals.

## 2. Scope

In scope for V1:

- Admin-only access.
- Read-only investigation of existing conversation content.
- Optional improved draft generation as a non-persistent suggestion.
- Structured output containing diagnosis, evidence, quality summary, and recommended next actions.
- Audit metadata persistence for each investigation run.

Out of scope for V1:

- Customer-facing agent workflows.
- Autonomous write actions to user conversations.
- Broad multi-agent orchestration.
- Microservices decomposition.

## 3. Allowed Tooling and Data Sources

Allowlisted backend and AI paths:

- Backend conversation and admin data from admin endpoints and database models.
- AI retrieval preview via debug search endpoint.
- AI critique endpoint for quality and hallucination signals.
- AI regenerate endpoint for optional draft generation.

Disallowed actions:

- Mutating chat history or conversation content during investigation.
- Calling non-allowlisted external tools.

## 4. Request and Response Contracts

### 4.1 Run Investigation Request

Endpoint:

- POST /admin/investigations/run

Body schema:

```json
{
  "conversation_id": 123,
  "instruction_intent": "investigate_root_cause",
  "constraints": "optional string, max 300 chars",
  "k": 5
}
```

Field rules:

- conversation_id: required positive integer.
- instruction_intent: required enum.
- constraints: optional, used only for draft generation intent.
- k: optional integer, 1-20 recommended.

Allowed instruction_intent values:

- investigate_root_cause
- explain_low_confidence
- draft_improved_answer
- recommend_next_action

### 4.2 Run Investigation Response

```json
{
  "investigation_id": 1,
  "conversation_id": 123,
  "instruction_intent": "investigate_root_cause",
  "diagnosis": "string",
  "supporting_evidence": {
    "retrieved_chunks": [],
    "total_chunks_retrieved": 5,
    "document_ids": [10, 22]
  },
  "quality_summary": {
    "confidence_score": 0.72,
    "hallucination_score": 0.18,
    "alignment_score": 0.81
  },
  "recommended_next_actions": ["string"],
  "improved_draft_answer": "optional string",
  "status": "completed",
  "created_at": "2026-03-12T10:15:00"
}
```

Status values:

- completed
- partial

Partial means one or more upstream AI calls failed, but a structured response is still returned.

### 4.3 Audit Retrieval Contracts

Endpoints:

- GET /admin/investigations/{investigation_id}
- GET /admin/investigations/conversation/{conversation_id}

Purpose:

- Read back audit metadata and summaries for traceability and review.

## 5. Safety and Guardrails

Access control:

- Every investigation endpoint requires admin role.

Read-only guarantee:

- Investigation flow does not persist or mutate conversation messages.
- Optional regenerated answer is returned only as draft output.

Input constraints:

- instruction_intent is enum-constrained.
- constraints is trimmed and length-capped for regenerate requests.
- k is bounded to avoid unbounded retrieval depth.

Operational controls:

- Upstream AI calls have explicit timeouts.
- Investigation runs are audit-logged with status and latency.

## 6. Success Metrics

Phase 1 completion criteria:

- Contract is documented and versioned.
- Scope boundaries are explicit and agreed.
- Allowlisted tool usage is explicit.
- Safety rules are explicit.
- Measurable success criteria are defined.

V1 operational metrics:

- Investigation success rate.
- Partial response rate.
- P95 investigation latency.
- Percentage of low-confidence cases with actionable diagnosis.
- Admin adoption: number of weekly investigation runs.

## 7. Phase 1 Exit Checklist

- V1 goal documented.
- Allowlisted tools documented.
- Input and output schemas documented.
- Safety rules documented.
- Success metrics documented.

Result: Phase 1 is complete.
