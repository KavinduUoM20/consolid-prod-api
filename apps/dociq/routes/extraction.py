from typing import Optional, Dict, Any, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, WebSocket, Query, BackgroundTasks, Request
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


class EnhanceExtractionRequest(BaseModel):
    data: Dict[str, Any]


class EnhanceExtractionResponse(BaseModel):
    extraction_id: UUID
    message: str
    data: Dict[str, Any]
    redis_data: Optional[Dict[str, Any]] = None


async def get_extraction_service(session: AsyncSession = Depends(get_dociq_session)) -> ExtractionService:
    """Dependency to get extraction service"""
    return ExtractionService(session)


@router.post("/extractions/", response_model=ExtractionResponse, status_code=status.HTTP_201_CREATED)
async def create_extraction(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    extraction_service: ExtractionService = Depends(get_extraction_service)
):
    """
    Step 1: Upload document and start extraction process
    
    - **file**: PDF/Excel file to upload and process
    - Returns extraction_id for tracking the KYC flow
    """
    # Validate file type
    allowed_extensions = ['.pdf', '.xlsx', '.xls']
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
        
        # Extract headers for cluster, customer, and material type information
        cluster = request.headers.get("X-Cluster")
        customer = request.headers.get("X-Customer")
        material_type = request.headers.get("X-Material-Type")
        
        # Create extraction and document records, process with Mistral
        extraction, document = await extraction_service.create_extraction_with_document(
            file_bytes=file_content,
            filename=file.filename,
            file_size=file_size,
            cluster=cluster,
            customer=customer,
            material_type=material_type
        )
        
        # Determine response message based on processing result
        if extraction.status == "extracted":
            message = "Document uploaded and processed successfully with Mistral"
        elif extraction.status == "extraction_failed":
            message = "Document uploaded but Mistral processing failed"
        else:
            message = "Document uploaded successfully"
        
        # Add background task if headers are present
        if cluster and customer:
            background_tasks.add_task(
                extraction_service.process_cluster_customer_headers,
                cluster=cluster,
                customer=customer,
                material_type=material_type,
                extraction_id=str(extraction.id),
                document_id=str(document.id)
            )
        
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


@router.get("/extractions/", response_model=List[ExtractionRead])
async def get_all_extractions(
    limit: Optional[int] = Query(None, ge=1, le=100, description="Number of extractions to return (max 100)"),
    offset: Optional[int] = Query(None, ge=0, description="Number of extractions to skip"),
    extraction_service: ExtractionService = Depends(get_extraction_service)
):
    """
    Get all extractions with optional pagination
    
    - **limit**: Maximum number of extractions to return (1-100)
    - **offset**: Number of extractions to skip for pagination
    - Returns list of extraction records ordered by creation date (newest first)
    """
    try:
        extractions = await extraction_service.get_all_extractions(limit=limit, offset=offset)
        return extractions
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve extractions: {str(e)}"
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


@router.post("/extractions/{extraction_id}/enhance", response_model=EnhanceExtractionResponse)
async def enhance_extraction(
    extraction_id: UUID,
    request: EnhanceExtractionRequest,
    extraction_service: ExtractionService = Depends(get_extraction_service)
):
    """
    Enhance extraction content and processing
    
    - **extraction_id**: UUID of the extraction to enhance
    - **request**: Request body containing data to enhance
    - Returns the same data object from the request body plus Redis table results
    """
    try:
        # Get the extraction record - it should always exist with cluster, customer, material_type
        extraction = await extraction_service.get_extraction_by_id(extraction_id)
        
        if not extraction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Extraction {extraction_id} not found"
            )
        
        # Debug: Show all extraction fields
        print(f"Extraction record found:")
        print(f"  - ID: {extraction.id}")
        print(f"  - cluster: '{extraction.cluster}'")
        print(f"  - customer: '{extraction.customer}'")
        print(f"  - material_type: '{extraction.material_type}'")
        print(f"  - status: '{extraction.status}'")
        print(f"  - current_step: '{extraction.current_step}'")
        print(f"  - created_at: {extraction.created_at}")
        
        # Use the parameters from the extraction record
        cluster = extraction.cluster
        customer = extraction.customer  
        material_type = extraction.material_type
        
        # Validate that we have the required parameters
        if not cluster or not customer or not material_type:
            print(f"WARNING: Extraction record missing required fields!")
            print(f"  - cluster: {'✓' if cluster else '✗'} '{cluster}'")
            print(f"  - customer: {'✓' if customer else '✗'} '{customer}'")
            print(f"  - material_type: {'✓' if material_type else '✗'} '{material_type}'")
        
        print(f"Using extraction record parameters - Cluster: {cluster}, Customer: {customer}, Material Type: {material_type}")
        
        # Fetch Redis table results if we have the required parameters
        redis_data = None
        if cluster and customer and material_type:
            redis_data = extraction_service.get_all_table_results_from_redis(
                cluster=cluster,
                customer=customer,
                material_type=material_type
            )
            print(f"Redis lookup successful: found {len(redis_data.get('customers', []))} customers, {len(redis_data.get('suppliers', []))} suppliers, {len(redis_data.get('material_security_groups', []))} security groups" if redis_data else "Redis lookup returned no data")
        else:
            print(f"Missing required parameters for Redis lookup: cluster={cluster}, customer={customer}, material_type={material_type}")
        
        # Prepare response message
        message = "Extraction enhancement completed successfully"
        if redis_data:
            total_customers = len(redis_data.get("customers", []))
            total_suppliers = len(redis_data.get("suppliers", []))
            total_msg = len(redis_data.get("material_security_groups", []))
            message += f" with {total_customers} customers, {total_suppliers} suppliers, {total_msg} material security groups"
        else:
            message += " (no Redis data available)"
        
        # Log what we're returning
        print(f"Returning target data fields: {list(request.data.keys())}")
        print(f"Redis data available: {redis_data is not None}")
        if redis_data:
            print(f"Redis data contains: {list(redis_data.keys())}")
        
        return EnhanceExtractionResponse(
            extraction_id=extraction_id,
            message=message,
            data=request.data,  # ✅ Original target data from request
            redis_data=redis_data  # ✅ Related Redis data (customers, suppliers, material_security_groups)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to enhance extraction: {str(e)}"
        )


