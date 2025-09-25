from typing import Optional
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, Text

class OCAPTechnicalData(SQLModel, table=True):
    """Simplified model for the 'ocap' table focusing on slot-based fields."""
    
    __tablename__ = "ocap"
    
    # Core slot fields that we extract and match on
    operation: Optional[str] = Field(
        sa_column=Column(Text, primary_key=True),
        description="Manufacturing operation"
    )
    
    machinetype: Optional[str] = Field(
        sa_column=Column(Text),
        description="Type of machine used"
    )
    
    defect: Optional[str] = Field(
        sa_column=Column(Text),
        description="Description of the defect"
    )
    
    error: Optional[str] = Field(
        sa_column=Column(Text),
        description="Specific error or issue description"
    )
    
    # Solution fields
    action: Optional[str] = Field(
        sa_column=Column(Text),
        description="Recommended action or solution"
    )
    
    fishbone: Optional[str] = Field(
        sa_column=Column(Text),
        description="Root cause analysis"
    )
    
    def __repr__(self):
        return f"<OCAPTechnicalData operation='{self.operation}' defect='{self.defect}'>"
    
    def to_solution_dict(self) -> dict:
        """Convert to dictionary focusing on solution information."""
        return {
            "operation": self.operation,
            "machinetype": self.machinetype,
            "defect": self.defect,
            "error": self.error,
            "action": self.action,
            "fishbone": self.fishbone
        }
