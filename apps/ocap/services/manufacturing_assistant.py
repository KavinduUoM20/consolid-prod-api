import os
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from langchain_openai import AzureChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser

from ..models.technical_models import (
    ConversationPhase, 
    TechnicalSlotExtraction, 
    TechnicalIntent, 
    ConversationState,
    ConversationSummary
)
from ..config import get_ocap_settings
from .technical_db_service import TechnicalDatabaseService
from common.utils.llm_connections import required_vars

class ManufacturingTechnicalAssistant:
    """Advanced technical problem-solving assistant for manufacturing."""
    
    def __init__(self):
        """Initialize the technical assistant."""
        settings = get_ocap_settings()
        
        # Use existing Azure OpenAI configuration from common/utils/llm_connections
        self.llm = AzureChatOpenAI(
            azure_deployment=required_vars["AZURE_OPENAI_DEPLOYMENT"],
            api_version=required_vars["AZURE_OPENAI_API_VERSION"],
            azure_endpoint=required_vars["AZURE_OPENAI_ENDPOINT"],
            api_key=required_vars["AZURE_OPENAI_API_KEY"],
            temperature=0.2,
            timeout=30,
            max_retries=2
        )
        
        # Store settings for OCAP-specific configuration
        self.settings = settings
        
        # Initialize database service
        self.db_service = TechnicalDatabaseService()
        
        # Conversation state
        self.conversation_state = ConversationState()
        
        # Technical slot configuration with priorities and validation
        self.slot_config = {
            "operation": {
                "type": "string", 
                "priority": 1, 
                "required": True,
                "validation": lambda x: len(x.strip()) >= 3,
                "description": "Manufacturing operation being performed",
                "examples": [
                    "Attach sleeve to body",
                    "Attach sleeve to body barrel seam", 
                    "Raglon sleeve attach",
                    "Side seam",
                    "Hemming",
                    "Button hole",
                    "Zipper attachment"
                ]
            },
            "machine_type": {
                "type": "string", 
                "priority": 2, 
                "required": True,
                "validation": lambda x: len(x.strip()) >= 1,
                "description": "Type of machine being used",
                "examples": [
                    "FS (Flat Seam)",
                    "OL (Overlock)",
                    "LS (Lock Stitch)",
                    "BS (Blind Stitch)",
                    "BH (Button Hole)",
                    "ZZ (Zigzag)"
                ]
            },
            "defect": {
                "type": "string", 
                "priority": 3, 
                "required": True,
                "validation": lambda x: len(x.strip()) >= 3,
                "description": "Type of defect observed",
                "examples": [
                    "Broken stitch",
                    "Raw edge",
                    "Puckering",
                    "Skipped stitch",
                    "Thread break",
                    "Uneven seam",
                    "Loose tension",
                    "Tight seam"
                ]
            },
            "error": {
                "type": "string", 
                "priority": 4, 
                "required": True,
                "validation": lambda x: len(x.strip()) >= 3,
                "description": "Specific error or issue encountered",
                "examples": [
                    "Blunt needle",
                    "Foot/Throat plate damage",
                    "Incorrect foot shoe",
                    "Wrong needle size",
                    "Thread tension issue",
                    "Feed dog problem",
                    "Timing issue",
                    "Motor malfunction"
                ]
            }
        }
        
        # Technical values database - structured JSON with predefined values
        self.technical_db = {
            "operations": [
                "Attach sleeve to body",
                "Attach sleeve to body barrel seam",
                "Raglon Sleeve attach",
                "Side Seam"
            ],
            "machine_types": [
                "FS",  # Flat Seam
                "OL",  # Overloc
            ],
            "defects": [
                "Broken stitch",
                "Raw edge"
               
            ],
            "errors": [
                "Throat plate damage",
                "Manual trimming",
                "Looper damage / Looper/Spreader damage",
                "Incorrect timing",
                "Incorrect thread tension tightness",
                "Incorrect Foot pressure",
                "Incorrect foot height",
                "Incorrect feedog height",
                "High pressure vacuum cutters",
                "Blunt Needle",
                "Incorrect Foot shoe"
            ]
        }
        
        self._initialize_chains()
        
    def _initialize_chains(self):
        """Initialize all LLM chains for technical problem solving."""
        
        # 1. Technical Intent Understanding Chain
        intent_template = PromptTemplate(
            input_variables=["user_input", "conversation_history"],
            template="""
Analyze the user's technical problem intent and extract key information:

Conversation History: {conversation_history}
Current User Input: "{user_input}"

Determine:
1. Primary intent (problem_solving, inquiry, clarification, equipment_check, etc.)
2. Confidence level (0.0 to 1.0)
3. Technical entities mentioned (operations, machines, defects, errors, etc.)
4. Urgency level (low, medium, high, critical)
5. Problem severity (minor, moderate, major, critical)

Return as JSON only.
"""
        )
        self.intent_chain = intent_template | self.llm | JsonOutputParser(pydantic_object=TechnicalIntent)
        
        # 2. Technical Slot Extraction Chain
        slot_template = PromptTemplate(
            input_variables=["user_input", "existing_slots", "conversation_context", "technical_database"],
            template="""
You are an expert manufacturing technical support specialist. Extract technical problem information from the user's message.

Current Problem Information: {existing_slots}
Conversation Context: {conversation_context}
User Message: "{user_input}"

TECHNICAL DATABASE - Use EXACT values from this database:
{technical_database}

Extract or update these technical details ONLY if explicitly mentioned or clearly implied:
- operation: Manufacturing operation - MUST match exactly from operations list above
- machine_type: Machine type - MUST match exactly from machine_types list above  
- defect: Type of defect - MUST match exactly from defects list above
- error: Specific error/issue - MUST match exactly from errors list above

CRITICAL MATCHING RULES:
1. ALWAYS use the exact value from the database that best matches user input
2. If user says "issue in the raw edge" → use "Raw edge" from defects
3. If user says "overlock" → use "OL" from machine_types
4. If user says "stitches breaking" → use "Broken stitch" from defects
5. If user says "needle is dull" → use "Blunt needle" from errors
6. Map user's natural language to the closest database value
7. Return only valid JSON with extracted fields
8. Use null for fields not mentioned or if no good match exists

Example: User says "I'm having broken stitches on my overlock while doing side seams, think it's a blunt needle"
Response: {{"operation": "Side seam", "machine_type": "OL", "defect": "Broken stitch", "error": "Blunt needle"}}

Example: User says "issue in the raw edge during hemming on flat seam machine"
Response: {{"operation": "Hemming", "machine_type": "FS", "defect": "Raw edge", "error": null}}
"""
        )
        self.slot_chain = slot_template | self.llm | JsonOutputParser(pydantic_object=TechnicalSlotExtraction)
        
        # 3. Technical Response Generation Chain
        response_template = PromptTemplate(
            input_variables=["conversation_state", "user_input", "conversation_phase"],
            template="""
You are a professional manufacturing technical support specialist. Generate a helpful, technical response.

Current State: {conversation_state}
User Input: "{user_input}"
Conversation Phase: {conversation_phase}

Guidelines:
1. Be professional, knowledgeable, and helpful
2. Use appropriate technical terminology
3. Ask for missing technical information systematically
4. Show you understand the manufacturing context
5. Ask for 1-2 pieces of information at most per turn
6. Prioritize most critical missing information for problem diagnosis
7. Use clear, actionable language
8. If user seems confused, offer examples or clarification
9. Keep responses concise and focused - aim for 2-3 sentences maximum

Special Phase Guidelines:
- POST_SOLUTION: Ask if they have other technical problems or need clarification
- NEW_PROBLEM: Help them start diagnosing a new technical issue
- After COMPLETION: Transition smoothly to offering additional technical support

Response should be professional and technically accurate, like talking to an experienced technician.
"""
        )
        self.response_chain = response_template | self.llm | StrOutputParser()
        
        # 4. Technical Solution Generation Chain
        solution_template = PromptTemplate(
            input_variables=["problem_details", "database_context"],
            template="""
Generate a concise technical solution based on the problem details and database context.

Problem Details: {problem_details}

Database Context:
{database_context}

Instructions:
1. If database context contains a matching solution, use it as the primary reference
2. If no database context is available, provide a relevant technical solution based on the problem details
3. Keep the solution concise but actionable - maximum 3-4 sentences
4. Include specific actions, settings, or components to check/adjust
5. Use professional manufacturing terminology
6. Focus on the most critical steps to resolve the issue

Format your response as a clear, actionable solution that a technician can immediately implement.
"""
        )
        self.solution_chain = solution_template | self.llm | StrOutputParser()
    
    def _get_conversation_context(self) -> str:
        """Get formatted conversation context."""
        history = self.conversation_state.conversation_history
        if not history:
            return "New technical support session"
        
        recent_history = history[-6:]  # Last 3 exchanges
        context = []
        for i, msg in enumerate(recent_history):
            speaker = "Technician" if i % 2 == 0 else "Support"
            context.append(f"{speaker}: {msg}")
        
        return "\n".join(context)
    
    def _determine_conversation_phase(self, intent_analysis: Dict) -> ConversationPhase:
        """Determine current conversation phase based on context."""
        slots = self.conversation_state.slots
        missing_slots = self._get_missing_critical_slots()
        current_phase = self.conversation_state.current_phase
        intent = intent_analysis.get("intent", "").lower()
        
        # Handle post-solution scenarios
        if current_phase == ConversationPhase.POST_SOLUTION:
            if any(keyword in intent for keyword in ["new", "another", "different", "problem", "issue"]):
                return ConversationPhase.NEW_PROBLEM
            elif any(keyword in intent for keyword in ["clarify", "explain", "more", "detail"]):
                return ConversationPhase.CLARIFICATION
            else:
                return ConversationPhase.POST_SOLUTION
        
        # Handle new problem after completion
        if current_phase == ConversationPhase.COMPLETION:
            return ConversationPhase.POST_SOLUTION
            
        # Handle new problem phase
        if current_phase == ConversationPhase.NEW_PROBLEM:
            if len(missing_slots) > 2:
                return ConversationPhase.PROBLEM_IDENTIFICATION
            elif len(missing_slots) > 0:
                return ConversationPhase.CLARIFICATION
            else:
                return ConversationPhase.ANALYSIS
        
        # Original logic for first problem
        if self.conversation_state.turn_count <= 1:
            return ConversationPhase.GREETING
        elif len(missing_slots) > 2:
            return ConversationPhase.PROBLEM_IDENTIFICATION
        elif len(missing_slots) > 0:
            return ConversationPhase.CLARIFICATION
        elif self.conversation_state.clarifications_needed:
            return ConversationPhase.CLARIFICATION
        elif len(missing_slots) == 0:
            return ConversationPhase.ANALYSIS
        else:
            return ConversationPhase.PROBLEM_IDENTIFICATION
    
    def _get_missing_critical_slots(self) -> List[str]:
        """Get missing slots ordered by priority."""
        slots = self.conversation_state.slots
        missing = []
        
        for slot_name, config in sorted(self.slot_config.items(), key=lambda x: x[1]["priority"]):
            if config["required"] and slot_name not in slots:
                missing.append(slot_name)
        
        return missing
    
    def _extract_slots_from_input(self, user_input: str) -> Dict:
        """Extract technical slots using advanced LLM processing with database matching."""
        try:
            context = self._get_conversation_context()
            existing_slots = self.conversation_state.slots
            
            # Prepare technical database for prompt
            db_context = json.dumps(self.technical_db, indent=2)
            
            print(f"🔍 Invoking slot extraction chain...")
            extracted = self.slot_chain.invoke({
                "user_input": user_input,
                "existing_slots": json.dumps(existing_slots, indent=2),
                "conversation_context": context,
                "technical_database": db_context
            })
            print(f"🔍 Slot extraction result: {extracted}")
            print(f"🔍 Slot extraction type: {type(extracted)}")
            
            # Validate extracted slots against database values
            validated_slots = {}
            # Handle both dict and Pydantic objects
            slot_items = extracted.dict().items() if hasattr(extracted, 'dict') else extracted.items()
            for slot_name, value in slot_items:
                if value is not None and slot_name in self.slot_config:
                    # Check if value exists in database
                    db_key = slot_name + "s" if slot_name != "machine_type" else "machine_types"
                    if db_key in self.technical_db:
                        if value in self.technical_db[db_key]:
                            validated_slots[slot_name] = value
                            print(f"✅ Matched {slot_name}: '{value}' from database")
                        else:
                            # Try fuzzy matching
                            best_match = self._find_best_match(value, self.technical_db[db_key])
                            if best_match:
                                validated_slots[slot_name] = best_match
                                print(f"🔄 Fuzzy matched {slot_name}: '{value}' → '{best_match}'")
                            else:
                                print(f"⚠️ No match found for {slot_name}: '{value}' in database")
                    else:
                        # Fallback to original validation
                        config = self.slot_config[slot_name]
                        try:
                            if config["validation"](value):
                                validated_slots[slot_name] = value
                            else:
                                print(f"⚠️ Invalid value for {slot_name}: {value}")
                        except Exception as e:
                            print(f"⚠️ Validation error for {slot_name}: {e}")
            
            return validated_slots
            
        except Exception as e:
            print(f"❌ Error extracting slots: {e}")
            return {}
    
    def _find_best_match(self, user_value: str, db_values: List[str]) -> Optional[str]:
        """Find best matching value from database using fuzzy matching."""
        user_value_lower = user_value.lower().strip()
        
        # Exact match (case insensitive)
        for db_value in db_values:
            if user_value_lower == db_value.lower():
                return db_value
        
        # Partial match - check if user value contains db value or vice versa
        best_match = None
        best_score = 0
        
        for db_value in db_values:
            db_value_lower = db_value.lower()
            
            # Check if user input contains database value
            if db_value_lower in user_value_lower:
                score = len(db_value_lower) / len(user_value_lower)
                if score > best_score:
                    best_score = score
                    best_match = db_value
            
            # Check if database value contains user input
            elif user_value_lower in db_value_lower:
                score = len(user_value_lower) / len(db_value_lower)
                if score > best_score:
                    best_score = score
                    best_match = db_value
        
        # Return match if score is above threshold
        return best_match if best_score > 0.3 else None
    
    async def _retrieve_database_context(self) -> str:
        """Retrieve technical solution from database based on current slots."""
        try:
            # Only retrieve if we have some slots filled
            if not self.conversation_state.slots:
                return "No database context available - no technical information collected yet."
            
            print(f"🔍 Retrieving database context for slots: {self.conversation_state.slots}")
            
            # Call database service to retrieve single solution
            db_result = await self.db_service.retrieve_technical_solutions(self.conversation_state.slots)
            
            if not db_result.get("found") or not db_result.get("solution"):
                return "No matching technical solution found in database for current problem parameters."
            
            # Format single solution for prompt context
            solution = db_result.get("solution")
            context_parts = [
                "Found matching technical solution:",
                f"  - Operation: {solution.get('operation', 'N/A')}",
                f"  - Machine Type: {solution.get('machinetype', 'N/A')}",
                f"  - Defect: {solution.get('defect', 'N/A')}",
                f"  - Error: {solution.get('error', 'N/A')}",
                f"  - Root Cause: {solution.get('fishbone', 'N/A')}",
                f"  - Recommended Action: {solution.get('action', 'N/A')}"
            ]
            
            formatted_context = "\n".join(context_parts)
            print(f"✅ Retrieved database context: 1 solution found")
            
            return formatted_context
            
        except Exception as e:
            print(f"❌ Error retrieving database context: {e}")
            return f"Database retrieval error: {str(e)}"
    
    def _generate_intelligent_response(self, user_input: str, intent_analysis: Dict) -> str:
        """Generate contextually appropriate technical response."""
        try:
            phase = self._determine_conversation_phase(intent_analysis)
            self.conversation_state.current_phase = phase
            
            state_summary = {
                "collected_info": self.conversation_state.slots,
                "missing_info": self._get_missing_critical_slots(),
                "conversation_phase": phase.value,
                "turn_count": self.conversation_state.turn_count,
                "problem_severity": intent_analysis.get("problem_severity", "moderate"),
                "urgency": intent_analysis.get("urgency", "medium")
            }
            
            response = self.response_chain.invoke({
                "conversation_state": json.dumps(state_summary, indent=2),
                "user_input": user_input,
                "conversation_phase": phase.value
            })
            
            return response.strip()
            
        except Exception as e:
            print(f"❌ Error generating response: {e}")
            return self._generate_fallback_response()
    
    def _generate_fallback_response(self) -> str:
        """Generate fallback response when LLM fails."""
        missing = self._get_missing_critical_slots()
        if not missing:
            return "Perfect! I have all the information needed. Let me analyze the problem and provide a solution."
        
        # Generate dynamic questions with database values
        operations_list = ", ".join(self.technical_db["operations"][:5]) + "..."
        machine_types_list = ", ".join(self.technical_db["machine_types"][:8])
        defects_list = ", ".join(self.technical_db["defects"][:5]) + "..."
        errors_list = ", ".join(self.technical_db["errors"][:5]) + "..."
        
        slot_questions = {
            "operation": f"What manufacturing operation were you performing? (e.g., {operations_list})",
            "machine_type": f"What type of machine are you using? (e.g., {machine_types_list})",
            "defect": f"What type of defect are you observing? (e.g., {defects_list})",
            "error": f"What specific error or issue do you think is causing this problem? (e.g., {errors_list})"
        }
        
        next_question = slot_questions.get(missing[0], "Could you provide more details about the technical problem?")
        return next_question
    
    async def _generate_technical_solution(self) -> str:
        """Generate concise technical solution with database context."""
        try:
            problem_details = self.conversation_state.slots.copy()
            
            # Retrieve database context for final solution
            print(f"🔍 Retrieving database context for final solution: {problem_details}")
            database_context = await self._retrieve_database_context()
            
            # Store solved problem
            self.conversation_state.problem_count += 1
            problem_details["problem_id"] = f"PROB{self.conversation_state.problem_count:03d}"
            problem_details["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.conversation_state.solved_problems.append(problem_details)
            
            solution = self.solution_chain.invoke({
                "problem_details": json.dumps(problem_details, indent=2),
                "database_context": database_context
            })
            
            # Add post-solution message
            post_solution_msg = "\n\n🔧 Do you have any other technical problems I can help you solve, or do you need clarification on this solution?"
            
            return solution.strip() + post_solution_msg
            
        except Exception as e:
            print(f"❌ Error generating solution: {e}")
            return "✅ Based on the information provided, I recommend checking the machine settings and components. Please follow standard troubleshooting procedures.\n\n🔧 Do you have any other technical problems I can help with?"
    
    async def process_user_message(self, user_input: str) -> str:
        """Main method to process user input and generate technical response."""
        try:
            # Update conversation state
            self.conversation_state.turn_count += 1
            self.conversation_state.conversation_history.append(user_input)
            
            print(f"🔍 Processing user message: {user_input[:100]}...")
            print(f"📊 Turn count: {self.conversation_state.turn_count}")
            
        except Exception as e:
            print(f"❌ Error updating conversation state: {e}")
            return "I'm having trouble processing your message. Please try again."
        
        try:
            # 1. Analyze user intent
            context = self._get_conversation_context()
            print(f"🔍 Invoking intent chain with context: {context[:100]}...")
            
            intent_analysis = self.intent_chain.invoke({
                "user_input": user_input,
                "conversation_history": context
            })
            
            print(f"🧠 Intent Analysis: {intent_analysis}")
            print(f"🧠 Intent Analysis Type: {type(intent_analysis)}")
            
            # Handle new problem request in post-solution phase
            current_phase = self.conversation_state.current_phase
            intent = intent_analysis.intent.lower() if hasattr(intent_analysis, 'intent') else ""
            
            if current_phase in [ConversationPhase.POST_SOLUTION, ConversationPhase.COMPLETION]:
                if any(keyword in intent for keyword in ["new", "another", "different", "problem", "issue"]):
                    # Start new problem - reset slots but keep problem history
                    self.conversation_state.slots = {}
                    self.conversation_state.current_phase = ConversationPhase.NEW_PROBLEM
                    print("🆕 Starting new problem diagnosis")
            
            # 2. Extract slots from user input (only if in problem-solving phases)
            if current_phase not in [ConversationPhase.POST_SOLUTION]:
                print(f"🔍 Extracting slots from input...")
                extracted_slots = self._extract_slots_from_input(user_input)
                if extracted_slots:
                    self.conversation_state.slots.update(extracted_slots)
                    print(f"📝 Extracted: {extracted_slots}")
                else:
                    print(f"📝 No slots extracted")
            
            # 3. Determine next action based on phase and slots
            missing_slots = self._get_missing_critical_slots()
            
            if current_phase == ConversationPhase.POST_SOLUTION:
                # Handle post-solution interactions
                # Handle both dict and Pydantic objects
                intent_dict = intent_analysis.dict() if hasattr(intent_analysis, 'dict') else intent_analysis
                response = self._generate_intelligent_response(user_input, intent_dict)
            elif not missing_slots and current_phase not in [ConversationPhase.COMPLETION, ConversationPhase.POST_SOLUTION]:
                # All information collected - generate technical solution
                response = await self._generate_technical_solution()
                self.conversation_state.current_phase = ConversationPhase.COMPLETION
            else:
                # Generate intelligent response to continue problem diagnosis
                # Handle both dict and Pydantic objects
                intent_dict = intent_analysis.dict() if hasattr(intent_analysis, 'dict') else intent_analysis
                response = self._generate_intelligent_response(user_input, intent_dict)
            
            # Add response to conversation history
            self.conversation_state.conversation_history.append(response)
            
            return response
            
        except Exception as e:
            print(f"❌ PRODUCTION ERROR - Message Processing Failed")
            print(f"❌ Error: {str(e)}")
            print(f"❌ Error Type: {type(e).__name__}")
            print(f"❌ User Input: {user_input}")
            print(f"❌ Turn Count: {self.conversation_state.turn_count}")
            print(f"❌ Current Phase: {self.conversation_state.current_phase}")
            print(f"❌ Collected Slots: {self.conversation_state.slots}")
            
            import traceback
            print(f"❌ FULL TRACEBACK:")
            print(traceback.format_exc())
            print(f"❌ END TRACEBACK")
            
            # Log environment status
            try:
                from common.utils.llm_connections import required_vars
                print(f"❌ ENV CHECK - Deployment: {required_vars.get('AZURE_OPENAI_DEPLOYMENT', 'NOT SET')}")
                print(f"❌ ENV CHECK - Endpoint: {required_vars.get('AZURE_OPENAI_ENDPOINT', 'NOT SET')}")
                print(f"❌ ENV CHECK - API Version: {required_vars.get('AZURE_OPENAI_API_VERSION', 'NOT SET')}")
                print(f"❌ ENV CHECK - API Key: {'SET' if required_vars.get('AZURE_OPENAI_API_KEY') else 'NOT SET'}")
            except Exception as env_e:
                print(f"❌ ENV CHECK FAILED: {env_e}")
            
            # Provide a more helpful fallback response
            if self.conversation_state.turn_count <= 1:
                return "🔧 Welcome to Manufacturing Technical Support! I'm experiencing some technical issues, but I can still help. Please describe the manufacturing problem you're having - what operation were you performing and what type of issue occurred?"
            else:
                return "I'm having some technical difficulties with my advanced features, but I'm still here to help. Could you please tell me more about your manufacturing problem? What operation, machine type, and issue are you experiencing?"
    
    def get_conversation_summary(self) -> ConversationSummary:
        """Get current conversation state summary."""
        return ConversationSummary(
            collected_slots=self.conversation_state.slots,
            missing_slots=self._get_missing_critical_slots(),
            conversation_phase=self.conversation_state.current_phase.value,
            turn_count=self.conversation_state.turn_count,
            solved_problems=len(self.conversation_state.solved_problems),
            problem_count=self.conversation_state.problem_count
        )
    
    def reset_conversation(self):
        """Reset conversation state."""
        self.conversation_state = ConversationState()
    
    def start_new_problem(self):
        """Start a new problem diagnosis while preserving solution history."""
        # Keep solution history but reset current problem
        self.conversation_state.slots = {}
        self.conversation_state.current_phase = ConversationPhase.NEW_PROBLEM
        self.conversation_state.clarifications_needed = []
        print(f"🆕 Starting problem #{self.conversation_state.problem_count + 1}")
    
    def get_technical_database(self) -> Dict:
        """Get the technical database for reference."""
        return self.technical_db.copy()
    
    async def test_database_connection(self) -> bool:
        """Test the database connection and retrieval functionality."""
        try:
            print("🔍 Testing OCAP database connection...")
            is_connected = await self.db_service.test_connection()
            
            if is_connected:
                print("✅ Database connection test passed")
                
                # Test sample retrieval with minimal slots
                test_slots = {"operation": "Attach sleeve to body"}
                test_result = await self.db_service.retrieve_technical_solutions(test_slots)
                found = test_result.get('found', False)
                print(f"✅ Sample retrieval test: {'Solution found' if found else 'No solution found'}")
                
                return True
            else:
                print("❌ Database connection test failed")
                return False
                
        except Exception as e:
            print(f"❌ Database test error: {e}")
            return False
