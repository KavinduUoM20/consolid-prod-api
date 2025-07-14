"""
Very simple test for Mistral OCR
"""
from mistralai import Mistral
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

def test_simple_mistral():
    """Simple test with public PDF"""
    
    # Check if API key is set
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        print("❌ MISTRAL_API_KEY not set")
        return False
    
    try:
        # Initialize client
        client = Mistral(api_key=api_key)
        print("✅ Mistral client initialized successfully")
        
        # Test with public PDF
        print("🔄 Testing with public PDF...")
        
        ocr_response = client.ocr.process(
            model="mistral-ocr-latest",
            document={
                "type": "document_url",
                "document_url": "https://arxiv.org/pdf/2501.00663",
            },
        )
        
        print("✅ OCR request successful!")
        print(f"Response type: {type(ocr_response)}")
        
        # Check if we got pages
        if hasattr(ocr_response, "pages"):
            print(f"Number of pages: {len(ocr_response.pages)}")
            if ocr_response.pages:
                print("✅ First page content preview:")
                print(ocr_response.pages[0].markdown[:200] + "...")
        else:
            print("⚠️  No pages found in response")
            print(f"Response: {ocr_response}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Simple Mistral Test")
    print("=" * 30)
    
    success = test_simple_mistral()
    
    if success:
        print("✅ Test passed!")
    else:
        print("❌ Test failed!") 