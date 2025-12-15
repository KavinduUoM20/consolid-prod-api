# OCAP Manufacturing Technical Support - Technical Documentation

## Overview

The OCAP (Operations Control and Problem-solving) application is a manufacturing technical support system that provides real-time assistance for production floor issues. It uses AI-powered conversation flows to diagnose technical problems and provide solutions based on a structured database of manufacturing knowledge.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Application                          │
├─────────────────────────────────────────────────────────────────┤
│  Main App (main.py) → API Router → V1 Router → OCAP Router     │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                     OCAP Module                                 │
├─────────────────────────────────────────────────────────────────┤
│  Routes/          Models/           Services/                   │
│  ├─chat.py        ├─technical_data.py  ├─manufacturing_assistant.py│
│  └─health.py      └─technical_models.py└─technical_db_service.py │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│              External Dependencies                              │
├─────────────────────────────────────────────────────────────────┤
│  Azure OpenAI    │    PostgreSQL     │    LangChain            │
│  (GPT Models)    │    (OCAP Table)   │    (AI Orchestration)   │
└─────────────────────────────────────────────────────────────────┘
```

## Technical Flow: From Endpoint to Solution

### 1. Entry Point - WebSocket Connection

**Endpoint**: `ws://localhost:8000/api/v1/ocap/ocap-chat/ws`

**File**: `apps/ocap/routes/chat.py`

```python
@router.websocket("/ocap-chat/ws")
async def manufacturing_chat_websocket(websocket: WebSocket)
```

**Process**:
1. **Connection Management**: Checks against `MAX_ACTIVE_CONNECTIONS` limit (50)
2. **Assistant Initialization**: Creates `ManufacturingTechnicalAssistant` instance
3. **Connection Storage**: Stores connection in `active_connections` dictionary
4. **Welcome Message**: Sends structured welcome message via `WebSocketMessage` model

### 2. Message Processing Pipeline

**Core Method**: `ManufacturingTechnicalAssistant.process_user_message()`

**File**: `apps/ocap/services/manufacturing_assistant.py`

#### Phase 1: Intent Analysis
```python
# Uses LangChain + Azure OpenAI to analyze user intent
intent_analysis = self.intent_chain.invoke({
    "user_input": user_input,
    "conversation_history": context
})
```

**Output**: `TechnicalIntent` model containing:
- `intent`: problem_solving, inquiry, clarification, etc.
- `confidence`: 0-1 score
- `technical_entities`: List of mentioned technical terms
- `urgency`: low, medium, high, critical
- `problem_severity`: minor, moderate, major, critical

#### Phase 2: Slot Extraction
```python
# Extracts technical problem parameters
extracted_slots = self._extract_slots_from_input(user_input)
```

**Technical Slots** (Required for solution):
- `operation`: Manufacturing operation (e.g., "Attach sleeve to body")
- `machine_type`: Machine type (e.g., "FS", "OL", "LS")
- `defect`: Type of defect (e.g., "Broken stitch", "Raw edge")
- `error`: Specific error (e.g., "Blunt needle", "Throat plate damage")

**Database Matching**: Uses fuzzy matching against predefined technical database:
```python
self.technical_db = {
    "operations": ["Attach sleeve to body", "Side Seam", ...],
    "machine_types": ["FS", "OL", "LS", "BS", ...],
    "defects": ["Broken stitch", "Raw edge", ...],
    "errors": ["Blunt needle", "Throat plate damage", ...]
}
```

#### Phase 3: Conversation Phase Determination
```python
phase = self._determine_conversation_phase(intent_analysis)
```

**Conversation Phases**:
- `GREETING`: Initial welcome
- `PROBLEM_IDENTIFICATION`: Gathering basic problem info
- `CLARIFICATION`: Asking for missing details
- `ANALYSIS`: Processing complete information
- `SOLUTION_GENERATION`: Providing technical solution
- `COMPLETION`: Solution delivered
- `POST_SOLUTION`: Offering additional help
- `NEW_PROBLEM`: Starting new problem diagnosis

#### Phase 4: Response Generation

**If Missing Information**:
```python
response = self._generate_intelligent_response(user_input, intent_analysis)
```
- Uses LangChain to generate contextual questions
- Prioritizes missing slots by importance
- Provides examples from technical database

**If Complete Information**:
```python
response = await self._generate_technical_solution()
```

### 3. Database Integration

**File**: `apps/ocap/services/technical_db_service.py`

**Database Table**: `ocap` (PostgreSQL)
**Model**: `OCAPTechnicalData` (SQLModel)

**Schema**:
```sql
CREATE TABLE ocap (
    operation TEXT PRIMARY KEY,
    machinetype TEXT,
    defect TEXT,
    error TEXT,
    action TEXT,        -- Solution steps
    fishbone TEXT       -- Root cause analysis
);
```

**Query Process**:
```python
async def retrieve_technical_solutions(self, slots: Dict[str, Any])
```

1. **Condition Building**: Creates ILIKE conditions for partial matching
2. **Query Execution**: `SELECT * FROM ocap WHERE ... LIMIT 1`
3. **Result Processing**: Returns structured solution or "not found"

### 4. AI Solution Generation

**File**: `apps/ocap/services/manufacturing_assistant.py`

**LangChain Integration**:
```python
# Solution generation chain
solution = self.solution_chain.invoke({
    "problem_details": json.dumps(problem_details, indent=2),
    "database_context": database_context
})
```

**Process**:
1. **Database Lookup**: Retrieves matching solution from OCAP table
2. **AI Enhancement**: Uses Azure OpenAI to format and enhance solution
3. **Contextual Response**: Combines database knowledge with AI reasoning
4. **Post-Solution Flow**: Transitions to offering additional help

