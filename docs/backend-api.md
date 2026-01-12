# Backend API Contract

> **Version**: 1.0.0  
> **Last Updated**: January 12, 2026  
> **Base URL**: `http://localhost:8000`

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

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `email` | string (email) | ✅ | Valid email address |
| `password` | string | ✅ | User password |
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

**Side Effects:**
- Generates reset token (not actually sent via email in current implementation)

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
| `document_ids` | integer[] | ❌ | `null` (searches all) | Specific documents to search |

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

**Response (200):**
```json
{
  "conversations": [
    {
      "id": 1,
      "user_id": 123,
      "title": "Password Help",
      "created_at": "2026-01-12T10:30:00"
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
| `file` | file (PDF) | ✅ | PDF file to upload |

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
- Enqueues background indexing task (Celery)
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
  "query": "password reset"
}
```

**Response (200):**
```json
{
  "documents": [
    {
      "id": 1,
      "title": "Security Guide",
      "content": "...",
      "owner_id": 123,
      "index_status": "completed",
      "chunk_count": 10
    }
  ]
}
```

---

### `POST /documents/update-status` (Internal)

Update document indexing status (called by AI engine).

| Property | Value |
|----------|-------|
| Auth Required | ❌ No (internal use) |

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

**Response (200):**
```json
{
  "total": 450,
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

## Vector Endpoints

### `POST /vectors/sync` (Internal)

Sync vector metadata from FAISS to PostgreSQL.

| Property | Value |
|----------|-------|
| Auth Required | ❌ No (internal use) |

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
| Auth Required | ❌ No (internal use) |

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
| Auth Required | ❌ No |

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
| Auth Required | ❌ No |

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
| `POST /chat/chat` | 100 | 1 minute (per user) |
| `POST /documents/upload` | 20 | 1 hour (per user) |

When rate limited, you'll receive:

```json
{
  "detail": "Rate limit exceeded. Try again in X seconds."
}
```

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
