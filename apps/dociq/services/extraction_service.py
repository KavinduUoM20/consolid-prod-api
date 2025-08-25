from typing import Optional, Tuple, List
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import os
import shutil
from pathlib import Path
import redis

from apps.dociq.models.document import Document
from apps.dociq.models.extraction import Extraction
from apps.dociq.llm.prompt_utils import process_content_mapping
from common.utils.parser import parse_with_mistral_from_bytes

# Configure upload directory
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Configure Redis connection with environment variable fallbacks
REDIS_HOST = os.getenv('REDIS_HOST', 'big-bear-redis')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_USERNAME = os.getenv('REDIS_USERNAME', 'default')
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', '12345')

try:
    REDIS_CLIENT = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        username=REDIS_USERNAME,
        password=REDIS_PASSWORD,
        decode_responses=False,  # Keep as bytes for file storage
        socket_connect_timeout=5,
        socket_timeout=5
    )
    # Test the connection
    REDIS_CLIENT.ping()
    REDIS_AVAILABLE = True
    print(f"Redis connection established successfully to {REDIS_HOST}:{REDIS_PORT}")
except Exception as e:
    print(f"Redis connection failed: {e}")
    print("Files will only be saved to disk")
    REDIS_AVAILABLE = False
    REDIS_CLIENT = None


