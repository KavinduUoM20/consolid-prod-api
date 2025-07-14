import uuid
from datetime import datetime
from typing import Optional, List, Literal
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column
import sqlalchemy.dialects.postgresql as pg
from pydantic import BaseModel


# Only used in JSON storage — no separate DB table
class FieldMapping(BaseModel):
    target_field: str
    sample_field_names: List[str]
    value_patterns: List[str]
    description: Optional[str] = None
    required: bool = True


class Template(SQLModel, table=True):
    __tablename__ = "templates"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(pg.UUID(as_uuid=True), primary_key=True, nullable=False)
    )

    name: str = Field(sa_column=Column(pg.VARCHAR(255), nullable=False))
    type: Literal["pdf", "excel"] = Field(sa_column=Column(pg.VARCHAR(50), nullable=False))
    category: str = Field(sa_column=Column(pg.VARCHAR(100), nullable=False))
    description: Optional[str] = Field(default=None, sa_column=Column(pg.TEXT, nullable=True))
    status: Optional[str] = Field(default="active", sa_column=Column(pg.VARCHAR(50), nullable=True))

    field_mappings: List[FieldMapping] = Field(
        sa_column=Column(pg.JSONB, nullable=False, default=list)
    )

    # Excel-specific
    header_row: Optional[int] = Field(default=None, sa_column=Column(pg.INTEGER, nullable=True))
    sheetname: Optional[str] = Field(default=None, sa_column=Column(pg.VARCHAR(100), nullable=True))

    created_at: datetime = Field(
        sa_column=Column(pg.TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow)
    )
    updated_at: datetime = Field(
        sa_column=Column(pg.TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    )

    # Relationships
    extractions: List["Extraction"] = Relationship(back_populates="template")

    def __repr__(self):
        return f"<Template {self.name} ({self.type})>"

    @property
    def fields(self) -> int:
        return len(self.field_mappings)
