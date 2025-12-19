# AI Engine - Advanced Features

## 🎯 New Quality & Evaluation Features

### 1. 🚨 Hallucination Detection
**File:** `ai_engine/utils/hallucination.py`

Automatically detects potential hallucinations using source-answer alignment scoring:
- **Embedding similarity** - Compares answer semantics with source chunks
- **Keyword overlap** - Measures factual grounding in sources
- **Risk levels** - Low/Medium/High hallucination risk

**Integration:**
- Automatically included in all `/query` and `/stream` responses
- Returns `hallucination_score` (0-1, lower is better)
- Returns `alignment_score` (0-1, higher is better)
- Provides detailed metrics in `details` field

**Response format:**
```json
{
  "hallucination_detection": {
    "hallucination_score": 0.15,
    "alignment_score": 0.85,
    "details": {
      "max_source_similarity": 0.89,
      "avg_source_similarity": 0.82,
      "keyword_overlap": 0.75,
      "risk_level": "low"
    }
  }
}
```

---

### 2. 🧠 Self-Critique Endpoint
**Endpoint:** `POST /critique`

Have the LLM judge its own answers for quality and accuracy.

**Request:**
```json
{
  "question": "What is the refund policy?",
  "answer": "You can get a refund within 30 days...",
  "sources": [...]
}
```

**Response:**
```json
{
  "critique": {
    "llm_critique": {
      "accuracy_score": 9,
      "relevance_score": 8,
      "completeness_score": 7,
      "clarity_score": 9,
      "overall_score": 8,
      "strengths": ["Clear language", "Directly answers question"],
      "weaknesses": ["Could provide more examples"],
      "suggestions": ["Add specific refund scenarios"],
      "grounded_in_context": true,
      "summary": "Good answer, well-grounded in sources"
    },
    "hallucination_detection": {
      "hallucination_score": 0.12,
      "alignment_score": 0.88
    }
  }
}
```

---

### 3. 🔍 Context Inspection Endpoint
**Endpoint:** `POST /inspect-context`

See what chunks would be retrieved for a query without generating an answer.

**Request:**
```json
{
  "query": "How do I reset my password?",
  "document_ids": [1, 2],
  "k": 5
}
```

**Response:**
```json
{
  "query": "How do I reset my password?",
  "total_retrieved": 5,
  "chunks": [
    {
      "document_id": 1,
      "chunk_id": 3,
      "title": "User Guide",
      "text": "To reset your password, click...",
      "score": 0.89
    },
    ...
  ]
}
```

**Use cases:**
- Debug retrieval issues
- Understand context quality
- Verify document indexing
- Fine-tune search parameters

---

### 4. 🔄 Answer Regeneration Endpoint
**Endpoint:** `POST /regenerate`

Regenerate answers with specific user constraints.

**Request:**
```json
{
  "session_id": "user123",
  "query": "What is your return policy?",
  "constraints": "Make it shorter and use bullet points",
  "document_ids": [1],
  "k": 5,
  "previous_answer": "Our return policy allows..."
}
```

**Response:**
```json
{
  "answer": "Return policy:\n• 30-day window\n• Original packaging required...",
  "sources": [...],
  "regeneration_info": {
    "constraints_applied": "Make it shorter and use bullet points",
    "had_previous_answer": true,
    "sources_used": 5
  }
}
```

**Example constraints:**
- "Make it shorter"
- "Add more technical detail"
- "Use simpler language"
- "Format as bullet points"
- "Be more formal/casual"
- "Include code examples"
- "Focus on security aspects"

---

## 📊 Integration

All features are integrated into the existing pipeline:

1. **Hallucination detection** - Automatically runs on all queries
2. **Self-critique** - Available via dedicated endpoint
3. **Context inspection** - Debugging and verification tool
4. **Regeneration** - User-driven answer refinement

---

## 🧪 Testing

Test the new endpoints:

```bash
# Inspect context
curl -X POST http://localhost:9000/inspect-context \
  -H "Content-Type: application/json" \
  -d '{"query": "test query", "k": 3}'

# Critique an answer
curl -X POST http://localhost:9000/critique \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is X?",
    "answer": "X is...",
    "sources": [{"text": "..."}]
  }'

# Regenerate with constraints
curl -X POST http://localhost:9000/regenerate \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test",
    "query": "What is X?",
    "constraints": "Make it shorter",
    "k": 5
  }'
```

---

## 📝 Notes

- Hallucination scores use embeddings + keyword overlap
- Self-critique uses LLM introspection
- Context inspection is read-only (no answer generation)
- Regeneration preserves chat history and session context