class ExtractionService:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    def process_cluster_customer_headers(self, cluster: str, customer: str, extraction_id: str, document_id: str):
        """
        Background task to process X-Cluster and X-Customer headers
        
        Args:
            cluster: Value from X-Cluster header
            customer: Value from X-Customer header  
            extraction_id: ID of the created extraction
            document_id: ID of the created document
        """
        print(f"=== Background Task Processing ===")
        print(f"Cluster: {cluster}")
        print(f"Customer: {customer}")
        print(f"Extraction ID: {extraction_id}")
        print(f"Document ID: {document_id}")
        print(f"=== End Background Task ===")
        
        # Add your actual background processing logic here
        # Examples:
        # - Send analytics/tracking data
        # - Update external systems
        # - Log to specialized systems
        # - Trigger notifications
        # - Update customer-specific configurations

    async def create_extraction_with_document(
        self, 
        file_bytes: bytes, 
        filename: str,
        file_size: int,
        cluster: Optional[str] = None,
        customer: Optional[str] = None
    ) -> Tuple[Extraction, Document]:
        """
        Create a document and extraction record, process with Mistral
        
        Args:
            file_bytes: Uploaded file bytes
            filename: Original filename
            file_size: File size in bytes
            cluster: Optional cluster identifier
            customer: Optional customer identifier
            
        Returns:
            Tuple of (Extraction, Document) records
        """
        # Determine document type from filename
        doc_type = self._get_document_type(filename)
        
        # Save file to disk
        file_path = self._save_file(file_bytes, filename)
        
        # Create document record
        document = Document(
            doc_name=filename,
            doc_size=file_size,
            doc_type=doc_type,
            doc_path=str(file_path)
        )
        self.session.add(document)
        await self.session.flush()  # Get the ID without committing
        
        # Create extraction record
        extraction = Extraction(
            document_id=document.id,
            current_step="document_upload",
            status="uploaded",
            cluster=cluster,
            customer=customer
        )
        self.session.add(extraction)
        await self.session.flush()  # Get the ID without committing
        
        # Process with Mistral
        markdown_content = parse_with_mistral_from_bytes(file_bytes, filename)
        
        if markdown_content:
            print("=" * 50)
            print("MISTRAL PARSING RESULT:")
            print("=" * 50)
            print(markdown_content)
            print("=" * 50)
            
            # Save markdown content to a predictable location based on document ID
            outputs_dir = Path("outputs")
            outputs_dir.mkdir(exist_ok=True)
            md_filename = f"{document.id}.md"
            md_file_path = outputs_dir / md_filename
            
            try:
                with open(md_file_path, 'w', encoding='utf-8') as f:
                    f.write(markdown_content)
                print(f"Markdown content saved to: {md_file_path}")
            except Exception as e:
                print(f"Error saving markdown content: {e}")
            
            # Update extraction status
            extraction.status = "extracted"
            extraction.current_step = "extraction_complete"
        else:
            print("Mistral parsing failed or returned no content")
            extraction.status = "extraction_failed"
            extraction.current_step = "extraction_failed"
        
        # Commit both records
        await self.session.commit()
        await self.session.refresh(document)
        await self.session.refresh(extraction)
        
        return extraction, document

    def _get_document_type(self, filename: str) -> str:
        """Determine document type from filename extension"""
        extension = filename.lower().split('.')[-1] if '.' in filename else ''
        
        if extension in ['pdf']:
            return 'pdf'
        elif extension in ['xlsx', 'xls']:
            return 'excel'
        elif extension in ['doc', 'docx']:
            return 'doc' if extension == 'doc' else 'docx'
        elif extension in ['txt']:
            return 'txt'
        elif extension in ['jpg', 'jpeg', 'png', 'gif']:
            return 'image'
        else:
            return 'pdf'  # Default to PDF

    def _save_file(self, file_bytes: bytes, filename: str) -> Path:
        """Save uploaded file to disk and Redis"""
        # Create unique filename to avoid conflicts
        unique_filename = f"{uuid.uuid4()}_{filename}"
        file_path = UPLOAD_DIR / unique_filename
        
        # Save to disk
        with open(file_path, "wb") as buffer:
            buffer.write(file_bytes)
        
        # Save to Redis
        if REDIS_AVAILABLE and REDIS_CLIENT:
            try:
                redis_key = f"file:{unique_filename}"
                REDIS_CLIENT.set(redis_key, file_bytes)
                print(f"File saved to Redis with key: {redis_key}")
            except Exception as e:
                print(f"Error saving file to Redis: {e}")
        else:
            print(f"Redis not available, file '{unique_filename}' saved only to disk.")
        
        return file_path

    async def get_extraction_by_id(self, extraction_id: uuid.UUID) -> Optional[Extraction]:
        """Get extraction by ID"""
        result = await self.session.execute(
            select(Extraction).where(Extraction.id == extraction_id)
        )
        return result.scalar_one_or_none()

    async def get_all_extractions(self, limit: Optional[int] = None, offset: Optional[int] = None) -> List[Extraction]:
        """Get all extractions with optional pagination"""
        query = select(Extraction).order_by(Extraction.created_at.desc())
        
        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)
            
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_extraction_with_document(self, extraction_id: uuid.UUID) -> Optional[Extraction]:
        """Get extraction with document relationship loaded"""
        result = await self.session.execute(
            select(Extraction).where(Extraction.id == extraction_id)
        )
        extraction = result.scalar_one_or_none()
        
        if extraction:
            # Load the document relationship
            await self.session.refresh(extraction, attribute_names=['document'])
        
        return extraction

    async def update_extraction_template(self, extraction_id: uuid.UUID, template_id: uuid.UUID) -> Optional[Extraction]:
        """
        Update the template_id of an extraction record
        
        Args:
            extraction_id: UUID of the extraction to update
            template_id: UUID of the template to assign
            
        Returns:
            Updated Extraction record or None if not found
        """
        # Get the extraction record
        extraction = await self.get_extraction_by_id(extraction_id)
        
        if not extraction:
            return None
        
        # Update the template_id and current_step
        extraction.template_id = template_id
        extraction.current_step = "template_selected"
        # updated_at will be automatically updated due to onupdate=datetime.utcnow
        
        # Commit the changes
        await self.session.commit()
        await self.session.refresh(extraction)
        
        return extraction

    async def map_extraction(self, extraction_id: uuid.UUID):
        """
        Map extraction content to template fields
        
        Args:
            extraction_id: UUID of the extraction to map
            
        Returns:
            Mapping results
        """
        # Get extraction by ID
        extraction = await self.get_extraction_by_id(extraction_id)
        
        if not extraction:
            raise ValueError(f"Extraction {extraction_id} not found")
        
        # Check if template_id is set
        if not extraction.template_id:
            raise ValueError(f"Extraction {extraction_id} has no template assigned")
        
        # Extract document_id and template_id from extraction object
        document_id = extraction.document_id
        template_id = extraction.template_id
        
        # Call function in prompt_utils.py with document_id, template_id, and session
        target_mapping = await process_content_mapping(document_id, template_id, self.session)
        
        # Save the target mapping to the database
        self.session.add(target_mapping)
        await self.session.flush()  # Get the ID without committing
        
        # Update the extraction record with target_mapping_id and current_step
        extraction.target_mapping_id = target_mapping.id
        extraction.current_step = "target_mapped"
        extraction.status = "mapped"
        
        # Commit all changes
        await self.session.commit()
        await self.session.refresh(extraction)
        await self.session.refresh(target_mapping)
        
        return target_mapping 