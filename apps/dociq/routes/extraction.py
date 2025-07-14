from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from apps.dociq.db import get_dociq_session
from apps.dociq.services.extraction_service import ExtractionService
from apps.dociq.schemas.extraction import ExtractionRead

router = APIRouter()


class ExtractionResponse(BaseModel):
    extraction_id: UUID
    document_id: UUID
    status: str
    current_step: str
    message: str


class UpdateTemplateRequest(BaseModel):
    template_id: UUID


class UpdateTemplateResponse(BaseModel):
    extraction_id: UUID
    template_id: UUID
    message: str


class ProceedToNextStepRequest(BaseModel):
    template_id: UUID


class ProceedToNextStepResponse(BaseModel):
    extraction_id: UUID
    template_id: UUID
    current_step: str
    message: str


async def get_extraction_service(session: AsyncSession = Depends(get_dociq_session)) -> ExtractionService:
    """Dependency to get extraction service"""
    return ExtractionService(session)


@router.post("/extractions/", response_model=ExtractionResponse, status_code=status.HTTP_201_CREATED)
async def create_extraction(
    file: UploadFile = File(...),
    extraction_service: ExtractionService = Depends(get_extraction_service)
):
    """
    Step 1: Upload document and start extraction process
    
    - **file**: PDF/Excel file to upload and process
    - Returns extraction_id for tracking the KYC flow
    """
    # Validate file type
    allowed_extensions = ['.pdf', '.xlsx', '.xls', '.doc', '.docx', '.txt', '.jpg', '.jpeg', '.png', '.gif']
    file_extension = '.' + file.filename.split('.')[-1].lower() if '.' in file.filename else ''
    
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {file_extension}. Allowed types: {', '.join(allowed_extensions)}"
        )
    
    try:
        # Read file content
        file_content = await file.read()
        file_size = len(file_content)
        
        # Create extraction and document records, process with Mistral
        extraction, document = await extraction_service.create_extraction_with_document(
            file_bytes=file_content,
            filename=file.filename,
            file_size=file_size
        )
        
        # Determine response message based on processing result
        if extraction.status == "extracted":
            message = "Document uploaded and processed successfully with Mistral"
        elif extraction.status == "extraction_failed":
            message = "Document uploaded but Mistral processing failed"
        else:
            message = "Document uploaded successfully"
        
        return ExtractionResponse(
            extraction_id=extraction.id,
            document_id=document.id,
            status=extraction.status,
            current_step=extraction.current_step,
            message=message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process document: {str(e)}"
        )


@router.get("/extractions/{extraction_id}", response_model=ExtractionRead)
async def get_extraction(
    extraction_id: UUID,
    extraction_service: ExtractionService = Depends(get_extraction_service)
):
    """
    Get extraction status and details
    
    - **extraction_id**: UUID of the extraction to retrieve
    - Returns complete extraction record with all fields
    """
    extraction = await extraction_service.get_extraction_by_id(extraction_id)
    
    if not extraction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Extraction with ID {extraction_id} not found"
        )
    
    return extraction


@router.patch("/extractions/{extraction_id}", response_model=UpdateTemplateResponse)
async def update_extraction_template(
    extraction_id: UUID,
    request: UpdateTemplateRequest,
    extraction_service: ExtractionService = Depends(get_extraction_service)
):
    """
    Update the template_id of an existing extraction record (Legacy endpoint)
    
    - **extraction_id**: UUID of the extraction to update
    - **template_id**: UUID of the template to assign to the extraction
    """
    try:
        # Update the extraction template
        updated_extraction = await extraction_service.update_extraction_template(
            extraction_id=extraction_id,
            template_id=request.template_id
        )
        
        if not updated_extraction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Extraction with ID {extraction_id} not found"
            )
        
        return UpdateTemplateResponse(
            extraction_id=updated_extraction.id,
            template_id=updated_extraction.template_id,
            message=f"Template {request.template_id} successfully assigned to extraction {extraction_id}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update extraction template: {str(e)}"
        )


@router.patch("/extractions/{extraction_id}/proceed", response_model=ProceedToNextStepResponse)
async def proceed_to_next_step(
    extraction_id: UUID,
    request: ProceedToNextStepRequest,
    extraction_service: ExtractionService = Depends(get_extraction_service)
):
    """
    Proceed to the next step in the extraction workflow
    
    - **extraction_id**: UUID of the extraction to update
    - **template_id**: UUID of the template to assign to the extraction
    - This endpoint is called when "Next: Configure Settings" button is clicked
    """
    try:
        # Update the extraction template and move to next step
        updated_extraction = await extraction_service.update_extraction_template(
            extraction_id=extraction_id,
            template_id=request.template_id
        )
        
        if not updated_extraction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Extraction with ID {extraction_id} not found"
            )
        
        return ProceedToNextStepResponse(
            extraction_id=updated_extraction.id,
            template_id=updated_extraction.template_id,
            current_step=updated_extraction.current_step,
            message=f"Successfully proceeded to next step. Template {request.template_id} assigned and current step updated to '{updated_extraction.current_step}'"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to proceed to next step: {str(e)}"
        )


@router.post("/extractions/{extraction_id}/map")
async def map_extraction(
    extraction_id: UUID,
    extraction_service: ExtractionService = Depends(get_extraction_service)
):
    """
    Map extraction content to template fields
    
    - **extraction_id**: UUID of the extraction to map
    """
    try:
        # Call the service's map_extraction method
        result = await extraction_service.map_extraction(extraction_id)
        
        return {
            "extraction_id": extraction_id,
            "message": "Content mapping completed successfully",
            "result": result
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to map extraction: {str(e)}"
        ) 