#!/usr/bin/env python3
"""
Test script to verify API endpoints and CORS configuration
"""
import requests
import json
import sys

def test_api_endpoints():
    
    # Base URL - change this to your actual API URL
    base_url = "https://api.consolidator-ai.site"
    
    print("🔍 Testing API Endpoints")
    print("=" * 50)
    
    # Test endpoints
    endpoints = [
        "/api/v1/dociq/",
        "/api/v1/dociq/hello",
        "/api/v1/dociq/health",
        "/docs"
    ]
    
    for endpoint in endpoints:
        url = base_url + endpoint
        print(f"\nTesting: {url}")
        
        try:
            response = requests.get(url, timeout=10)
            print(f"Status: {response.status_code}")
            print(f"Headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                print("✅ Endpoint working")
                if response.headers.get('content-type', '').startswith('application/json'):
                    try:
                        data = response.json()
                        print(f"Response: {json.dumps(data, indent=2)}")
                    except:
                        print("Response: (non-JSON)")
                else:
                    print("Response: (non-JSON content)")
            else:
                print("❌ Endpoint failed")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
    
    # Test CORS headers specifically
    print(f"\n{'='*50}")
    print("🔍 Testing CORS Headers")
    print("=" * 50)
    
    cors_test_url = base_url + "/api/v1/dociq/health"
    
    try:
        # Test with Origin header
        headers = {
            'Origin': 'https://consolidator-ai.site',
            'Access-Control-Request-Method': 'GET',
            'Access-Control-Request-Headers': 'Content-Type'
        }
        
        response = requests.options(cors_test_url, headers=headers, timeout=10)
        print(f"OPTIONS request status: {response.status_code}")
        print(f"CORS headers:")
        
        cors_headers = [
            'Access-Control-Allow-Origin',
            'Access-Control-Allow-Methods', 
            'Access-Control-Allow-Headers',
            'Access-Control-Allow-Credentials'
        ]
        
        for header in cors_headers:
            value = response.headers.get(header, 'Not set')
            print(f"  {header}: {value}")
            
        # Check if production domain is allowed
        allow_origin = response.headers.get('Access-Control-Allow-Origin', '')
        if 'consolidator-ai.site' in allow_origin or allow_origin == '*':
            print("✅ CORS configured for production domain")
        else:
            print("❌ CORS NOT configured for production domain")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ CORS test failed: {e}")

def test_file_upload():
    """Test file upload endpoint"""
    print(f"\n{'='*50}")
    print("🔍 Testing File Upload Endpoint")
    print("=" * 50)
    
    base_url = "https://api.consolidator-ai.site"
    upload_url = base_url + "/api/v1/dociq/extractions/"
    
    # Create a simple test file
    test_content = b"This is a test file content"
    
    try:
        files = {'file': ('test.txt', test_content, 'text/plain')}
        headers = {'Origin': 'https://consolidator-ai.site'}
        
        response = requests.post(upload_url, files=files, headers=headers, timeout=30)
        print(f"Upload status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        if response.status_code in [200, 201]:
            print("✅ Upload endpoint working")
            try:
                data = response.json()
                print(f"Response: {json.dumps(data, indent=2)}")
            except:
                print("Response: (non-JSON)")
        else:
            print("❌ Upload endpoint failed")
            print(f"Response: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Upload test failed: {e}")

if __name__ == "__main__":
    test_api_endpoints()
    test_file_upload()
    print(f"\n{'='*50}")
    print("Test complete!") 
