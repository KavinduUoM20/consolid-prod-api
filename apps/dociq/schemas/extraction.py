from typing import Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel


class ExtractionRead(BaseModel):
    """Complete extraction record for API responses"""
    id: UUID
    document_id: Optional[UUID] = None
    template_id: Optional[UUID] = None
    target_mapping_id: Optional[UUID] = None
    current_step: Optional[str] = None
    status: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }


class ExtractionUpdate(BaseModel):
    """Schema for updating extraction fields"""
    template_id: Optional[UUID] = None
    target_mapping_id: Optional[UUID] = None
    current_step: Optional[str] = None
    status: Optional[str] = None

    model_config = {
        "from_attributes": True
    }


class ExtractionCreate(BaseModel):
    """Schema for creating new extraction records"""
    document_id: Optional[UUID] = None
    template_id: Optional[UUID] = None
    target_mapping_id: Optional[UUID] = None
    current_step: Optional[str] = None
    status: Optional[str] = None

    model_config = {
        "from_attributes": True
    } 