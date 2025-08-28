from typing import Optional, Tuple, List
import uuid
import asyncio
import json
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
import os
import shutil
from pathlib import Path
import redis

from apps.dociq.models.document import Document
from apps.dociq.models.extraction import Extraction
from apps.dociq.llm.prompt_utils import process_content_mapping
from apps.dociq.db import AsyncSessionLocal
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
    
    async def process_cluster_customer_headers(self, cluster: str, customer: str, material_type: str, extraction_id: str, document_id: str):
        """
        Background task to process X-Cluster, X-Customer, and X-Material-Type headers
        
        Args:
            cluster: Value from X-Cluster header
            customer: Value from X-Customer header
            material_type: Value from X-Material-Type header
            extraction_id: ID of the created extraction
            document_id: ID of the created document
        """
        print(f"=== Background Task Processing ===")
        print(f"Cluster: {cluster}")
        print(f"Customer: {customer}")
        print(f"Material Type: {material_type}")
        print(f"Extraction ID: {extraction_id}")
        print(f"Document ID: {document_id}")
        print(f"=== End Background Task ===")
        
        # Run concurrent queries to database tables
        await self._query_database_tables(cluster, customer, material_type)
        
        # Add your actual background processing logic here
        # Examples:
        # - Send analytics/tracking data
        # - Update external systems
        # - Log to specialized systems
        # - Trigger notifications
        # - Update customer-specific configurations

    async def _query_database_tables(self, cluster: str, customer: str, material_type: str):
        """
        Concurrently query the database tables: customers, supplier, material_security_group
        
        Args:
            cluster: Cluster identifier
            customer: Customer identifier
            material_type: Material type identifier
        """
        try:
            # Create a new database session for this background task
            async with AsyncSessionLocal() as session:
                # First, let's check if the tables exist and have any data at all
                try:
                    # Check if tables exist and have data
                    tables_check = await session.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name IN ('customers', 'supplier', 'material_security_group')"))
                    existing_tables = [row[0] for row in tables_check.fetchall()]
                    print(f"Existing tables: {existing_tables}")
                    
                    for table in existing_tables:
                        count_result = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                        count = count_result.scalar()
                        print(f"Table '{table}' has {count} total records")
                        
                except Exception as e:
                    print(f"Error checking tables: {e}")
                
                # Define the three concurrent queries with case insensitive partial matching
                customers_query = text("""
                    SELECT *
                    FROM customers
                    WHERE cluster ILIKE '%' || :cluster || '%'
                      AND customer ILIKE '%' || :customer || '%'
                """)
                supplier_query = text("""
                    SELECT *
                    FROM suppliers
                    WHERE cluster ILIKE '%' || :cluster || '%'
                """)
                material_security_group_query = text("""
                    SELECT *
                    FROM material_security_group
                    WHERE cluster ILIKE '%' || :cluster || '%' 
                      AND customer ILIKE '%' || :customer || '%'
                      AND material_type ILIKE '%' || :material_type || '%'
                """)
                
                # Execute all three queries concurrently
                print(f"Starting concurrent queries to database with material_type: {material_type}...")
                print(f"Query parameters - cluster: '{cluster}', customer: '{customer}', material_type: '{material_type}'")
                print("Executing queries with partial matching:")
                print(f"  - customers: WHERE cluster ILIKE '%{cluster}%' AND customer ILIKE '%{customer}%'")
                print(f"  - supplier: WHERE cluster ILIKE '%{cluster}%'")
                print(f"  - material_security_group: WHERE cluster ILIKE '%{cluster}%' AND customer ILIKE '%{customer}%' AND material_type ILIKE '%{material_type}%'")
                
                customers_task = session.execute(customers_query, {"cluster": cluster, "customer": customer})
                supplier_task = session.execute(supplier_query, {"cluster": cluster})
                material_security_group_task = session.execute(material_security_group_query, {"cluster": cluster, "customer": customer, "material_type": material_type})
                
                # Wait for all queries to complete
                customers_result, supplier_result, material_security_group_result = await asyncio.gather(
                    customers_task,
                    supplier_task,
                    material_security_group_task,
                    return_exceptions=True
                )
                
                # Process results and store in Redis
                # print("=== Database Query Results ===")
                
                # Process customers result
                if isinstance(customers_result, Exception):
                    print(f"Customers query failed: {customers_result}")
                    customers_rows = []
                else:
                    customers_rows = customers_result.fetchall()
                    print(f"Customers table: {len(customers_rows)} rows retrieved")
                    # Optionally print first few rows for debugging
                    for i, row in enumerate(customers_rows[:3]):  # Show first 3 rows
                        print(f"  Customer {i+1}: {dict(row._mapping)}")
                    if len(customers_rows) > 3:
                        print(f"  ... and {len(customers_rows) - 3} more rows")
                
                # Process supplier result
                if isinstance(supplier_result, Exception):
                    print(f"Supplier query failed: {supplier_result}")
                    supplier_rows = []
                else:
                    supplier_rows = supplier_result.fetchall()
                    print(f"Supplier table: {len(supplier_rows)} rows retrieved")
                    # Optionally print first few rows for debugging
                    for i, row in enumerate(supplier_rows[:3]):  # Show first 3 rows
                        print(f"  Supplier {i+1}: {dict(row._mapping)}")
                    if len(supplier_rows) > 3:
                        print(f"  ... and {len(supplier_rows) - 3} more rows")
                
                # Process material_security_group result
                if isinstance(material_security_group_result, Exception):
                    print(f"Material security group query failed: {material_security_group_result}")
                    material_security_group_rows = []
                else:
                    material_security_group_rows = material_security_group_result.fetchall()
                    print(f"Material security group table: {len(material_security_group_rows)} rows retrieved")
                    # Optionally print first few rows for debugging
                    for i, row in enumerate(material_security_group_rows[:3]):  # Show first 3 rows
                        print(f"  Material security group {i+1}: {dict(row._mapping)}")
                    if len(material_security_group_rows) > 3:
                        print(f"  ... and {len(material_security_group_rows) - 3} more rows")
                
                # Store results in Redis as hashmaps
                await self._store_table_results_in_redis(
                    cluster, customer, material_type,
                    customers_rows, supplier_rows, material_security_group_rows
                )
                
                # print("=== End Database Query Results ===")
                
        except Exception as e:
            # print(f"Error querying database tables: {e}")
            pass

    async def _store_table_results_in_redis(
        self, 
        cluster: str, 
        customer: str, 
        material_type: str,
        customers_rows: List,
        supplier_rows: List, 
        material_security_group_rows: List
    ):
        """
        Store database table results in Redis as hashmaps for easy retrieval
        
        Args:
            cluster: Cluster identifier
            customer: Customer identifier  
            material_type: Material type identifier
            customers_rows: Results from customers table
            supplier_rows: Results from supplier table
            material_security_group_rows: Results from material_security_group table
        """
        if not REDIS_AVAILABLE or not REDIS_CLIENT:
            return
            
        try:
            # Create a unique key prefix for this query
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            key_prefix = f"db_query:{cluster}:{customer}:{material_type}:{timestamp}"
            
            # Store customers table results
            customers_hash_key = f"{key_prefix}:customers"
            if customers_rows:
                # Convert rows to clean JSON array
                rows_data = []
                for row in customers_rows:
                    row_data = dict(row._mapping)
                    # Convert non-serializable types to strings
                    clean_row = {}
                    for k, v in row_data.items():
                        if v is None:
                            clean_row[k] = None
                        elif isinstance(v, (str, int, float, bool)):
                            clean_row[k] = v
                        else:
                            clean_row[k] = str(v)
                    rows_data.append(clean_row)
                
                # Store as clean JSON
                REDIS_CLIENT.hset(customers_hash_key, "data", json.dumps(rows_data))
                REDIS_CLIENT.hset(customers_hash_key, "metadata", json.dumps({
                    "table_name": "customers",
                    "row_count": len(customers_rows),
                    "query_timestamp": timestamp,
                    "query_params": {
                        "cluster": cluster,
                        "customer": customer,
                        "material_type": material_type
                    }
                }))
                
                # Set expiration (24 hours)
                REDIS_CLIENT.expire(customers_hash_key, 86400)
            
            # Store supplier table results
            supplier_hash_key = f"{key_prefix}:supplier"
            if supplier_rows:
                # Convert rows to clean JSON array
                rows_data = []
                for row in supplier_rows:
                    row_data = dict(row._mapping)
                    # Convert non-serializable types to strings
                    clean_row = {}
                    for k, v in row_data.items():
                        if v is None:
                            clean_row[k] = None
                        elif isinstance(v, (str, int, float, bool)):
                            clean_row[k] = v
                        else:
                            clean_row[k] = str(v)
                    rows_data.append(clean_row)
                
                # Store as clean JSON
                REDIS_CLIENT.hset(supplier_hash_key, "data", json.dumps(rows_data))
                REDIS_CLIENT.hset(supplier_hash_key, "metadata", json.dumps({
                    "table_name": "supplier",
                    "row_count": len(supplier_rows),
                    "query_timestamp": timestamp,
                    "query_params": {
                        "cluster": cluster,
                        "customer": customer,
                        "material_type": material_type
                    }
                }))
                
                # Set expiration (24 hours)
                REDIS_CLIENT.expire(supplier_hash_key, 86400)
            
            # Store material_security_group table results
            msg_hash_key = f"{key_prefix}:material_security_group"
            if material_security_group_rows:
                # Convert rows to clean JSON array
                rows_data = []
                for row in material_security_group_rows:
                    row_data = dict(row._mapping)
                    # Convert non-serializable types to strings
                    clean_row = {}
                    for k, v in row_data.items():
                        if v is None:
                            clean_row[k] = None
                        elif isinstance(v, (str, int, float, bool)):
                            clean_row[k] = v
                        else:
                            clean_row[k] = str(v)
                    rows_data.append(clean_row)
                
                # Store as clean JSON
                REDIS_CLIENT.hset(msg_hash_key, "data", json.dumps(rows_data))
                REDIS_CLIENT.hset(msg_hash_key, "metadata", json.dumps({
                    "table_name": "material_security_group",
                    "row_count": len(material_security_group_rows),
                    "query_timestamp": timestamp,
                    "query_params": {
                        "cluster": cluster,
                        "customer": customer,
                        "material_type": material_type
                    }
                }))
                
                # Set expiration (24 hours)
                REDIS_CLIENT.expire(msg_hash_key, 86400)
            
            # Store a master key that lists all the table keys for this query
            master_key = f"{key_prefix}:master"
            table_keys = {
                "customers": customers_hash_key if customers_rows else None,
                "supplier": supplier_hash_key if supplier_rows else None, 
                "material_security_group": msg_hash_key if material_security_group_rows else None
            }
            
            print(f"Redis storage summary:")
            print(f"  - customers_rows: {len(customers_rows)} -> hash_key: {customers_hash_key if customers_rows else 'None'}")
            print(f"  - supplier_rows: {len(supplier_rows)} -> hash_key: {supplier_hash_key if supplier_rows else 'None'}")
            print(f"  - material_security_group_rows: {len(material_security_group_rows)} -> hash_key: {msg_hash_key if material_security_group_rows else 'None'}")
            
            # Remove None values
            table_keys = {k: v for k, v in table_keys.items() if v is not None}
            print(f"  - Final table_keys: {table_keys}")
            
            REDIS_CLIENT.hset(master_key, "query_info", json.dumps({
                "cluster": cluster,
                "customer": customer,
                "material_type": material_type,
                "timestamp": timestamp,
                "table_keys": table_keys
            }))
            REDIS_CLIENT.expire(master_key, 86400)
            
        except Exception as e:
            # Silently handle Redis errors to not break the main flow
            pass

    def get_table_results_from_redis(self, cluster: str, customer: str, material_type: str, timestamp: str = None):
        """
        Retrieve database table results from Redis hashmaps
        
        Args:
            cluster: Cluster identifier
            customer: Customer identifier  
            material_type: Material type identifier
            timestamp: Optional timestamp, if None will try to find the latest
            
        Returns:
            dict: Dictionary containing the table results or None if not found
        """
        if not REDIS_AVAILABLE or not REDIS_CLIENT:
            return None
            
        try:
            # If no timestamp provided, try to find keys with pattern
            if not timestamp:
                pattern = f"db_query:{cluster}:{customer}:{material_type}:*:master"
                master_keys = REDIS_CLIENT.keys(pattern)
                if not master_keys:
                    return None
                # Get the most recent one (keys are sorted by timestamp)
                master_key = sorted(master_keys)[-1].decode('utf-8')
            else:
                master_key = f"db_query:{cluster}:{customer}:{material_type}:{timestamp}:master"
            
            # Get the master information
            master_info = REDIS_CLIENT.hget(master_key, "query_info")
            if not master_info:
                return None
                
            query_info = json.loads(master_info.decode('utf-8'))
            table_keys = query_info.get("table_keys", {})
            
            results = {
                "query_info": query_info,
                "tables": {}
            }
            
            # Retrieve each table's data
            for table_name, hash_key in table_keys.items():
                table_data = REDIS_CLIENT.hgetall(hash_key)
                if table_data:
                    # Decode the data
                    decoded_data = {k.decode('utf-8'): v.decode('utf-8') for k, v in table_data.items()}
                    
                    # Extract data and metadata from new clean format
                    rows = []
                    metadata = {}
                    
                    if "data" in decoded_data:
                        rows = json.loads(decoded_data["data"])
                    
                    if "metadata" in decoded_data:
                        metadata = json.loads(decoded_data["metadata"])
                    
                    results["tables"][table_name] = {
                        "rows": rows,
                        "metadata": metadata
                    }
            
            return results
            
        except Exception as e:
            return None

    def get_all_table_results_from_redis(self, cluster: str, customer: str, material_type: str, timestamp: str = None):
        """
        Retrieve all database table results (customers, suppliers, material_security_groups) from Redis
        
        Args:
            cluster: Cluster identifier
            customer: Customer identifier  
            material_type: Material type identifier
            timestamp: Optional timestamp, if None will try to find the latest
            
        Returns:
            dict: Dictionary containing all table results with keys 'customers', 'suppliers', 'material_security_groups'
                  Returns None if no data found
        """
        if not REDIS_AVAILABLE or not REDIS_CLIENT:
            return None
            
        try:
            # Get the full results using the existing method
            redis_results = self.get_table_results_from_redis(cluster, customer, material_type, timestamp)
            
            if not redis_results or "tables" not in redis_results:
                return None
            
            # Extract and organize the data for easy access
            all_results = {
                "query_info": redis_results.get("query_info", {}),
                "customers": [],
                "suppliers": [],
                "material_security_groups": []
            }
            
            # Extract customers data
            if "customers" in redis_results["tables"]:
                all_results["customers"] = redis_results["tables"]["customers"]["rows"]
            
            # Extract supplier data (note: Redis stores as "supplier" but we return as "suppliers")
            if "supplier" in redis_results["tables"]:
                all_results["suppliers"] = redis_results["tables"]["supplier"]["rows"]
            
            # Extract material_security_group data (return as "material_security_groups")
            if "material_security_group" in redis_results["tables"]:
                all_results["material_security_groups"] = redis_results["tables"]["material_security_group"]["rows"]
            
            return all_results
            
        except Exception as e:
            return None

    async def create_extraction_with_document(
        self, 
        file_bytes: bytes, 
        filename: str,
        file_size: int,
        cluster: Optional[str] = None,
        customer: Optional[str] = None,
        material_type: Optional[str] = None
    ) -> Tuple[Extraction, Document]:
        """
        Create a document and extraction record, process with Mistral
        
        Args:
            file_bytes: Uploaded file bytes
            filename: Original filename
            file_size: File size in bytes
            cluster: Optional cluster identifier
            customer: Optional customer identifier
            material_type: Optional material type identifier
            
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
            customer=customer,
            material_type=material_type
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