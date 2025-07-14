import uuid
from datetime import datetime
from typing import Optional, Literal, List
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column
import sqlalchemy.dialects.postgresql as pg


class Document(SQLModel, table=True):
    __tablename__ = "documents"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(pg.UUID(as_uuid=True), primary_key=True, nullable=False)
    )

    doc_name: str = Field(sa_column=Column(pg.VARCHAR(255), nullable=False))
    doc_size: int = Field(sa_column=Column(pg.BIGINT, nullable=False))  # Size in bytes
    pages: Optional[int] = Field(default=None, sa_column=Column(pg.INTEGER, nullable=True))
    doc_type: Literal["pdf", "excel", "doc", "docx", "txt", "image"] = Field(
        sa_column=Column(pg.VARCHAR(50), nullable=False)
    )
    doc_path: str = Field(sa_column=Column(pg.TEXT, nullable=False))

    created_at: datetime = Field(
        sa_column=Column(pg.TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow)
    )
    updated_at: datetime = Field(
        sa_column=Column(pg.TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    )

    # Relationships
    extractions: List["Extraction"] = Relationship(back_populates="document")

    def __repr__(self):
        return f"<Document {self.doc_name} ({self.doc_type})>"

    @property
    def size_mb(self) -> float:
        """Return document size in megabytes"""
        return round(self.doc_size / (1024 * 1024), 2)

    @property
    def size_kb(self) -> float:
        """Return document size in kilobytes"""
        return round(self.doc_size / 1024, 2) 