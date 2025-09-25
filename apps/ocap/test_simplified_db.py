#!/usr/bin/env python3
"""
Test script for the simplified OCAP database retrieval approach.
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

async def test_simplified_database():
    """Test the simplified database approach."""
    try:
        from apps.ocap.services.technical_db_service import TechnicalDatabaseService
        
        print("🔧 Testing Simplified OCAP Database Retrieval")
        print("=" * 50)
        
        # Initialize service
        db_service = TechnicalDatabaseService()
        
        # Test 1: Connection test
        print("\n1. Testing database connection...")
        is_connected = await db_service.test_connection()
        
        if not is_connected:
            print("❌ Database connection failed - stopping tests")
            return False
        
        # Test 2: Simple query with partial slots
        print("\n2. Testing query with operation only...")
        test_slots_1 = {
            "operation": "Attach sleeve"
        }
        
        result_1 = await db_service.retrieve_technical_solutions(test_slots_1)
        print(f"   Found: {result_1.get('found', False)}")
        if result_1.get('found'):
            solution = result_1.get('solution')
            print(f"   Operation: {solution.get('operation')}")
            print(f"   Action: {solution.get('action')}")
        
        # Test 3: Query with multiple slots  
        print("\n3. Testing query with multiple slots...")
        test_slots_2 = {
            "operation": "Attach sleeve",
            "machine_type": "OL",
            "defect": "Broken stitch"
        }
        
        result_2 = await db_service.retrieve_technical_solutions(test_slots_2)
        print(f"   Found: {result_2.get('found', False)}")
        if result_2.get('found'):
            solution = result_2.get('solution')
            print(f"   Operation: {solution.get('operation')}")
            print(f"   Machine Type: {solution.get('machinetype')}")
            print(f"   Defect: {solution.get('defect')}")
            print(f"   Action: {solution.get('action')}")
        
        # Test 4: Query that should not match
        print("\n4. Testing query with non-matching slots...")
        test_slots_3 = {
            "operation": "NonExistentOperation",
            "machine_type": "NonExistentMachine"
        }
        
        result_3 = await db_service.retrieve_technical_solutions(test_slots_3)
        print(f"   Found: {result_3.get('found', False)}")
        
        print("\n✅ Simplified database tests completed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = asyncio.run(test_simplified_database())
    sys.exit(0 if success else 1)
