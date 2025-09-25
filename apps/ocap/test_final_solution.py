#!/usr/bin/env python3
"""
Test script to demonstrate the updated final solution generation with database context.
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

async def test_final_solution_with_database():
    """Test the final solution generation with database integration."""
    try:
        from apps.ocap.services.manufacturing_assistant import ManufacturingTechnicalAssistant
        
        print("🔧 Testing Final Solution Generation with Database Context")
        print("=" * 60)
        
        # Initialize assistant
        assistant = ManufacturingTechnicalAssistant()
        
        # Test database connection first
        print("\n1. Testing database connection...")
        db_connected = await assistant.test_database_connection()
        
        if not db_connected:
            print("❌ Database connection failed - stopping test")
            return False
        
        # Simulate a complete problem scenario
        print("\n2. Simulating complete problem diagnosis...")
        
        # Set up slots as if user provided all information
        assistant.conversation_state.slots = {
            "operation": "Attach sleeve to body",
            "machine_type": "OL", 
            "defect": "Broken stitch",
            "error": "Throat plate damage"
        }
        
        print(f"   Collected slots: {assistant.conversation_state.slots}")
        
        # Test database retrieval for these slots
        print("\n3. Testing database retrieval...")
        db_context = await assistant._retrieve_database_context()
        print(f"   Database context preview: {db_context[:100]}...")
        
        # Generate final technical solution
        print("\n4. Generating final technical solution...")
        solution = await assistant._generate_technical_solution()
        
        print("\n" + "="*60)
        print("GENERATED SOLUTION:")
        print("="*60)
        print(solution)
        print("="*60)
        
        print("\n✅ Final solution generation test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = asyncio.run(test_final_solution_with_database())
    sys.exit(0 if success else 1)
