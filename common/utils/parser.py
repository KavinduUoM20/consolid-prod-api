"""
Mistral OCR parser for document extraction
"""
import base64
import uuid
import os
from pathlib import Path
from typing import Optional
from fastapi import UploadFile
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import Mistral client
from mistralai import Mistral

# Initialize Mistral client
client = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))


def parse_with_mistral(file: UploadFile) -> str:
    """
    Extracts content from an uploaded file (PDF or Image) using Mistral OCR.
    - Reads file bytes
    - Encodes the file in base64
    - Constructs Mistral-compatible payload depending on file type
    - Processes it and returns Markdown
    - Saves the output Markdown to `outputs/{uuid}.md`
    - Returns the path to the saved `.md` file
    """
    try:
        # Read file bytes
        file_bytes = file.file.read()
        encoded = base64.b64encode(file_bytes).decode("utf-8")
        
        # Determine file type from filename and content
        filename = file.filename.lower()
        mime_type = file.content_type or "application/octet-stream"
        
        # Override MIME type based on file extension for better compatibility
        if filename.endswith('.pdf'):
            mime_type = "application/pdf"
        elif filename.endswith(('.jpg', '.jpeg')):
            mime_type = "image/jpeg"
        elif filename.endswith('.png'):
            mime_type = "image/png"
        elif filename.endswith('.gif'):
            mime_type = "image/gif"
        elif filename.endswith(('.doc', '.docx')):
            mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        elif filename.endswith(('.xls', '.xlsx')):
            mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        elif filename.endswith('.txt'):
            mime_type = "text/plain"

        # Determine payload type based on file type
        if "pdf" in mime_type.lower():
            document = {
                "type": "document_url",
                "document_url": f"data:application/pdf;base64,{encoded}"
            }
            file_type = "PDF"
        elif any(img_type in mime_type.lower() for img_type in ["image", "jpg", "jpeg", "png", "gif"]):
            document = {
                "type": "image_url",
                "image_url": f"data:{mime_type};base64,{encoded}"
            }
            file_type = "Image"
        else:
            # Default to document_url for other types
            document = {
                "type": "document_url",
                "document_url": f"data:{mime_type};base64,{encoded}"
            }
            file_type = "Document"

        print(f"Processing {file_type} file: {file.filename}")
        print(f"File size: {len(file_bytes)} bytes")
        print(f"MIME type: {mime_type}")

        # Use Mistral OCR API
        ocr_response = client.ocr.process(
            model="mistral-ocr-latest",
            document=document
        )

        # Extract markdown content from OCR response
        if hasattr(ocr_response, "pages"):
            pages = ocr_response.pages
        elif isinstance(ocr_response, list):
            pages = ocr_response
        else:
            raise Exception("No pages found in OCR result")

        # Combine all pages into markdown
        markdown = "\n\n".join(page.markdown for page in pages)

        # Create outputs directory
        output_dir = Path("outputs")
        output_dir.mkdir(exist_ok=True)

        # Save markdown to file
        output_filename = f"{uuid.uuid4()}.md"
        output_path = output_dir / output_filename

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(markdown)

        print(f"Markdown saved to: {output_path}")
        return str(output_path)

    except Exception as e:
        print(f"Error parsing document with Mistral: {e}")
        return None


def parse_with_mistral_from_bytes(file_bytes: bytes, filename: str, mime_type: str = None) -> Optional[str]:
    """
    Alternative function to parse file bytes (useful for testing)
    """
    try:
        # Create a mock UploadFile object
        class MockFile:
            def __init__(self, file_bytes):
                self.file_bytes = file_bytes
            
            def read(self):
                return self.file_bytes
        
        class MockUploadFile:
            def __init__(self, file_bytes, filename, content_type):
                self.file_bytes = file_bytes
                self.filename = filename
                self.content_type = content_type
                self.file = MockFile(file_bytes)

        mock_file = MockUploadFile(file_bytes, filename, mime_type)
        return parse_with_mistral(mock_file)

    except Exception as e:
        print(f"Error parsing document bytes with Mistral: {e}")
        return None 