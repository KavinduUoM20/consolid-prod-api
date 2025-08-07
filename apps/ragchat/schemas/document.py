from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class DocumentCreate(BaseModel):
    filename: str
    file_path: str
    file_size: int
    file_type: str
    title: Optional[str] = None
    description: Optional[str] = None
    user_id: Optional[str] = None

class DocumentResponse(BaseModel):
    id: str
    filename: str
    file_path: str
    file_size: int
    file_type: str
    created_at: datetime
    updated_at: datetime
    is_processed: bool
    processing_status: str
    vector_store_id: Optional[str] = None
    chunk_count: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None
    user_id: Optional[str] = None 