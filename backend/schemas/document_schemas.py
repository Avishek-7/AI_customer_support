from pydantic import BaseModel, EmailStr
from typing import List, Optional

class DocumentBase(BaseModel):
    title: str
    content: str

class DocumentUpload(BaseModel):
    title: str
    file_content: str 

class DocumentResponse(DocumentBase):
    id: int
    owner_id: int

    class Config:
        orm_mode = True

class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]

class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None

class DocumentDeleteResponse(BaseModel):
    detail: str

class DocumentShareRequest(BaseModel):
    email: EmailStr

class DocumentShareResponse(BaseModel):
    detail: str

class DocumentSearchRequest(BaseModel):
    query: str

class DocumentSearchResponse(BaseModel):
    documents: List[DocumentResponse]

class DocumentStatusUpdateRequest(BaseModel):
    document_id: int
    status: str
    chunk_count: Optional[int] = None




