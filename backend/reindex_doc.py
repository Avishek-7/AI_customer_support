#!/usr/bin/env python3
"""Script to manually trigger indexing for a document"""
import asyncio
import httpx
import sys
import os
import json
from sqlalchemy import text
from core.database import AsyncSessionLocal
from core.config import settings

async def trigger_indexing(doc_id: int):
    # Get document details
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text('SELECT id, title, content FROM documents WHERE id = :id'),
            {'id': doc_id}
        )
        doc = result.fetchone()
        
        if not doc:
            print(f'Document {doc_id} not found')
            return False
            
        document_id, title, content = doc
        content = content or ""
        base_url = os.getenv("REINDEX_SERVICE_URL", "http://localhost:9000").rstrip("/")
        print(f'Found document: ID={document_id}, Title={title}')
        print(f'Content length: {len(content)} characters')
        print(f'Triggering indexing to AI engine...')
        
        # Call AI engine to index
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    f'{base_url}/index-document',
                    json={
                        'document_id': document_id,
                        'title': title,
                        'content': content
                    },
                    headers={"X-Internal-API-Key": settings.INTERNAL_API_KEY},
                )
                response.raise_for_status()
            except httpx.TimeoutException as e:
                print(f'✗ Indexing timeout for document {document_id} ({title}): {e}')
                return False
            except httpx.RequestError as e:
                print(f'✗ Request error for document {document_id} ({title}): {e}')
                return False
            except httpx.HTTPStatusError as e:
                print(f'✗ Indexing failed for document {document_id} ({title}): {e.response.status_code} {e.response.text}')
                return False

            try:
                result_data = response.json()
            except json.JSONDecodeError:
                result_data = {}

            print('✓ Successfully indexed!')
            print(f'  Chunks indexed: {result_data.get("chunks_indexed", 0)}')

            # Update database status
            await session.execute(
                text('UPDATE documents SET index_status = :status, chunk_count = :count WHERE id = :id'),
                {'status': 'completed', 'count': result_data.get('chunks_indexed', 0), 'id': document_id}
            )
            await session.commit()
            print('✓ Database updated')
            return True

if __name__ == '__main__':
    doc_id = int(sys.argv[1]) if len(sys.argv) > 1 else 21
    print(f'Reindexing document {doc_id}...\n')
    success = asyncio.run(trigger_indexing(doc_id))
    sys.exit(0 if success else 1)
