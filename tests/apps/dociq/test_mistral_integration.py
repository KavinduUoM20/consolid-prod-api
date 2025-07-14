"""
Integration test for Mistral parser with extraction service
"""
import asyncio
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import the extraction service
from apps.dociq.services.extraction_service import ExtractionService
from apps.dociq.db import get_dociq_session


async def test_mistral_integration():
    """Test the integration of Mistral parser with extraction service"""
    
    # Check if MISTRAL_API_KEY is set
    if not os.getenv("MISTRAL_API_KEY"):
        print("⚠️  MISTRAL_API_KEY not set. Using mock for testing.")
        use_mock = True
    else:
        print("✅ MISTRAL_API_KEY found. Using real API for testing.")
        use_mock = False
    
    # Mock file data
    file_bytes = b"mock pdf content for testing"
    filename = "test_document.pdf"
    file_size = len(file_bytes)
    
    # Mock the Mistral OCR response
    mock_page = MagicMock()
    mock_page.markdown = """# Test Document

## Extracted Content
This is a test document processed by Mistral OCR.

### Key Information
- **Document Type**: PDF
- **Processing Date**: 2024-01-01
- **Confidence Score**: 95.2%

### Sample Text
Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.

---
*Processed by Mistral OCR*"""

    mock_ocr_response = MagicMock()
    mock_ocr_response.pages = [mock_page]
    
    try:
        # Get database session
        async for session in get_dociq_session():
            extraction_service = ExtractionService(session)
            
            if use_mock:
                # Use mock for testing
                with patch('common.utils.parser.client') as mock_client:
                    mock_client.ocr.process.return_value = mock_ocr_response
                    
                    print("🔄 Testing extraction service with mock Mistral OCR API...")
                    extraction, document = await extraction_service.create_extraction_with_document(
                        file_bytes=file_bytes,
                        filename=filename,
                        file_size=file_size
                    )
            else:
                # Use real API
                print("🔄 Testing extraction service with real Mistral OCR API...")
                extraction, document = await extraction_service.create_extraction_with_document(
                    file_bytes=file_bytes,
                    filename=filename,
                    file_size=file_size
                )
            
            # Print results
            print(f"✅ Extraction created successfully!")
            print(f"   - Extraction ID: {extraction.id}")
            print(f"   - Document ID: {document.id}")
            print(f"   - Status: {extraction.status}")
            print(f"   - Current Step: {extraction.current_step}")
            print(f"   - Document Name: {document.doc_name}")
            print(f"   - Document Type: {document.doc_type}")
            print(f"   - Document Size: {document.doc_size} bytes")
            
            # Check if markdown file was created
            if extraction.status == "extracted":
                print("✅ Document processing successful!")
            else:
                print("❌ Document processing failed!")
            
            break
            
    except Exception as e:
        print(f"❌ Error during integration test: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("🚀 Starting Mistral Integration Test")
    print("=" * 50)
    
    # Run the async test
    asyncio.run(test_mistral_integration())
    
    print("=" * 50)
    print("🏁 Integration test completed!") 