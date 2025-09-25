from typing import Dict, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, text
from apps.ocap.models.technical_data import OCAPTechnicalData
from apps.ocap.db import AsyncSessionLocal

class TechnicalDatabaseService:
    """Simplified service for retrieving technical solutions from the OCAP database."""
    
    def __init__(self):
        self.session_factory = AsyncSessionLocal
    
    async def retrieve_technical_solutions(self, slots: Dict[str, Any]) -> Dict[str, Any]:
        """
        Retrieve a single technical solution using simple ILIKE matching with LIMIT 1.
        
        Args:
            slots: Dictionary containing extracted technical slots
                  (operation, machine_type, defect, error)
        
        Returns:
            Dictionary containing the matched solution and metadata
        """
        async with self.session_factory() as session:
            try:
                # Build query conditions based on available slots
                conditions = []
                
                # Map slot names to database column names  
                slot_mapping = {
                    "operation": "operation",
                    "machine_type": "machinetype", 
                    "defect": "defect",
                    "error": "error"
                }
                
                print(f"🔍 Building query conditions for slots: {slots}")
                
                # Build WHERE conditions with ILIKE for partial text matching
                for slot_name, slot_value in slots.items():
                    if slot_value and slot_name in slot_mapping:
                        db_column = slot_mapping[slot_name]
                        conditions.append(
                            getattr(OCAPTechnicalData, db_column).ilike(f"%{slot_value}%")
                        )
                        print(f"  - Added condition: {db_column} ILIKE '%{slot_value}%'")
                
                if not conditions:
                    print("⚠️ No valid conditions built from slots")
                    return {
                        "solution": None,
                        "query_info": {"conditions": "No valid slots provided"},
                        "found": False
                    }
                
                # Simple query with AND conditions and LIMIT 1
                query = select(OCAPTechnicalData).where(and_(*conditions)).limit(1)
                print(f"🔍 Executing query with {len(conditions)} conditions")
                
                result = await session.execute(query)
                solution = result.scalars().first()
                
                if solution:
                    print(f"✅ Found matching solution: {solution.operation}")
                    return {
                        "solution": solution.to_solution_dict(),
                        "query_info": {
                            "conditions_count": len(conditions),
                            "slots_used": list(slots.keys())
                        },
                        "found": True
                    }
                else:
                    print("⚠️ No matching solution found")
                    return {
                        "solution": None,
                        "query_info": {
                            "conditions_count": len(conditions),
                            "slots_used": list(slots.keys())
                        },
                        "found": False
                    }
                
            except Exception as e:
                print(f"❌ Database retrieval error: {e}")
                return {
                    "solution": None,
                    "query_info": {"error": str(e)},
                    "found": False
                }
    
    async def test_connection(self) -> bool:
        """Test database connection."""
        try:
            async with self.session_factory() as session:
                # Simple query to test connection
                result = await session.execute(text("SELECT COUNT(*) FROM ocap"))
                count = result.scalar()
                print(f"✅ OCAP database connection successful. Total records: {count}")
                return True
        except Exception as e:
            print(f"❌ OCAP database connection failed: {e}")
            return False
