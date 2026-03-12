# Backend API Contract

> **Version**: 1.0.0  
> **Last Updated**: January 12, 2026  
> **Base URL**: `http://localhost:8000`

> ⚠️ Security: `http://localhost:8000` is for local development only. Production deployments must use HTTPS.

This document defines the complete API contract for the AI Customer Support backend. Use this as the source of truth for frontend development and API integration.

---

## Table of Contents

1. [Authentication](#authentication)
2. [Auth Endpoints](#auth-endpoints)
3. [Chat Endpoints](#chat-endpoints)
4. [Conversation Endpoints](#conversation-endpoints)
5. [Document Endpoints](#document-endpoints)
6. [User Endpoints](#user-endpoints)
7. [Admin Endpoints](#admin-endpoints)
8. [Vector Endpoints](#vector-endpoints)
9. [Error Responses](#error-responses)
10. [Rate Limiting](#rate-limiting)

---

## Authentication

All authenticated endpoints require a JWT token in the `Authorization` header:

```
Authorization: Bearer <token>
```

Tokens are obtained via `/auth/register` or `/auth/login`.

| Token Type | Expiry | Notes |
|------------|--------|-------|
| Access Token | 24 hours | Used for API requests |

---

## Auth Endpoints

### `POST /auth/register`

Create a new user account.

| Property | Value |
|----------|-------|
| Auth Required | ❌ No |
| Rate Limit | 5 requests/hour per email |

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123",
  "full_name": "John Doe"
}
```

| Field | Type | Required | Validation / Description |
|-------|------|----------|--------------------------|
| `email` | string (email) | ✅ | Valid email address |
| `password` | string | ✅ | Min 8 chars, at least 1 uppercase letter, and at least 1 number |
| `full_name` | string | ❌ | User's display name |

**Response (200):**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Side Effects:**
- Creates new user in database
- Generates JWT access token

---

### `POST /auth/login`

Authenticate an existing user.

| Property | Value |
|----------|-------|
| Auth Required | ❌ No |
| Rate Limit | 10 requests/5 minutes per email |

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `email` | string (email) | ✅ | Registered email |
| `password` | string | ✅ | User password |

**Response (200):**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Error Responses:**
- `401`: Invalid credentials

---

### `POST /auth/forgot-password`

Request a password reset.

| Property | Value |
|----------|-------|
| Auth Required | ❌ No |

**Request Body:**
```json
{
  "email": "user@example.com"
}
```

**Response (200):**
```json
{
  "message": "Password reset instructions sent to your email."
}
```

> ⚠️ **NOT IMPLEMENTED WARNING**: Email delivery for forgot-password must be treated as non-production until verified end-to-end.

**TODO**
- Track implementation/verification status in an issue or PR before relying on email delivery in production: https://github.com/Avishek-7/AI_customer_support/issues/new
- Expected behavior: generate token, persist token state, and send reset email through configured SMTP provider.

**Side Effects:**
- NOT IMPLEMENTED: reset token is generated but emails are not sent

**Error Responses:**
- `404`: User not found

---

### `POST /auth/reset-password`

Reset password using token.

| Property | Value |
|----------|-------|
| Auth Required | ❌ No |

**Request Body:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "new_password": "NewSecurePass123"
}
```

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `token` | string | ✅ | Valid reset token |
| `new_password` | string | ✅ | Min 8 chars, 1 uppercase, 1 number |

**Response (200):**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Side Effects:**
- Updates user password hash
- Returns new access token

---

### `GET /auth/reset-password/{token}`

Verify if a reset token is valid.

| Property | Value |
|----------|-------|
| Auth Required | ❌ No |

**Response (200):**
```json
{
  "message": "Token is valid",
  "user_id": "123"
}
```

**Error Responses:**
- `400`: Invalid or expired token

---

## Chat Endpoints

### `POST /chat/chat`

Send a message and receive a complete response (non-streaming).

| Property | Value |
|----------|-------|
| Auth Required | ✅ Yes |
| Rate Limit | 100 requests/minute per user |

**Request Body:**
```json
{
  "message": "How do I reset my account password?",
  "conversation_id": 1,
  "system_prompt": "You are an AI customer support assistant.",
  "document_ids": [1, 2, 3]
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `message` | string | ✅ | - | User's question |
| `conversation_id` | integer | ✅ | - | ID of existing conversation |
| `system_prompt` | string | ❌ | "You are an AI customer support assistant." | Custom system prompt |
| `document_ids` | integer[] \| null | ❌ | `null` (searches up to 20 most-recent indexed docs) | Specific documents to search |

**Context & Token Limits:**
- When `document_ids` is `null`, backend bounds retrieval to a capped subset (up to 20 docs) to avoid unbounded vector lookups.
- Large prompts (`system_prompt` + `message`) and broad document scope increase token use and latency; prefer explicit `document_ids` selection for users with many documents.
- For accounts with >20 documents, use client-side document selection before sending chat requests.

**Response (200):**
```json
{
  "answer": "To reset your password, go to Settings > Security > Reset Password...",
  "sources": [
    {
      "document_id": 1,
      "title": "User Guide",
      "chunk_id": 5,
      "score": 0.89,
      "text": "..."
    }
  ]
}
```

**Side Effects:**
- Saves message to chat history
- Updates conversation title (on first message)
- Tracks API usage (tokens, latency)

**Error Responses:**
- `404`: Conversation not found
- `500`: AI engine unavailable

---

### `POST /chat/stream`

Send a message and receive streaming response (SSE).

| Property | Value |
|----------|-------|
| Auth Required | ✅ Yes |
| Content-Type | `text/event-stream` |

**Request Body:** Same as `/chat/chat`

**Response (SSE Stream):**
```
data: {"type": "token", "content": "To"}

data: {"type": "token", "content": " reset"}

data: {"type": "token", "content": " your"}

data: {"type": "sources", "sources": [...]}

data: {"type": "done"}
```

| Event Type | Description |
|------------|-------------|
| `token` | Individual response token |
| `sources` | Retrieved source documents |
| `done` | Stream complete |

**Side Effects:**
- Same as `/chat/chat` (via background task)

---

### `GET /chat/history`

Get all chat history for current user (legacy endpoint).

| Property | Value |
|----------|-------|
| Auth Required | ✅ Yes |
| Deprecated | ⚠️ Use `/chat/conversations/{id}/messages` instead |

**Response (200):**
```json
{
  "history": [
    {
      "id": 1,
      "message": "How do I...",
      "response": "You can...",
      "timestamp": "2026-01-12T10:30:00"
    }
  ]
}
```

---

## Conversation Endpoints

### `POST /chat/conversations`

Create a new conversation.

| Property | Value |
|----------|-------|
| Auth Required | ✅ Yes |

**Request Body:**
```json
{
  "title": "Password Help"
}
```

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `title` | string | ❌ | "New Conversation" |

**Response (200):**
```json
{
  "id": 1,
  "user_id": 123,
  "title": "Password Help",
  "created_at": "2026-01-12T10:30:00"
}
```

**Side Effects:**
- Creates new conversation record

---

### `GET /chat/conversations`

Get all conversations for current user.

| Property | Value |
|----------|-------|
| Auth Required | ✅ Yes |

**Query Parameters:**
| Param | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `limit` | integer | ❌ | `50` | Number of conversations to return (`1-100`) |
| `offset` | integer | ❌ | `0` | Number of conversations to skip for pagination |

**Response (200):**
```json
{
  "total": 120,
  "limit": 50,
  "offset": 0,
  "conversations": [
    {
      "id": 1,
      "user_id": 123,
      "title": "Password Help",
      "created_at": "2026-01-12T10:30:00",
      "updated_at": "2026-01-12T10:32:00",
      "message_count": 4,
      "last_message_preview": "To reset your password..."
    }
  ]
}
```

---

### `GET /chat/conversations/{conversation_id}`

Get a specific conversation.

| Property | Value |
|----------|-------|
| Auth Required | ✅ Yes |

**Path Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `conversation_id` | integer | Conversation ID |

**Response (200):**
```json
{
  "id": 1,
  "user_id": 123,
  "title": "Password Help",
  "created_at": "2026-01-12T10:30:00"
}
```

**Error Responses:**
- `404`: Conversation not found

---

### `PATCH /chat/conversations/{conversation_id}`

Update a conversation (rename).

| Property | Value |
|----------|-------|
| Auth Required | ✅ Yes |

**Request Body:**
```json
{
  "title": "Account Recovery Help"
}
```

| Field | Type | Required |
|-------|------|----------|
| `title` | string | ❌ |

**Response (200):**
```json
{
  "id": 1,
  "user_id": 123,
  "title": "Account Recovery Help",
  "created_at": "2026-01-12T10:30:00"
}
```

**Side Effects:**
- Updates conversation title

---

### `DELETE /chat/conversations/{conversation_id}`

Delete a conversation and all its messages.

| Property | Value |
|----------|-------|
| Auth Required | ✅ Yes |

**Response (200):**
```json
{
  "message": "Conversation deleted successfully"
}
```

**Side Effects:**
- Deletes conversation
- Cascades to delete all chat messages

---

### `GET /chat/conversations/{conversation_id}/messages`

Get all messages in a conversation.

| Property | Value |
|----------|-------|
| Auth Required | ✅ Yes |

**Response (200):**
```json
{
  "history": [
    {
      "id": 1,
      "message": "How do I reset?",
      "response": "You can reset by...",
      "timestamp": "2026-01-12T10:30:00"
    }
  ]
}
```

---

## Document Endpoints

### `POST /documents/upload`

Upload and index a PDF document.

| Property | Value |
|----------|-------|
| Auth Required | ✅ Yes |
| Content-Type | `multipart/form-data` |
| Rate Limit | 20 uploads/hour per user |

**Request (Form Data):**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | ✅ | Document title |
| `file` | file (PDF) | ✅ | PDF file to upload (max 10MB) |

**Response (200):**
```json
{
  "id": 1,
  "title": "User Manual",
  "content": "Extracted text content...",
  "owner_id": 123,
  "index_status": "pending",
  "chunk_count": 0
}
```

**Side Effects:**
- Extracts text from PDF
- Creates document record
- Enqueues background indexing task
- Tracks API usage

**Error Responses:**
- `400`: Only PDF files allowed

---

### `GET /documents/`

Get all documents for current user.

| Property | Value |
|----------|-------|
| Auth Required | ✅ Yes |

**Response (200):**
```json
{
  "documents": [
    {
      "id": 1,
      "title": "User Manual",
      "content": "...",
      "owner_id": 123,
      "index_status": "completed",
      "chunk_count": 15
    }
  ]
}
```

---

### `GET /documents/{doc_id}`

Get a specific document.

| Property | Value |
|----------|-------|
| Auth Required | ✅ Yes |

**Response (200):**
```json
{
  "id": 1,
  "title": "User Manual",
  "content": "Full document text...",
  "owner_id": 123,
  "index_status": "completed",
  "chunk_count": 15
}
```

**Error Responses:**
- `404`: Document not found or access denied

---

### `PUT /documents/{doc_id}`

Update a document's title or content.

| Property | Value |
|----------|-------|
| Auth Required | ✅ Yes |

**Request Body:**
```json
{
  "title": "Updated Title",
  "content": "Updated content..."
}
```

| Field | Type | Required |
|-------|------|----------|
| `title` | string | ❌ |
| `content` | string | ❌ |

**Response (200):** Same as GET

**Side Effects:**
- Updates document record
- Re-indexes document in AI engine (background task)

---

### `DELETE /documents/{doc_id}`

Delete a document.

| Property | Value |
|----------|-------|
| Auth Required | ✅ Yes |

**Response (200):**
```json
{
  "detail": "Document deleted successfully"
}
```

**Side Effects:**
- Deletes from FAISS index (AI engine)
- Deletes from database

---

### `GET /documents/status/{doc_id}`

Check document indexing status.

| Property | Value |
|----------|-------|
| Auth Required | ✅ Yes |

**Response (200):**
```json
{
  "document_id": 1,
  "status": "completed",
  "chunk_count": 15
}
```

| Status | Description |
|--------|-------------|
| `pending` | Awaiting indexing |
| `processing` | Currently being indexed |
| `completed` | Ready for search |
| `failed` | Indexing failed |

---

### `POST /documents/{doc_id}/reindex`

Force re-index a document.

| Property | Value |
|----------|-------|
| Auth Required | ✅ Yes |

**Response (200):**
```json
{
  "id": 1,
  "title": "User Manual",
  "content": "...",
  "owner_id": 123,
  "index_status": "completed",
  "chunk_count": 15
}
```

**Side Effects:**
- Deletes old vectors from FAISS
- Re-chunks and re-embeds document
- Updates chunk count

---

### `POST /documents/search`

Search documents by content.

| Property | Value |
|----------|-------|
| Auth Required | ✅ Yes |

**Request Body:**
```json
{
  "query": "password reset",
  "limit": 20,
  "offset": 0
}
```

| Field | Type | Required | Default | Constraints | Description |
|-------|------|----------|---------|-------------|-------------|
| `query` | string | ✅ | - | non-empty | Search text |
| `limit` | integer | ❌ | `20` | `1-100` | Max documents returned |
| `offset` | integer | ❌ | `0` | `>=0` | Pagination offset |

**Example request:**
```json
{
  "query": "password reset",
  "limit": 20,
  "offset": 20
}
```

**Response (200):**
```json
{
  "total_count": 57,
  "next_offset": 20,
  "documents": [
    {
      "id": 1,
      "title": "Security Guide",
      "score": 0.91,
      "content": "...",
      "owner_id": 123,
      "index_status": "completed",
      "chunk_count": 10
    }
  ]
}
```

**Ranking Note:**
- Results are ordered by relevance score (`score`), based on backend search relevance (vector similarity and/or text relevance depending on active index).

---

### `POST /documents/update-status` (Internal)

Update document indexing status (called by AI engine).

| Property | Value |
|----------|-------|
| Auth Required | ✅ Yes (service-to-service, internal API key only) |

**Security:**
- Required header: `X-Internal-API-Key: <INTERNAL_API_KEY>`
- JWT bearer token is **not** required for this endpoint.
- Obtain the key from backend configuration (`INTERNAL_API_KEY`) and provision it as a secret in the AI engine deployment.

**Required headers example:**
```http
POST /documents/update-status
X-Internal-API-Key: <INTERNAL_API_KEY>
Content-Type: application/json
```

**Request Body:**
```json
{
  "document_id": 1,
  "status": "completed",
  "chunk_count": 15
}
```

---

## User Endpoints

### `GET /users/me`

Get current user's profile.

| Property | Value |
|----------|-------|
| Auth Required | ✅ Yes |

**Response (200):**
```json
{
  "id": 123,
  "name": "John Doe",
  "email": "john@example.com",
  "role": "user"
}
```

---

### `GET /users/`

List all users (admin only).

| Property | Value |
|----------|-------|
| Auth Required | ✅ Yes |
| Role Required | `admin` |

**Privacy & Compliance (applies to all Users endpoints):**
- Access to user PII must be audit-logged with `actor_id`, `endpoint`, `target_user_id`, `timestamp`, and `action_reason`.
- Admin access requires role-based justification consistent with organizational policy and legal basis.
- User and audit-log retention/deletion schedules must follow organization policy (consult your data-retention standard).
- Sensitive operations (`GET /users/`, `DELETE /users/{user_id}`) should use stricter approval/workflow controls.

**Response (200):**
```json
{
  "users": [
    {
      "id": 1,
      "name": "John Doe",
      "email": "john@example.com",
      "role": "user"
    }
  ]
}
```

---

### `GET /users/{user_id}`

Get user by ID (self or admin only).

| Property | Value |
|----------|-------|
| Auth Required | ✅ Yes |
| Role Required | Self or `admin` |

**Response (200):**
```json
{
  "id": 123,
  "name": "John Doe",
  "email": "john@example.com",
  "role": "user"
}
```

---

### `POST /users/`

Create new user (admin only).

| Property | Value |
|----------|-------|
| Auth Required | ✅ Yes |
| Role Required | `admin` |

**Request Body:**
```json
{
  "email": "newuser@example.com",
  "password": "SecurePass123",
  "name": "Jane Doe",
  "role": "user"
}
```

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `email` | string (email) | ✅ | - |
| `password` | string | ✅ | - |
| `name` | string | ❌ | `null` |
| `role` | string | ❌ | "user" |

**Response (201):**
```json
{
  "id": 124,
  "name": "Jane Doe",
  "email": "newuser@example.com",
  "role": "user"
}
```

---

### `PUT /users/{user_id}`

Update user (self or admin).

| Property | Value |
|----------|-------|
| Auth Required | ✅ Yes |
| Role Required | Self or `admin` |

**Request Body:**
```json
{
  "name": "Updated Name",
  "email": "newemail@example.com",
  "password": "NewPassword123",
  "role": "admin"
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `name` | string | ❌ | |
| `email` | string | ❌ | Must be unique |
| `password` | string | ❌ | |
| `role` | string | ❌ | Admin only |

**Response (200):** Updated user object

---

### `DELETE /users/{user_id}`

Delete user (admin only).

| Property | Value |
|----------|-------|
| Auth Required | ✅ Yes |
| Role Required | `admin` |

**Response (204):** No content

**Side Effects:**
- Permanently deletes user and associated data

---

## Admin Endpoints

All admin endpoints require `role: "admin"`.

### `GET /admin/users`

List all users with statistics.

| Property | Value |
|----------|-------|
| Auth Required | ✅ Yes |
| Role Required | `admin` |

**Response (200):**
```json
[
  {
    "id": 1,
    "name": "John Doe",
    "email": "john@example.com",
    "role": "user",
    "document_count": 5,
    "chat_count": 42,
    "total_api_calls": 156
  }
]
```

---

### `GET /admin/usage-stats`

Get API usage statistics by endpoint.

| Property | Value |
|----------|-------|
| Auth Required | ✅ Yes |
| Role Required | `admin` |

**Response (200):**
```json
[
  {
    "endpoint": "/chat",
    "total_calls": 1500,
    "total_tokens": 45000,
    "avg_latency": 2.35
  }
]
```

---

### `GET /admin/system-stats`

Get system-wide statistics.

| Property | Value |
|----------|-------|
| Auth Required | ✅ Yes |
| Role Required | `admin` |

**Response (200):**
```json
{
  "total_users": 150,
  "total_documents": 450,
  "total_chats": 3200,
  "total_api_calls": 15000,
  "users_last_24h": 12,
  "documents_last_24h": 8
}
```

---

### `GET /admin/users/{user_id}/usage`

Get specific user's API usage.

| Property | Value |
|----------|-------|
| Auth Required | ✅ Yes |
| Role Required | `admin` |

**Response (200):**
```json
{
  "user_id": 123,
  "total_calls": 156,
  "recent_usage": [
    {
      "endpoint": "/chat",
      "tokens": 150,
      "latency": 2.1,
      "created_at": "2026-01-12T10:30:00"
    }
  ]
}
```

---

### `GET /admin/documents`

List all documents across all users.

| Property | Value |
|----------|-------|
| Auth Required | ✅ Yes |
| Role Required | `admin` |

**Query Parameters:**
| Param | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `limit` | integer | ❌ | `50` | Number of records to return (`1-200`) |
| `offset` | integer | ❌ | `0` | Number of records to skip |

**Example request:**
```http
GET /admin/documents?limit=25&offset=25
Authorization: Bearer <admin_token>
```

**Response (200):**
```json
{
  "limit": 25,
  "offset": 25,
  "total": 450,
  "returned_count": 25,
  "documents": [
    {
      "id": 1,
      "title": "User Manual",
      "owner_id": 123,
      "index_status": "completed",
      "chunk_count": 15
    }
  ]
}
```

---

### `GET /admin/chats`

List recent chats across all users.

| Property | Value |
|----------|-------|
| Auth Required | ✅ Yes |
| Role Required | `admin` |

**Privacy, Legal Basis, and Audit Requirements:**
- Admin chat access must be justified by approved operational/legal basis (e.g., support quality, abuse investigation, legal hold).
- Every chat-content access should be audit-logged (`actor_id`, `target_user_id`, `message_id`, `timestamp`, `action_reason`).
- Prefer data minimization: list views should default to metadata (`message_id`, `user_id`, `timestamp`) and require explicit action to view full content.
- Define retention for chat content and related audit records per policy and jurisdictional requirements.
- Recommended RBAC hardening: separate `chat_viewer` permission and/or justification workflow for content access.

**Response (200):**
```json
{
  "total": 100,
  "recent_chats": [
    {
      "id": 1,
      "user_id": 123,
      "message": "How do I...",
      "timestamp": "2026-01-12T10:30:00"
    }
  ]
}
```

---

### `GET /admin/stats`

Quick stats overview.

| Property | Value |
|----------|-------|
| Auth Required | ✅ Yes |
| Role Required | `admin` |

**Response (200):**
```json
{
  "users": 150,
  "documents": 450,
  "chats": 3200,
  "usage_today": 234
}
```

---

### `GET /admin/debug/conversations/{conversation_id}`

Debug a conversation with RAG pipeline details.

| Property | Value |
|----------|-------|
| Auth Required | ✅ Yes |
| Role Required | `admin` |

**Response (200):**
```json
{
  "conversation_id": 1,
  "user_id": 123,
  "title": "Password Help",
  "message_count": 4,
  "messages": [
    {
      "id": 1,
      "user_id": 123,
      "role": "user",
      "content": "How do I reset?",
      "created_at": "2026-01-12T10:30:00"
    }
  ],
  "debug_info": {
    "last_query": "How do I reset?",
    "retrieved_chunks": [...],
    "total_chunks_retrieved": 5,
    "document_ids": [1, 2],
    "prompt_length_chars": 1500,
    "prompt_length_words": 280,
    "confidence_score": 0.85,
    "hallucination_score": 0.12,
    "alignment_score": 0.88,
    "critique_details": {...}
  }
}
```

---

### `POST /admin/investigations/run`

Run an admin-only read-only copilot investigation for one conversation.

| Property | Value |
|----------|-------|
| Auth Required | ✅ Yes |
| Role Required | `admin` |

**Request Body:**
```json
{
  "conversation_id": 123,
  "instruction_intent": "investigate_root_cause",
  "constraints": "optional constraints for draft generation",
  "k": 5
}
```

| Field | Type | Required | Validation / Description |
|-------|------|----------|--------------------------|
| `conversation_id` | integer | ✅ | Existing conversation ID |
| `instruction_intent` | string | ✅ | One of `investigate_root_cause`, `explain_low_confidence`, `draft_improved_answer`, `recommend_next_action` |
| `constraints` | string | ❌ | Optional regenerate constraints, trimmed and capped |
| `k` | integer | ❌ | Retrieval depth (recommended 1-20) |

**Response (200):**
```json
{
  "investigation_id": 1,
  "conversation_id": 123,
  "instruction_intent": "investigate_root_cause",
  "diagnosis": "string",
  "supporting_evidence": {
    "retrieved_chunks": [],
    "total_chunks_retrieved": 5,
    "document_ids": [1, 2]
  },
  "quality_summary": {
    "confidence_score": 0.72,
    "hallucination_score": 0.12,
    "alignment_score": 0.88
  },
  "recommended_next_actions": [
    "Review top retrieved chunks for relevance and freshness."
  ],
  "improved_draft_answer": "optional string",
  "status": "completed",
  "created_at": "2026-03-12T10:30:00"
}
```

Notes:
- This endpoint is read-only with respect to conversation and chat message content.
- The optional improved draft is returned but not written into chat history.
- `status` may be `partial` when upstream AI calls fail but fallback output is returned.

---

### `GET /admin/investigations/{investigation_id}`

Retrieve one investigation audit record.

| Property | Value |
|----------|-------|
| Auth Required | ✅ Yes |
| Role Required | `admin` |

**Response (200):**
```json
{
  "id": 1,
  "investigator_user_id": 7,
  "conversation_id": 123,
  "instruction_intent": "investigate_root_cause",
  "tools_called": ["debug/search-preview", "critique"],
  "status": "completed",
  "latency_ms": 842,
  "confidence_score": 0.72,
  "hallucination_score": 0.12,
  "alignment_score": 0.88,
  "diagnosis_summary": "string",
  "created_at": "2026-03-12T10:30:00"
}
```

---

### `GET /admin/investigations/conversation/{conversation_id}`

List recent investigations for a conversation.

| Property | Value |
|----------|-------|
| Auth Required | ✅ Yes |
| Role Required | `admin` |

**Query Parameters:**
| Param | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `limit` | integer | ❌ | `20` | Maximum records (`1-100`) |

**Response (200):**
```json
{
  "conversation_id": 123,
  "returned_count": 2,
  "items": [
    {
      "id": 1,
      "instruction_intent": "investigate_root_cause",
      "status": "completed",
      "latency_ms": 842,
      "confidence_score": 0.72,
      "hallucination_score": 0.12,
      "alignment_score": 0.88,
      "diagnosis_summary": "string",
      "created_at": "2026-03-12T10:30:00"
    }
  ]
}
```

---

## Vector Endpoints

### `POST /vectors/sync` (Internal)

Sync vector metadata from FAISS to PostgreSQL.

| Property | Value |
|----------|-------|
| Auth Required | ✅ Yes (service-to-service) |

**Security:**
- Required header: `X-Internal-API-Key: <internal_service_key>`
- Restricted to internal network callers only (private IP/VPC)

**Request Body:**
```json
{
  "metadata": [
    {
      "document_id": 1,
      "chunk_id": 0,
      "text": "Chunk text content..."
    }
  ]
}
```

**Response (200):**
```json
{
  "status": "success",
  "synced": 45,
  "total": 50
}
```

---

### `DELETE /vectors/document/{document_id}` (Internal)

Delete vector metadata for a document.

| Property | Value |
|----------|-------|
| Auth Required | ✅ Yes (service-to-service) |

**Security:**
- Required header: `X-Internal-API-Key: <internal_service_key>`
- Restricted to internal network callers only (private IP/VPC)

**Response (200):**
```json
{
  "status": "success",
  "document_id": 1,
  "deleted": 15
}
```

---

### `GET /vectors/document/{document_id}`

Get vector metadata for a document (debug).

| Property | Value |
|----------|-------|
| Auth Required | ✅ Yes (service-to-service) |

**Security:**
- Required header: `X-Internal-API-Key: <internal_service_key>`
- Returns `401` for missing/invalid key

**Response (200):**
```json
{
  "document_id": 1,
  "chunk_count": 15,
  "chunks": [
    {
      "id": 1,
      "chunk_index": 0,
      "text_preview": "First 100 chars...",
      "text_length": 512,
      "faiss_index": 0,
      "created_at": "2026-01-12T10:30:00"
    }
  ]
}
```

---

### `GET /vectors/stats`

Get vector storage statistics.

| Property | Value |
|----------|-------|
| Auth Required | ✅ Yes (service-to-service) |

**Security:**
- Required header: `X-Internal-API-Key: <internal_service_key>`
- Returns `401` for missing/invalid key

**Response (200):**
```json
{
  "total_vectors": 1500,
  "total_documents": 45,
  "per_document": [
    {
      "document_id": 1,
      "vector_count": 15,
      "total_chars": 7500
    }
  ]
}
```

---

## Error Responses

All errors follow this format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

### Common HTTP Status Codes

| Code | Meaning |
|------|---------|
| `400` | Bad Request - Invalid input |
| `401` | Unauthorized - Missing/invalid token |
| `403` | Forbidden - Insufficient permissions |
| `404` | Not Found - Resource doesn't exist |
| `422` | Validation Error - Schema validation failed |
| `429` | Too Many Requests - Rate limit exceeded |
| `500` | Internal Server Error |

### Validation Error (422) Format

```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

---

## Rate Limiting

| Endpoint | Limit | Window |
|----------|-------|--------|
| `POST /auth/register` | 5 | 1 hour (per email) |
| `POST /auth/login` | 10 | 5 minutes (per email) |
| `POST /auth/forgot-password` | 5 | 1 hour (per client IP) |
| `POST /auth/reset-password` | 10 | 1 hour (per client IP + token hash) |
| `POST /chat/chat` | 100 | 1 minute (per user) |
| `POST /documents/upload` | 20 | 1 hour (per user) |
| `POST /documents/search` | 120 | 1 minute (per user) |
| `POST /documents/{doc_id}/reindex` | 10 | 1 hour (per user) |
| `GET /users/`, `POST /users/`, `PUT /users/{id}`, `DELETE /users/{id}` | 60 | 1 minute (per admin user) |
| `GET /admin/*` | 100 | 1 minute (per admin user) |
| `POST /vectors/sync`, `DELETE /vectors/document/{id}`, `GET /vectors/*` | internal-service limits | service policy |
| Default / other endpoints | 100 | 1 minute (per principal) |

When rate limited, you'll receive:

**Response headers:**
- `X-RateLimit-Limit`: configured request limit
- `X-RateLimit-Remaining`: remaining requests in current window
- `X-RateLimit-Reset`: unix timestamp when window resets

```json
{
  "detail": "Rate limit exceeded. Try again in X seconds."
}
```

Example:
```http
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1767225600
Content-Type: application/json

{
  "detail": "Rate limit exceeded. Try again in X seconds."
}
```

**Internal Service Exemptions:**
- Internal service-to-service endpoints may use separate limits or exemptions based on trusted identity (`X-Internal-API-Key`) and internal network controls.
- Exemption requests must be reviewed by platform/security owners and documented with service name, rationale, and duration.

---

## Appendix: Type Definitions

### User Roles

| Role | Description |
|------|-------------|
| `user` | Standard user (default) |
| `admin` | Full admin access |

### Document Status

| Status | Description |
|--------|-------------|
| `pending` | Document uploaded, not yet indexed |
| `processing` | Currently being indexed |
| `completed` | Successfully indexed, ready for search |
| `failed` | Indexing failed |

### Chat Message Role

| Role | Description |
|------|-------------|
| `user` | Message from user |
| `assistant` | Response from AI |

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-01-12 | Initial API contract freeze |
