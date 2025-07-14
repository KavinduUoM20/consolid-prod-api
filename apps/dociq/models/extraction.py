import uuid
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, ForeignKey
import sqlalchemy.dialects.postgresql as pg


class Extraction(SQLModel, table=True):
    __tablename__ = "extractions"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(pg.UUID(as_uuid=True), primary_key=True, nullable=False)
    )

    # Optional foreign keys for step-wise KYC flow
    document_id: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(pg.UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True)
    )
    template_id: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(pg.UUID(as_uuid=True), ForeignKey("templates.id"), nullable=True)
    )
    target_mapping_id: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(pg.UUID(as_uuid=True), ForeignKey("target_mappings.id"), nullable=True)
    )

    # KYC flow tracking
    current_step: Optional[str] = Field(
        default=None,
        sa_column=Column(pg.VARCHAR(100), nullable=True)
    )
    status: Optional[str] = Field(
        default="uploaded",
        sa_column=Column(pg.VARCHAR(50), nullable=True)
    )

    # Timestamps
    created_at: datetime = Field(
        sa_column=Column(pg.TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow)
    )
    updated_at: datetime = Field(
        sa_column=Column(pg.TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    )

    # Relationships
    document: Optional["Document"] = Relationship(back_populates="extractions")
    template: Optional["Template"] = Relationship(back_populates="extractions")
    target_mapping: Optional["TargetMapping"] = Relationship(back_populates="extractions")

    def __repr__(self):
        return f"<Extraction {self.id} (Step: {self.current_step}, Status: {self.status})>"

    @property
    def is_completed(self) -> bool:
        """Check if the extraction is completed"""
        return self.status == "completed"

    @property
    def has_document(self) -> bool:
        """Check if document is associated"""
        return self.document_id is not None

    @property
    def has_template(self) -> bool:
        """Check if template is associated"""
        return self.template_id is not None

    @property
    def has_target_mapping(self) -> bool:
        """Check if target mapping is associated"""
        return self.target_mapping_id is not None 