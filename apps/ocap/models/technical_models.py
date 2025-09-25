from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field

class ConversationPhase(Enum):
    """Conversation phases for technical problem solving."""
    GREETING = "greeting"
    PROBLEM_IDENTIFICATION = "problem_identification"
    CLARIFICATION = "clarification"
    ANALYSIS = "analysis"
    SOLUTION_GENERATION = "solution_generation"
    COMPLETION = "completion"
    POST_SOLUTION = "post_solution"
    NEW_PROBLEM = "new_problem"

class TechnicalSlotExtraction(BaseModel):
    """Pydantic model for technical problem slot extraction."""
    operation: Optional[str] = Field(description="Manufacturing operation being performed")
    machine_type: Optional[str] = Field(description="Type of machine being used")
    defect: Optional[str] = Field(description="Type of defect observed")
    error: Optional[str] = Field(description="Specific error or issue encountered")

class TechnicalIntent(BaseModel):
    """Model for understanding technical problem intent."""
    intent: str = Field(description="Primary intent: problem_solving, inquiry, clarification, complaint, etc.")
    confidence: float = Field(description="Confidence score 0-1")
    technical_entities: List[str] = Field(description="List of technical entities mentioned")
    urgency: str = Field(description="low, medium, high, critical")
    problem_severity: str = Field(description="minor, moderate, major, critical")

class ConversationState(BaseModel):
    """Model for conversation state."""
    slots: Dict[str, Any] = Field(default_factory=dict)
    conversation_history: List[str] = Field(default_factory=list)
    current_phase: ConversationPhase = ConversationPhase.GREETING
    technical_context: Dict[str, Any] = Field(default_factory=dict)
    clarifications_needed: List[str] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)
    turn_count: int = 0
    solved_problems: List[Dict[str, Any]] = Field(default_factory=list)
    problem_count: int = 0

class WebSocketMessage(BaseModel):
    """Model for WebSocket messages."""
    type: str = Field(description="Message type: user_message, assistant_response, error, etc.")
    content: str = Field(description="Message content")
    timestamp: Optional[str] = Field(description="Message timestamp")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")

class ConversationSummary(BaseModel):
    """Model for conversation summary."""
    collected_slots: Dict[str, Any]
    missing_slots: List[str]
    conversation_phase: str
    turn_count: int
    solved_problems: int
    problem_count: int
