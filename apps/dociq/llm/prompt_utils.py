"""
Utility functions for reading and handling Jinja prompt templates
"""
import json
from pathlib import Path
from typing import List
from jinja2 import Environment, FileSystemLoader
from uuid import UUID
from common.utils.llm_connections import ask_llm
from apps.dociq.models.document import Document
from apps.dociq.models.template import Template
from apps.dociq.models.target_mapping import TargetMapping, TargetMappingEntry
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


def get_content_mapper_template() -> str:
    """
    Read the content mapper Jinja template from prompts/content_mapper.j2
    
    Returns:
        The template content as a string
    """
    # Get the path to the prompts directory
    prompts_dir = Path(__file__).parent.parent / "prompts"
    template_path = prompts_dir / "content_mapper.j2"
    
    # Read the template file
    with open(template_path, 'r', encoding='utf-8') as f:
        template_content = f.read()
    
    return template_content


async def get_document_content(session: AsyncSession, document_id: UUID) -> str:
    """
    Get document details and return the content of the file stored in doc_path
    
    Args:
        session: Database session
        document_id: UUID of the document
        
    Returns:
        Content of the file as string
    """
    # Get document by ID
    result = await session.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise ValueError(f"Document {document_id} not found")
    
    # Look for markdown file using document ID in outputs directory
    outputs_dir = Path("outputs")
    if outputs_dir.exists():
        md_filename = f"{document_id}.md"
        md_file_path = outputs_dir / md_filename
        
        if md_file_path.exists():
            try:
                with open(md_file_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                
                # Check if the content is a path to another file
                if content.startswith('outputs\\') or content.startswith('outputs/'):
                    # This is a reference to another file, read that file instead
                    referenced_file = Path(content)
                    
                    if referenced_file.exists():
                        with open(referenced_file, 'r', encoding='utf-8') as f:
                            actual_content = f.read()
                        return actual_content
                    else:
                        return content  # Return the path if referenced file doesn't exist
                else:
                    # This is actual content
                    if content:
                        return content
            except Exception as e:
                print(f"Error reading markdown content from {md_file_path}: {e}")
        else:
            print(f"Markdown file not found: {md_file_path}")
    else:
        print(f"Outputs directory does not exist: {outputs_dir}")
    
    # If markdown not found, try the original doc_path
    if document.doc_path and Path(document.doc_path).exists():
        try:
            with open(document.doc_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if content.strip():
                    return content
        except Exception as e:
            print(f"Error reading document content from {document.doc_path}: {e}")
    
    print(f"Could not find markdown content for document {document.id}")
    return None


async def get_template_field_mappings(session: AsyncSession, template_id: UUID) -> str:
    """
    Get template content and extract field_mappings as text
    
    Args:
        session: Database session
        template_id: UUID of the template
        
    Returns:
        Field mappings as formatted text string
    """
    # Get template by ID
    result = await session.execute(
        select(Template).where(Template.id == template_id)
    )
    template = result.scalar_one_or_none()
    
    if not template:
        raise ValueError(f"Template {template_id} not found")
    
    # Extract field_mappings and format as text
    field_mappings_text = []
    for i, field_mapping in enumerate(template.field_mappings, 1):
        field_text = f"{i}. Target Field: {field_mapping['target_field']}\n"
        field_text += f"   Sample Field Names: {', '.join(field_mapping['sample_field_names'])}\n"
        field_text += f"   Value Patterns: {', '.join(field_mapping['value_patterns'])}\n"
        field_text += f"   Description: {field_mapping['description']}\n"
        field_text += f"   Required: {field_mapping['required']}\n"
        field_mappings_text.append(field_text)
    
    return "\n".join(field_mappings_text)


async def process_content_mapping(document_id: UUID, template_id: UUID, session: AsyncSession):
    """
    Process content mapping with document_id and template_id
    
    Args:
        document_id: UUID of the document
        template_id: UUID of the template
        session: Database session
        
    Returns:
        Mapping results
    """
    # Get template field mappings
    template_field_mappings = await get_template_field_mappings(session, template_id)
    
    # Get document content
    document_content = await get_document_content(session, document_id)
    
    # Get the Jinja template
    template_content = get_content_mapper_template()
    
    # Set up Jinja environment and render template
    jinja_env = Environment(autoescape=False)
    template = jinja_env.from_string(template_content)
    
    # Render template with the retrieved data
    rendered_prompt = template.render(
        template_info=template_field_mappings,
        md_content=document_content
    )
    
    # Call LLM using llm_connections.py
    response = ask_llm(rendered_prompt)
    
    # Create response data structure
    response_data = {
        "extraction_id": str(document_id),
        "message": "Content mapping completed successfully",
        "result": response
    }
    
    # Parse the LLM response and return target mappings
    target_mapping = await parse_llm_response(response_data)
    
    return target_mapping


async def parse_llm_response(response_data: dict) -> TargetMapping:
    """
    Parse LLM response and convert to TargetMapping instance
    
    Args:
        response_data: Dictionary containing the LLM response with format:
            {
                "extraction_id": "uuid",
                "message": "Content mapping completed successfully",
                "result": "[{\"standard_field\": \"field1\", \"value\": \"value1\"}, ...]"
            }
        
    Returns:
        TargetMapping instance with parsed field mappings
        
    Raises:
        ValueError: If response format is invalid or JSON parsing fails
        KeyError: If required fields are missing from response
    """
    try:
        # Extract the result JSON string from the response
        result_json_str = response_data.get("result")
        if not result_json_str:
            raise ValueError("Missing 'result' field in response data")
        
        # Parse the JSON string into a list of dictionaries
        field_mappings = json.loads(result_json_str)
        
        if not isinstance(field_mappings, list):
            raise ValueError("Result must be a JSON array")
        
        # Create TargetMapping instance with empty list for target_mappings
        target_mapping = TargetMapping(target_mappings=[])
        
        # Add each mapping using the model's method
        for mapping in field_mappings:
            if not isinstance(mapping, dict):
                raise ValueError("Each mapping must be a JSON object")
            
            standard_field = mapping.get("standard_field")
            value = mapping.get("value")
            
            if not standard_field or not value:
                raise ValueError("Each mapping must have 'standard_field' and 'value' fields")
            
            # Add mapping using the model's method
            target_mapping.add_target_mapping(
                target_field=standard_field,
                target_value=value,
                target_confidence=None
            )
        
        return target_mapping
        
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in result field: {e}")
    except Exception as e:
        raise ValueError(f"Error parsing LLM response: {e}") 