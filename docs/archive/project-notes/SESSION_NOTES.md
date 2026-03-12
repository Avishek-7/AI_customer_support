# SESSION NOTES

Date: 2026-03-10
Project: AI Customer Support

## Current Goal
Turn the current RAG chatbot into an internal support copilot first, before expanding toward a broader AI agent.

## Agreed Direction
- Start with an internal-facing copilot, not a customer-facing autonomous agent
- First workflow should be a narrow, safe `Conversation Investigator`
- Keep V1 read-only and admin-only
- Do not begin with a full microservices rewrite
- Use existing backend/admin/debug capabilities and AI-engine critique/debug tools

## Why This Direction
- The repo already has strong debugging and admin primitives
- Existing AI service already supports retrieval inspection, critique, and regeneration
- This is the safest path to delivering real agent-like value quickly
- It is easier to evaluate and control than a general-purpose support agent

## V1 Copilot Definition
Primary use case:
- Investigate why a conversation got a weak, low-confidence, or hallucinated answer

Expected input:
- `conversation_id`
- optional admin instruction like:
  - investigate root cause
  - explain low confidence
  - draft improved answer
  - recommend next action

Expected output:
- diagnosis
- supporting evidence
- confidence / hallucination summary
- recommended next actions
- optional improved draft answer

## Recommended V1 Tool Set
Read-only tools first:
- conversation debug data from backend admin endpoints
- inspect retrieval context
- critique existing answer
- regenerate a better draft
- document status lookup
- user usage lookup

Likely source areas:
- `backend/api/admin.py`
- `backend/api/documents.py`
- `ai_engine/app.py`
- `ai_engine/rag/pipeline.py`
- `frontend/app/admin/debug/page.tsx`
- `frontend/lib/api.ts`

## Planned Phases
1. Finalize V1 spec
2. Define safe tool contracts
3. Add copilot orchestration layer
4. Add admin copilot UI
5. Add logging / guardrails / auditability
6. Evaluate on real failure cases
7. Only then expand scope or extract more services

## Architectural Position
Current architecture is best described as:
- modular monolith + AI microservice
- not full microservices yet

Current components:
- `frontend/` - Next.js UI
- `backend/` - main FastAPI app
- `ai_engine/` - separate RAG/LLM service
- PostgreSQL / Redis / FAISS as supporting infrastructure

## Microservices Decision
Agreed approach:
- do not start by splitting everything into microservices
- first stabilize the copilot use case
- later extract services only where boundaries are justified

Good future service candidates:
- auth/user service
- document service
- conversation/chat service
- admin/analytics service
- agent orchestration service
- indexing worker service

## Important Constraints
- V1 should be admin-only
- V1 should be read-only by default
- no broad unrestricted data access
- any future write action must be confirmation-gated
- model should use explicit allowlisted tools only
- add audit logs for copilot usage

## First Concrete Next Step
Draft the V1 spec with:
- goal
- allowed tools
- input/output schema
- safety rules
- success metrics

## Best First Deliverable
Build `Conversation Investigator` first.

## Resume Prompt
Continue from this state:
We are turning this project into an internal support copilot first.
Start with a read-only, admin-only `Conversation Investigator`.
Next task is to draft the V1 spec and implementation plan step by step.

## Implementation Progress (2026-03-12)

### Completed in first coding slice
- Added backend investigator orchestration endpoints in `backend/api/admin.py`:
  - `POST /admin/investigations/run`
  - `GET /admin/investigations/{investigation_id}`
  - `GET /admin/investigations/conversation/{conversation_id}`
- Implemented read-only investigation flow that reuses AI engine endpoints:
  - retrieval via `debug/search-preview`
  - quality critique via `/critique`
  - optional draft generation via `/regenerate`
- Added PostgreSQL-backed audit persistence model:
  - `backend/models/investigation_audit.py`
- Added migration script:
  - `backend/migrations/add_investigation_audit_table.py`
- Added frontend API bindings in `frontend/lib/api.ts` for running and listing investigations
- Added new admin page:
  - `frontend/app/admin/investigations/page.tsx`
- Added Investigations navigation card on admin dashboard:
  - `frontend/app/admin/page.tsx`

### Current behavior
- V1 remains admin-only (guarded by `require_admin`)
- Investigation endpoint is read-only against conversation/chat content
- Only audit metadata is persisted
- Regenerated answer is returned as optional draft output, not written back to chat history

### Next implementation steps
1. Run migration in target environment and verify table creation.
2. Add backend tests for auth, happy path, and partial AI-engine failure handling.
3. Add frontend history panel that calls `GET /admin/investigations/conversation/{conversation_id}`.
4. Improve diagnosis/action heuristics and add stricter constraint validation.
5. Add structured correlation id across backend logs for each investigation run.

## Phase 1 Completion (2026-03-12)

Phase 1 is complete.

Completed artifacts:
- V1 formal spec:
  - `docs/conversation-investigator-v1-spec.md`
- Backend API contract updates for investigator endpoints:
  - `docs/backend-api.md`

Phase 1 checklist status:
- Goal defined
- Allowed tools defined
- Input/output schema defined
- Safety rules defined
- Success metrics defined