@router.get("/extractions/")
async def list_extractions(
    limit: Optional[int] = Query(10, description="Number of extractions to return"),
    offset: Optional[int] = Query(0, description="Number of extractions to skip"),
    extraction_service: ExtractionService = Depends(get_extraction_service)
):
    """
    List extractions for debugging purposes
    
    - **limit**: Maximum number of extractions to return (default: 10)
    - **offset**: Number of extractions to skip (default: 0)
    """
    try:
        extractions = await extraction_service.get_all_extractions(limit=limit, offset=offset)
        
        # Debug: Check if material_type attribute exists and database schema
        if extractions:
            sample_extraction = extractions[0]
            print(f"Sample extraction attributes: {dir(sample_extraction)}")
            print(f"Has material_type attribute: {hasattr(sample_extraction, 'material_type')}")
            if hasattr(sample_extraction, 'material_type'):
                print(f"material_type value: '{sample_extraction.material_type}'")
            
            # Check database schema for material_type column
            try:
                from sqlalchemy import text
                session = extraction_service.session
                schema_check = await session.execute(text("""
                    SELECT column_name, data_type, is_nullable 
                    FROM information_schema.columns 
                    WHERE table_name = 'extractions' 
                    AND column_name = 'material_type'
                """))
                column_info = schema_check.fetchall()
                if column_info:
                    print(f"material_type column exists: {column_info[0]}")
                else:
                    print("material_type column does NOT exist in database schema")
            except Exception as e:
                print(f"Error checking schema: {e}")
        
        # Create response with explicit field access
        extraction_list = []
        for extraction in extractions:
            try:
                extraction_data = {
                    "id": str(extraction.id),
                    "status": extraction.status,
                    "current_step": extraction.current_step,
                    "cluster": getattr(extraction, 'cluster', 'ATTR_NOT_FOUND'),
                    "customer": getattr(extraction, 'customer', 'ATTR_NOT_FOUND'),
                    "material_type": getattr(extraction, 'material_type', 'ATTR_NOT_FOUND'),
                    "created_at": extraction.created_at,
                    "document_id": str(extraction.document_id) if extraction.document_id else None,
                    "has_required_fields": bool(extraction.cluster and extraction.customer and extraction.material_type)
                }
                print(f"Extraction {extraction.id}: cluster='{extraction.cluster}', customer='{extraction.customer}', material_type='{extraction.material_type}'")
                extraction_list.append(extraction_data)
            except Exception as e:
                print(f"Error processing extraction {extraction.id}: {e}")
                extraction_list.append({"id": str(extraction.id), "error": str(e)})
        
        return {
            "total_returned": len(extractions),
            "extractions": extraction_list
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list extractions: {str(e)}"
        )


@router.websocket("/extractions/ws")
async def extraction_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for real-time extraction updates
    """
    await websocket.accept()
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            # Echo back the same message (simple response)
            await websocket.send_text(f"Echo: {data}")
            
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await websocket.close() 