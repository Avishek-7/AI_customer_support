#!/usr/bin/env python3
"""Script to manually trigger indexing for a document"""
import asyncio
import httpx
import sys
from sqlalchemy import text
from core.database import AsyncSessionLocal

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
        print(f'Found document: ID={document_id}, Title={title}')
        print(f'Content length: {len(content)} characters')
        print(f'Triggering indexing to AI engine...')
        
        # Call AI engine to index
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                'http://localhost:9000/index-document',
                json={
                    'document_id': document_id,
                    'title': title,
                    'content': content
                }
            )
            
            if response.status_code == 200:
                result_data = response.json()
                print(f'✓ Successfully indexed!')
                print(f'  Chunks indexed: {result_data.get("chunks_indexed")}')
                
                # Update database status
                await session.execute(
                    text('UPDATE documents SET index_status = :status, chunk_count = :count WHERE id = :id'),
                    {'status': 'completed', 'count': result_data.get('chunks_indexed', 0), 'id': document_id}
                )
                await session.commit()
                print(f'✓ Database updated')
                return True
            else:
                print(f'✗ Indexing failed: {response.status_code}')
                print(response.text)
                return False

if __name__ == '__main__':
    doc_id = int(sys.argv[1]) if len(sys.argv) > 1 else 21
    print(f'Reindexing document {doc_id}...\n')
    success = asyncio.run(trigger_indexing(doc_id))
    sys.exit(0 if success else 1)
