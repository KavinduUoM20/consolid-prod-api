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


def get_content_enhancer_template() -> str:
    """
    Read the content enhancer Jinja template from prompts/content_enhancer.j2
    
    Returns:
        The template content as a string
    """
    # Get the path to the prompts directory
    prompts_dir = Path(__file__).parent.parent / "prompts"
    template_path = prompts_dir / "content_enhancer.j2"
    
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
        # Support both Pydantic models and plain dicts
        fm = (
            field_mapping.model_dump()
            if hasattr(field_mapping, "model_dump")
            else dict(field_mapping)
        )

        field_text = f"{i}. Target Field: {fm.get('target_field')}\n"
        field_text += f"   Sample Field Names: {', '.join(fm.get('sample_field_names', []))}\n"
        field_text += f"   Value Patterns: {', '.join(fm.get('value_patterns', []))}\n"
        field_text += f"   Description: {fm.get('description')}\n"
        field_text += f"   Required: {fm.get('required')}\n"
        field_mappings_text.append(field_text)
    
    return "\n".join(field_mappings_text)


async def process_content_mapping(document_id: UUID, template_id: UUID, session: AsyncSession, cluster: str = None, customer: str = None):
    """
    Process content mapping with document_id and template_id
    
    Args:
        document_id: UUID of the document
        template_id: UUID of the template
        session: Database session
        cluster: Optional cluster identifier for reference in template
        customer: Optional customer identifier for reference in template
        
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
        md_content=document_content,
        cluster=cluster,
        customer=customer
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


async def process_content_enhancement(target_mappings: List[dict], redis_data: dict = None):
    """
    Process content enhancement with target mappings and Redis data
    
    Args:
        target_mappings: List of target mapping dictionaries
        redis_data: Dictionary containing Redis table results
        
    Returns:
        LLM enhancement response
    """
    # Get the Jinja template
    template_content = get_content_enhancer_template()
    
    # Set up Jinja environment and render template
    jinja_env = Environment(autoescape=False)
    template = jinja_env.from_string(template_content)
    
    # Prepare data for template rendering
    template_data = {
        "target_mappings": target_mappings,
        "redis_data": redis_data or {},
        "has_redis_data": redis_data is not None
    }
    
    # Render template with the data
    rendered_prompt = template.render(**template_data)
    
    # Log the rendered prompt for debugging
    print("=== LLM Enhancement Prompt ===")
    print(rendered_prompt[:500] + "..." if len(rendered_prompt) > 500 else rendered_prompt)
    print("=== End Prompt ===")
    
    # Call LLM using llm_connections.py
    response = ask_llm(rendered_prompt)
    
    print(f"=== LLM Raw Response ===")
    print(response[:300] + "..." if len(response) > 300 else response)
    print("=== End Raw Response ===")
    
    # Parse and clean the response
    cleaned_response = parse_llm_enhancement_response(response)
    
    return cleaned_response


def parse_llm_enhancement_response(raw_response: str) -> dict:
    """
    Parse and clean the LLM enhancement response to extract structured JSON
    
    Args:
        raw_response: Raw response from LLM which may contain markdown code blocks
        
    Returns:
        dict: Structured response with parsed JSON and metadata
    """
    try:
        # Remove markdown code blocks if present
        cleaned_response = raw_response.strip()
        
        # Check if response is wrapped in markdown code blocks
        if cleaned_response.startswith('```json') and cleaned_response.endswith('```'):
            # Extract JSON from markdown code block
            cleaned_response = cleaned_response[7:-3].strip()  # Remove ```json and ```
        elif cleaned_response.startswith('```') and cleaned_response.endswith('```'):
            # Extract content from generic code block
            cleaned_response = cleaned_response[3:-3].strip()  # Remove ``` and ```
        
        # Try to parse as JSON
        try:
            enhanced_mappings = json.loads(cleaned_response)
            
            # Validate that it's a list of mappings
            if not isinstance(enhanced_mappings, list):
                raise ValueError("Enhanced mappings must be a JSON array")
            
            # Count enhancements
            enhancement_stats = {
                "original": 0,
                "enhanced": 0
            }
            
            for mapping in enhanced_mappings:
                confidence = mapping.get("target_confidence", "original")
                if confidence in enhancement_stats:
                    enhancement_stats[confidence] += 1
            
            return {
                "status": "success",
                "enhanced_mappings": enhanced_mappings,
                "enhancement_stats": enhancement_stats,
                "total_fields": len(enhanced_mappings)
            }
            
        except json.JSONDecodeError as e:
            print(f"Failed to parse LLM response as JSON: {e}")
            return {
                "status": "parse_error",
                "error": f"JSON parsing failed: {str(e)}",
                "raw_response": raw_response[:200] + "..." if len(raw_response) > 200 else raw_response
            }
    
    except Exception as e:
        print(f"Error processing LLM enhancement response: {e}")
        return {
            "status": "error",
            "error": str(e),
            "raw_response": raw_response[:200] + "..." if len(raw_response) > 200 else raw_response
        }


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