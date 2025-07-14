from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.dociq.db import get_dociq_session
from apps.dociq.services.template_service import TemplateService
from apps.dociq.schemas.template import (
    TemplateCreate, 
    TemplateRead, 
    TemplateUpdate,
    TemplateBase
)

router = APIRouter()


async def get_template_service(session: AsyncSession = Depends(get_dociq_session)) -> TemplateService:
    """Dependency to get template service"""
    return TemplateService(session)


@router.post("/templates", response_model=TemplateRead, status_code=status.HTTP_201_CREATED)
async def create_template(
    template_data: TemplateCreate,
    template_service: TemplateService = Depends(get_template_service)
):
    """
    Create a new template
    
    - **name**: Template name (must be unique)
    - **type**: Template type (pdf or excel)
    - **category**: Template category
    - **description**: Optional description
    - **field_mappings**: List of field mappings for data extraction
    - **header_row**: Excel-specific: row number containing headers
    - **sheetname**: Excel-specific: sheet name
    """
    # Check if template with same name already exists
    existing_template = await template_service.get_template_by_name(template_data.name)
    if existing_template:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Template with name '{template_data.name}' already exists"
        )
    
    try:
        template = await template_service.create_template(template_data)
        return template
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create template: {str(e)}"
        )


@router.get("/templates", response_model=List[TemplateRead])
async def get_templates(
    skip: int = 0,
    limit: int = 100,
    category: Optional[str] = None,
    template_type: Optional[str] = None,
    template_service: TemplateService = Depends(get_template_service)
):
    """
    Get all templates with optional filtering
    
    - **skip**: Number of records to skip for pagination
    - **limit**: Maximum number of records to return
    - **category**: Filter by category
    - **template_type**: Filter by template type (pdf or excel)
    """
    templates = await template_service.get_templates(
        skip=skip, 
        limit=limit, 
        category=category, 
        template_type=template_type
    )
    return templates


@router.get("/templates/{template_id}", response_model=TemplateRead)
async def get_template(
    template_id: UUID,
    template_service: TemplateService = Depends(get_template_service)
):
    """
    Get a specific template by ID
    """
    template = await template_service.get_template_by_id(template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template with ID {template_id} not found"
        )
    return template


@router.put("/templates/{template_id}", response_model=TemplateRead)
async def update_template(
    template_id: UUID,
    template_data: TemplateUpdate,
    template_service: TemplateService = Depends(get_template_service)
):
    """
    Update an existing template
    """
    template = await template_service.update_template(template_id, template_data)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template with ID {template_id} not found"
        )
    return template


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: UUID,
    template_service: TemplateService = Depends(get_template_service)
):
    """
    Delete a template
    """
    success = await template_service.delete_template(template_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template with ID {template_id} not found"
        ) 