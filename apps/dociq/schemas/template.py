from typing import Optional, List, Literal
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel


class FieldMappingSchema(BaseModel):
    target_field: str
    sample_field_names: List[str]
    value_patterns: List[str]
    description: Optional[str] = None
    required: bool = True

    model_config = {
        "from_attributes": True
    }


class TemplateBase(BaseModel):
    name: str
    type: Literal["pdf", "excel"]
    category: str
    description: Optional[str] = None
    status: Optional[str] = "active"
    field_mappings: List[FieldMappingSchema]

    # Excel-specific
    header_row: Optional[int] = None
    sheetname: Optional[str] = None

    model_config = {
        "from_attributes": True
    }


class TemplateCreate(TemplateBase):
    pass


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[Literal["pdf", "excel"]] = None
    category: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    field_mappings: Optional[List[FieldMappingSchema]] = None
    header_row: Optional[int] = None
    sheetname: Optional[str] = None

    model_config = {
        "from_attributes": True
    }


class TemplateRead(TemplateBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    fields: int  # Calculated field

    model_config = {
        "from_attributes": True
    }
