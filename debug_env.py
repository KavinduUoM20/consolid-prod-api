#!/usr/bin/env python3
"""
Debug script to check environment and API configuration
"""
import os
import sys
import asyncio
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def check_environment():
    """Check environment variables and configuration"""
    print("=== Environment Check ===")
    
    # Check CORS configuration
    print("\n--- CORS Configuration ---")
    cors_origins = os.getenv("DOCIQ_CORS_ORIGINS", "Not set")
    print(f"DOCIQ_CORS_ORIGINS: {cors_origins}")
    
    # Check database configuration
    print("\n--- Database Configuration ---")
    db_url = os.getenv("DOCIQ_DATABASE_URL", "Not set")
    print(f"DOCIQ_DATABASE_URL: {'Set' if db_url != 'Not set' else 'Not set'}")
    
    # Check API keys
    print("\n--- API Keys ---")
    mistral_key = os.getenv("MISTRAL_API_KEY", "Not set")
    azure_key = os.getenv("AZURE_OPENAI_API_KEY", "Not set")
    print(f"MISTRAL_API_KEY: {'Set' if mistral_key != 'Not set' else 'Not set'}")
    print(f"AZURE_OPENAI_API_KEY: {'Set' if azure_key != 'Not set' else 'Not set'}")
    
    # Check other important variables
    print("\n--- Other Configuration ---")
    debug_mode = os.getenv("DEBUG", "Not set")
    app_name = os.getenv("APP_NAME", "Not set")
    print(f"DEBUG: {debug_mode}")
    print(f"APP_NAME: {app_name}")

def check_cors_config():
    """Check CORS configuration from settings"""
    try:
        from apps.dociq.config import get_dociq_settings
        settings = get_dociq_settings()
        print("\n=== CORS Settings from Config ===")
        print(f"CORS_ORIGINS: {settings.CORS_ORIGINS}")
        print(f"CORS_ALLOW_CREDENTIALS: {settings.CORS_ALLOW_CREDENTIALS}")
        print(f"CORS_ALLOW_METHODS: {settings.CORS_ALLOW_METHODS}")
        print(f"CORS_ALLOW_HEADERS: {settings.CORS_ALLOW_HEADERS}")
        
        # Check if production domain is included
        production_domain = "https://consolidator-ai.site"
        if production_domain in settings.CORS_ORIGINS:
            print(f"✅ Production domain '{production_domain}' is included in CORS_ORIGINS")
        else:
            print(f"❌ Production domain '{production_domain}' is NOT included in CORS_ORIGINS")
            
    except Exception as e:
        print(f"Error checking CORS config: {e}")

def check_api_routes():
    """Check if API routes are properly configured"""
    try:
        from main import app
        print("\n=== API Routes Check ===")
        
        # Get all routes
        routes = []
        for route in app.routes:
            if hasattr(route, 'path'):
                routes.append(route.path)
        
        # Check for specific routes
        target_routes = [
            "/api/v1/dociq/extractions/",
            "/api/v1/dociq/hello",
            "/docs"
        ]
        
        for route in target_routes:
            if route in routes:
                print(f"✅ Route '{route}' found")
            else:
                print(f"❌ Route '{route}' NOT found")
                
        print(f"\nTotal routes found: {len(routes)}")
        
    except Exception as e:
        print(f"Error checking API routes: {e}")

async def test_database_connection():
    """Test database connection"""
    try:
        from apps.dociq.db import engine
        print("\n=== Database Connection Test ===")
        
        async with engine.begin() as conn:
            result = await conn.execute("SELECT 1")
            print("✅ Database connection successful")
            
    except Exception as e:
        print(f"❌ Database connection failed: {e}")

def main():
    """Main debug function"""
    print("🔍 API Debug Environment Check")
    print("=" * 50)
    
    check_environment()
    check_cors_config()
    check_api_routes()
    
    # Test database connection
    try:
        asyncio.run(test_database_connection())
    except Exception as e:
        print(f"❌ Database test failed: {e}")
    
    print("\n" + "=" * 50)
    print("Debug check complete!")

if __name__ == "__main__":
    main() 