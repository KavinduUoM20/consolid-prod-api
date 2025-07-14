"""
Simple test to verify Mistral client is working
"""
from mistralai import Mistral
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

def test_mistral_client():
    """Test if Mistral client can be initialized and used"""
    
    # Check if API key is set
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        print("❌ MISTRAL_API_KEY not set")
        return False
    
    try:
        # Initialize client
        client = Mistral(api_key=api_key)
        print("✅ Mistral client initialized successfully")
        
        # Test OCR functionality with a public PDF
        print("🔄 Testing Mistral OCR API with public PDF...")
        
        ocr_response = client.ocr.process(
            model="mistral-ocr-latest",
            document={
                "type": "document_url",
                "document_url": "https://arxiv.org/pdf/2501.00663",
            },
        )
        
        print(f"✅ Mistral OCR API test successful")
        print(f"Response type: {type(ocr_response)}")
        
        # Print some basic info about the response
        if hasattr(ocr_response, "pages"):
            print(f"Number of pages: {len(ocr_response.pages)}")
            if ocr_response.pages:
                first_page = ocr_response.pages[0]
                print(f"First page markdown preview: {first_page.markdown[:100]}...")
        elif isinstance(ocr_response, list):
            print(f"Number of pages: {len(ocr_response)}")
            if ocr_response:
                first_page = ocr_response[0]
                print(f"First page markdown preview: {first_page.markdown[:100]}...")
        else:
            print(f"Response structure: {ocr_response}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing Mistral client: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing Mistral Client")
    print("=" * 40)
    
    success = test_mistral_client()
    
    if success:
        print("✅ All tests passed!")
    else:
        print("❌ Tests failed!") 