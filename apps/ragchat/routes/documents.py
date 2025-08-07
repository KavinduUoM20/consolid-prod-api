from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import os
import uuid

from apps.ragchat.db import get_ragchat_session
from apps.ragchat.models import Document
from apps.ragchat.schemas.document import DocumentCreate, DocumentResponse
from apps.ragchat.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])

@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    title: str = None,
    description: str = None,
    user_id: str = None,
    db: AsyncSession = Depends(get_ragchat_session)
):
    """Upload a document for RAG processing"""
    document_service = DocumentService(db)
    
    # Validate file type
    allowed_types = ['.pdf', '.txt', '.docx', '.doc', '.md']
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in allowed_types:
        raise HTTPException(
            status_code=400, 
            detail=f"File type {file_ext} not supported. Allowed types: {allowed_types}"
        )
    
    # Save file
    file_id = str(uuid.uuid4())
    file_path = f"uploads/documents/{file_id}_{file.filename}"
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
    
    # Create document record
    document_data = DocumentCreate(
        filename=file.filename,
        file_path=file_path,
        file_size=len(content),
        file_type=file_ext,
        title=title or file.filename,
        description=description,
        user_id=user_id
    )
    
    return await document_service.create_document(document_data)

@router.get("/", response_model=List[DocumentResponse])
async def list_documents(
    user_id: str = None,
    db: AsyncSession = Depends(get_ragchat_session)
):
    """List all documents"""
    document_service = DocumentService(db)
    return await document_service.list_documents(user_id)

@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    db: AsyncSession = Depends(get_ragchat_session)
):
    """Get a specific document"""
    document_service = DocumentService(db)
    document = await document_service.get_document(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document

@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    db: AsyncSession = Depends(get_ragchat_session)
):
    """Delete a document"""
    document_service = DocumentService(db)
    success = await document_service.delete_document(document_id)
    if not success:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"message": "Document deleted successfully"}

@router.post("/{document_id}/process")
async def process_document(
    document_id: str,
    db: AsyncSession = Depends(get_ragchat_session)
):
    """Process a document for RAG (vectorize and index)"""
    document_service = DocumentService(db)
    success = await document_service.process_document(document_id)
    if not success:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"message": "Document processing started"} 