from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional
from uuid import uuid4

class Document(SQLModel, table=True):
    __tablename__ = "documents"
    
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    filename: str = Field(max_length=255)
    file_path: str = Field(max_length=500)
    file_size: int = Field(default=0)
    file_type: str = Field(max_length=50)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Document processing status
    is_processed: bool = Field(default=False)
    processing_status: str = Field(default="pending", max_length=50)
    
    # Vector storage info
    vector_store_id: Optional[str] = Field(default=None, max_length=255)
    chunk_count: Optional[int] = Field(default=None)
    
    # Metadata
    title: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = Field(default=None, max_length=1000)
    user_id: Optional[str] = Field(default=None, max_length=255)
    
    class Config:
        arbitrary_types_allowed = True 