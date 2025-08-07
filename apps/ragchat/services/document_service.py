from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime
from typing import List, Optional
import os

from apps.ragchat.models import Document
from apps.ragchat.schemas.document import DocumentCreate, DocumentResponse

class DocumentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_document(self, document_data: DocumentCreate) -> DocumentResponse:
        """Create a new document record"""
        document = Document(
            filename=document_data.filename,
            file_path=document_data.file_path,
            file_size=document_data.file_size,
            file_type=document_data.file_type,
            title=document_data.title,
            description=document_data.description,
            user_id=document_data.user_id
        )
        self.db.add(document)
        await self.db.commit()
        await self.db.refresh(document)
        return DocumentResponse.from_orm(document)

    async def get_document(self, document_id: str) -> Optional[DocumentResponse]:
        """Get a specific document"""
        result = await self.db.execute(
            select(Document).where(Document.id == document_id)
        )
        document = result.scalar_one_or_none()
        return DocumentResponse.from_orm(document) if document else None

    async def list_documents(self, user_id: str = None) -> List[DocumentResponse]:
        """List all documents"""
        query = select(Document)
        if user_id:
            query = query.where(Document.user_id == user_id)
        query = query.order_by(Document.created_at.desc())
        
        result = await self.db.execute(query)
        documents = result.scalars().all()
        return [DocumentResponse.from_orm(doc) for doc in documents]

    async def delete_document(self, document_id: str) -> bool:
        """Delete a document"""
        # Get document first
        result = await self.db.execute(
            select(Document).where(Document.id == document_id)
        )
        document = result.scalar_one_or_none()
        if not document:
            return False
        
        # Delete file from filesystem
        if os.path.exists(document.file_path):
            os.remove(document.file_path)
        
        # Delete from database
        await self.db.delete(document)
        await self.db.commit()
        return True

    async def process_document(self, document_id: str) -> bool:
        """Process a document for RAG (vectorize and index)"""
        # Get document
        result = await self.db.execute(
            select(Document).where(Document.id == document_id)
        )
        document = result.scalar_one_or_none()
        if not document:
            return False
        
        # Update processing status
        await self.db.execute(
            update(Document)
            .where(Document.id == document_id)
            .values(
                processing_status="processing",
                updated_at=datetime.utcnow()
            )
        )
        await self.db.commit()
        
        # TODO: Implement actual document processing
        # This would include:
        # 1. Text extraction from document
        # 2. Chunking the text
        # 3. Vectorizing chunks
        # 4. Storing in vector database
        # 5. Updating document status
        
        # For now, just mark as processed
        await self.db.execute(
            update(Document)
            .where(Document.id == document_id)
            .values(
                is_processed=True,
                processing_status="completed",
                chunk_count=1,  # Placeholder
                vector_store_id="placeholder",  # Placeholder
                updated_at=datetime.utcnow()
            )
        )
        await self.db.commit()
        
        return True 