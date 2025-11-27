from fastapi import FastAPI, APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from core.database import get_db
# from core.security import hash_password, verify_password, create_access_token
from models.user import User
from models.document import Document
from schemas.document_schemas import (
    DocumentBase,
    DocumentCreate,
    DocumentResponse,
    DocumentListResponse,
    DocumentUpdate,
    DocumentDeleteResponse,
    DocumentShareRequest,
    DocumentShareResponse,
    DocumentSearchRequest,
    DocumentSearchResponse,
    DocumentUpload,
)


