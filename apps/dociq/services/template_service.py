from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlmodel import select as sqlmodel_select

from apps.dociq.models.template import Template
from apps.dociq.schemas.template import TemplateCreate, TemplateUpdate


class TemplateService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_template(self, template_data: TemplateCreate) -> Template:
        """Create a new template"""
        template = Template(**template_data.model_dump())
        self.session.add(template)
        await self.session.commit()
        await self.session.refresh(template)
        return template

    async def get_template_by_id(self, template_id: UUID) -> Optional[Template]:
        """Get template by ID"""
        result = await self.session.execute(
            select(Template).where(Template.id == template_id)
        )
        return result.scalar_one_or_none()

    async def get_templates(
        self, 
        skip: int = 0, 
        limit: int = 100,
        category: Optional[str] = None,
        template_type: Optional[str] = None
    ) -> List[Template]:
        """Get templates with optional filtering"""
        query = select(Template)
        
        if category:
            query = query.where(Template.category == category)
        if template_type:
            query = query.where(Template.type == template_type)
            
        query = query.offset(skip).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def update_template(
        self, 
        template_id: UUID, 
        template_data: TemplateUpdate
    ) -> Optional[Template]:
        """Update an existing template"""
        template = await self.get_template_by_id(template_id)
        if not template:
            return None
        
        update_data = template_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(template, field, value)
        
        await self.session.commit()
        await self.session.refresh(template)
        return template

    async def delete_template(self, template_id: UUID) -> bool:
        """Delete a template"""
        template = await self.get_template_by_id(template_id)
        if not template:
            return False
        
        await self.session.delete(template)
        await self.session.commit()
        return True

    async def get_template_by_name(self, name: str) -> Optional[Template]:
        """Get template by name"""
        result = await self.session.execute(
            select(Template).where(Template.name == name)
        )
        return result.scalar_one_or_none() 