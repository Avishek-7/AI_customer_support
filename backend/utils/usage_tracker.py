from models.usage import APIUsage

async def track_usage(db, user_id, endpoint, tokens, latency):
    db.add(APIUsage(
        user_id=user_id,
        endpoint=endpoint,
        tokens=tokens,
        latency=latency  
    ))
    
    await db.commit()