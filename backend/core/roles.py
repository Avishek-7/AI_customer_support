from fastapi import Depends, HTTPException
from core.security import get_current_user

def require_admin(user=Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(403, "Admin access required")
    return user
