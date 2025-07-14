"""
Test cases for Mistral parser functionality
"""
import pytest
import os
from unittest.mock import patch, MagicMock
from common.utils.parser import parse_with_mistral_from_bytes


class TestMistralParser:
    """Test cases for Mistral document parser"""
    
    def test_parse_with_mistral_from_bytes_success(self):
        """Test successful parsing with mock Mistral OCR response"""
        # Mock file bytes
        file_bytes = b"mock pdf content"
        filename = "test_document.pdf"
        
        # Mock the Mistral OCR response
        mock_page = MagicMock()
        mock_page.markdown = "# Test Document\n\nThis is test content extracted by Mistral OCR."
        
        mock_ocr_response = MagicMock()
        mock_ocr_response.pages = [mock_page]
        
        with patch('common.utils.parser.client') as mock_client:
            mock_client.ocr.process.return_value = mock_ocr_response
            
            # Test the parser
            result = parse_with_mistral_from_bytes(file_bytes, filename)
            
            # Verify the result
            assert result is not None
            assert result.endswith('.md')
            
            # Verify the file was created
            assert os.path.exists(result)
            
            # Clean up
            if os.path.exists(result):
                os.remove(result)
    
    def test_parse_with_mistral_from_bytes_failure(self):
        """Test parsing failure handling"""
        file_bytes = b"mock content"
        filename = "test_document.pdf"
        
        with patch('common.utils.parser.client') as mock_client:
            mock_client.ocr.process.side_effect = Exception("API Error")
            
            # Test the parser
            result = parse_with_mistral_from_bytes(file_bytes, filename)
            
            # Verify the result is None on failure
            assert result is None
    
    def test_parse_with_mistral_from_bytes_no_api_key(self):
        """Test behavior when MISTRAL_API_KEY is not set"""
        file_bytes = b"mock content"
        filename = "test_document.pdf"
        
        # Temporarily remove the API key
        original_key = os.environ.get('MISTRAL_API_KEY')
        if 'MISTRAL_API_KEY' in os.environ:
            del os.environ['MISTRAL_API_KEY']
        
        try:
            # Test the parser
            result = parse_with_mistral_from_bytes(file_bytes, filename)
            
            # Should handle missing API key gracefully
            assert result is None
        finally:
            # Restore the API key
            if original_key:
                os.environ['MISTRAL_API_KEY'] = original_key
    
    def test_parse_with_mistral_from_bytes_different_file_types(self):
        """Test parsing different file types"""
        test_cases = [
            ("test.pdf", "application/pdf"),
            ("test.jpg", "image/jpeg"),
            ("test.png", "image/png"),
            ("test.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        ]
        
        for filename, mime_type in test_cases:
            file_bytes = b"mock content"
            
            # Mock the Mistral OCR response
            mock_page = MagicMock()
            mock_page.markdown = f"# {filename}\n\nTest content."
            
            mock_ocr_response = MagicMock()
            mock_ocr_response.pages = [mock_page]
            
            with patch('common.utils.parser.client') as mock_client:
                mock_client.ocr.process.return_value = mock_ocr_response
                
                # Test the parser
                result = parse_with_mistral_from_bytes(file_bytes, filename, mime_type)
                
                # Verify the result
                assert result is not None
                assert result.endswith('.md')
                
                # Clean up
                if os.path.exists(result):
                    os.remove(result)


if __name__ == "__main__":
    pytest.main([__file__]) 