### 5. Response Delivery

**WebSocket Message Format**:
```python
response_message = WebSocketMessage(
    type="assistant_response",
    content=response,
    timestamp=datetime.now().isoformat(),
    metadata={
        "connection_id": connection_id,
        "conversation_phase": summary.conversation_phase,
        "turn_count": summary.turn_count,
        "collected_slots": summary.collected_slots,
        "missing_slots": summary.missing_slots,
        "solved_problems": summary.solved_problems
    }
)
```

## Configuration & Settings

**File**: `apps/ocap/config.py`

```python
class OCAPSettings(BaseSettings):
    CONVERSATION_TIMEOUT: int = 3600  # 1 hour
    MAX_CONVERSATION_TURNS: int = 100
    MAX_ACTIVE_CONNECTIONS: int = 50
    CONNECTION_CLEANUP_INTERVAL: int = 300  # 5 minutes
```

## Database Configuration

**File**: `apps/ocap/db.py`

- **Reuses DocIQ Database**: Shares PostgreSQL connection
- **Session Management**: Async SQLAlchemy sessions
- **Table Discovery**: Auto-imports OCAP models

## Authentication & Security

**Integration**: Uses core authentication system (`core/auth/`)

**JWT Token Structure**:
```json
{
    "sub": "user_id",
    "username": "username",
    "email": "user@example.com",
    "role": "user_role",
    "tenant_id": "tenant_uuid",
    "tenant_slug": "tenant_name",
    "exp": 1234567890,
    "iat": 1234567890,
    "jti": "unique_token_id"
}
```

**Note**: Current OCAP WebSocket endpoint does not enforce authentication, but the infrastructure is available.

## Health Monitoring

**Endpoint**: `GET /api/v1/ocap/ocap/health`

**File**: `apps/ocap/routes/health.py`

**Health Checks**:
1. **Environment Variables**: Azure OpenAI configuration
2. **LLM Basic Connectivity**: Simple test prompt
3. **LangChain Components**: Chain initialization test
4. **Manufacturing Assistant**: Assistant initialization test

**Test Endpoint**: `GET /api/v1/ocap/ocap/test-llm`
- Direct assistant message processing test
- Returns success/failure with detailed error info

## Error Handling & Fallbacks

### LLM Failure Handling
```python
def _generate_fallback_response(self) -> str:
    """Generate fallback response when LLM fails."""
    missing = self._get_missing_critical_slots()
    # Returns structured questions based on missing information
```

### Database Failure Handling
```python
# If database retrieval fails, AI generates solution from context
if not db_result.get("found"):
    return "No matching technical solution found in database for current problem parameters."
```

### Connection Management
- **Connection Limits**: Enforced at WebSocket level
- **Cleanup**: Automatic cleanup on disconnect
- **Error Recovery**: Graceful degradation with informative messages

## Performance Considerations

### Connection Management
- **Max Connections**: 50 concurrent WebSocket connections
- **Memory Usage**: Each connection stores assistant instance + conversation state
- **Cleanup**: 5-minute interval cleanup for stale connections

### Database Optimization
- **Query Strategy**: LIMIT 1 for single solution retrieval
- **Indexing**: Primary key on `operation` field
- **Connection Pooling**: Reuses DocIQ database connection pool

### AI Processing
- **Temperature**: 0.2 (deterministic responses)
- **Timeout**: 30 seconds per LLM call
- **Retries**: 2 retry attempts for failed calls
- **Fallback**: Structured fallback responses when AI fails

## Deployment Architecture

```
Internet → Load Balancer → FastAPI App → OCAP Module
                                    ↓
                              Azure OpenAI API
                                    ↓
                              PostgreSQL Database
```

**Environment Variables Required**:
- `AZURE_OPENAI_DEPLOYMENT`
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_VERSION`
- `AZURE_OPENAI_API_KEY`

## API Integration Points

### WebSocket Client Example
```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/ocap/ocap-chat/ws');

ws.onmessage = function(event) {
    const message = JSON.parse(event.data);
    console.log('Assistant:', message.content);
    console.log('Metadata:', message.metadata);
};

ws.send(JSON.stringify({
    content: "I'm having broken stitches on my overlock machine"
}));
```

### Health Check Integration
```bash
# Check system health
curl http://localhost:8000/api/v1/ocap/ocap/health

# Test LLM directly
curl http://localhost:8000/api/v1/ocap/ocap/test-llm
```

## Monitoring & Observability

### Logging
- **Connection Events**: Connection/disconnection logging
- **Processing Steps**: Detailed step-by-step processing logs
- **Error Tracking**: Full error traces with context
- **Performance Metrics**: Processing time tracking

### Metrics Available
- Active connection count
- Conversation turn counts
- Solved problem counts
- Error rates by component
- Database query performance

### Debug Information
```python
# Available via /ocap-chat/active-connections endpoint
{
    "active_connections": 5,
    "connections": [
        {
            "connection_id": "conn_20231201_143022_123456",
            "connected_at": "2023-12-01T14:30:22",
            "conversation_summary": {
                "collected_slots": {...},
                "missing_slots": [...],
                "conversation_phase": "clarification",
                "turn_count": 3,
                "solved_problems": 0
            }
        }
    ]
}
```

## Future Enhancement Areas

1. **Authentication Integration**: Add JWT validation to WebSocket connections
2. **Rate Limiting**: Implement per-user rate limiting
3. **Conversation Persistence**: Store conversation history in database
4. **Analytics Dashboard**: Real-time monitoring of system performance
5. **Multi-language Support**: Extend to support multiple languages
6. **Voice Integration**: Add speech-to-text capabilities
7. **Mobile App Integration**: Optimize for mobile manufacturing environments
