import uuid
from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column
import sqlalchemy.dialects.postgresql as pg
from pydantic import BaseModel


class TargetMappingEntry(BaseModel):
    """Individual target mapping entry with field, value, and confidence"""
    target_field: str
    target_value: str
    target_confidence: Optional[float] = None

    model_config = {
        "from_attributes": True
    }


class TargetMapping(SQLModel, table=True):
    __tablename__ = "target_mappings"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(pg.UUID(as_uuid=True), primary_key=True, nullable=False)
    )

    overall_confidence: Optional[float] = Field(
        default=None,
        sa_column=Column(pg.FLOAT, nullable=True)
    )

    target_mappings: List[dict] = Field(
        sa_column=Column(pg.JSONB, nullable=False, default=list)
    )

    created_at: datetime = Field(
        sa_column=Column(pg.TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow)
    )
    updated_at: datetime = Field(
        sa_column=Column(pg.TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    )

    # Relationships
    extractions: List["Extraction"] = Relationship(back_populates="target_mapping")

    def __repr__(self):
        return f"<TargetMapping {self.id} (Confidence: {self.overall_confidence})>"

    def calculate_overall_confidence(self) -> float:
        """Calculate overall confidence as sum of individual target confidences"""
        if not self.target_mappings:
            return 0.0
        
        total_confidence = 0.0
        valid_entries = 0
        
        for mapping in self.target_mappings:
            if mapping.get('target_confidence') is not None:
                total_confidence += mapping['target_confidence']
                valid_entries += 1
        
        return total_confidence if valid_entries > 0 else 0.0

    def update_overall_confidence(self) -> None:
        """Update the overall_confidence field with calculated value"""
        self.overall_confidence = self.calculate_overall_confidence()

    def add_target_mapping(self, target_field: str, target_value: str, target_confidence: Optional[float] = None) -> None:
        """Add a new target mapping entry and update overall confidence"""
        mapping_entry = {
            "target_field": target_field,
            "target_value": target_value,
            "target_confidence": target_confidence
        }
        self.target_mappings.append(mapping_entry)
        self.update_overall_confidence()

    def get_mapping_by_field(self, target_field: str) -> Optional[dict]:
        """Get a specific mapping entry by target field"""
        for mapping in self.target_mappings:
            if mapping.get('target_field') == target_field:
                return mapping
        return None

    def update_mapping_confidence(self, target_field: str, new_confidence: float) -> bool:
        """Update confidence for a specific target field"""
        mapping = self.get_mapping_by_field(target_field)
        if mapping:
            mapping['target_confidence'] = new_confidence
            self.update_overall_confidence()
            return True
        return False

    @property
    def mapping_count(self) -> int:
        """Get the number of target mappings"""
        return len(self.target_mappings)

    @property
    def average_confidence(self) -> float:
        """Calculate average confidence across all mappings"""
        if not self.target_mappings:
            return 0.0
        
        valid_confidences = [m.get('target_confidence') for m in self.target_mappings if m.get('target_confidence') is not None]
        return sum(valid_confidences) / len(valid_confidences) if valid_confidences else 0.0 