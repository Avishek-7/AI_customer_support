# 🚀 Hybrid Vector Storage - Quick Start Guide

## ⚡ Quick Setup (3 Steps)

### Step 1: Run Migration
```bash
cd backend
python -m migrations.add_vector_metadata
```
Expected output: `✅ Migration completed successfully`

### Step 2: Restart Services
```bash
# Terminal 1 - Backend
cd backend
uvicorn main:app --reload --port 8000

# Terminal 2 - AI Engine  
cd ai_engine
uvicorn app:app --reload --port 9000
```

### Step 3: Test It
```bash
./run_vector_test.sh
```
Expected: `✅ ALL TESTS PASSED`

Or manually from backend environment:
```bash
cd backend
source .venv/bin/activate
cd ..
python test_vector_integration.py
```

---

## 📊 Quick Verification

### Check if it's working:
```bash
# Upload a document first through your app, then:

# Check vector statistics
curl http://localhost:8000/vectors/stats

# View specific document's chunks
curl http://localhost:8000/vectors/document/1
```

### Expected Response:
```json
{
  "total_vectors": 15,
  "total_documents": 1,
  "per_document": [
    {
      "document_id": 1,
      "vector_count": 15,
      "total_chars": 12450
    }
  ]
}
```

---

## 🎯 What You Get

| Feature | Description | Benefit |
|---------|-------------|---------|
| **FAISS Storage** | Fast vector search | Millisecond query times |
| **PostgreSQL Storage** | Persistent metadata | Survives restarts, SQL queries |
| **Auto Sync** | Automatic synchronization | No manual work needed |
| **Analytics** | Query chunk distribution | Insights and debugging |

---

## 🔍 Key Endpoints

```bash
# Get storage stats
GET /vectors/stats

# Get document chunks
GET /vectors/document/{document_id}

# Sync from FAISS (internal)
POST /vectors/sync

# Delete metadata (internal)
DELETE /vectors/document/{document_id}
```

---

## 📝 Monitoring

Watch logs for sync confirmation:
```bash
# AI Engine logs
tail -f ai_engine/logs/app.log | grep "sync"

# Backend logs
tail -f backend/logs/app.log | grep "vector"
```

Look for:
- ✅ `Successfully synced X vector metadata entries to database`
- ✅ `Vector metadata synced successfully`

---

## 🐛 Troubleshooting

### Problem: Table doesn't exist
```bash
# Run migration
cd backend
python -m migrations.add_vector_metadata
```

### Problem: Metadata out of sync
```bash
# Check counts
curl http://localhost:8000/vectors/stats  # PostgreSQL
# vs FAISS metadata.json entry count
```

### Problem: Import errors
```bash
# Restart both services
pkill -f uvicorn
# Then start them again
```

---

## 📚 Full Documentation

- **Architecture**: See `HYBRID_VECTOR_STORAGE.md`
- **Complete Summary**: See `INTEGRATION_SUMMARY.md`

---

## ✅ Success Indicators

You'll know it's working when:

1. ✅ Migration runs without errors
2. ✅ Services start successfully  
3. ✅ Test script passes all checks
4. ✅ `/vectors/stats` returns data after document upload
5. ✅ Logs show "synced vector metadata" messages

---

## 💡 Pro Tips

1. **Check stats after each upload** - Verify sync is working
2. **Monitor logs** - Watch for sync success/failure messages  
3. **Use PostgreSQL for analytics** - Query chunk distribution, sizes, etc.
4. **FAISS stays fast** - Search performance unchanged
5. **Backup both** - FAISS files + PostgreSQL dumps

---

## 🎉 You're Done!

Your project now has **enterprise-grade hybrid vector storage**:
- ⚡ Fast FAISS similarity search
- 🗄️ Persistent PostgreSQL metadata
- 🔄 Automatic synchronization
- 📊 Rich analytics capabilities

Happy coding! 🚀
