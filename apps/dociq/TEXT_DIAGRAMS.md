# DocIQ Enhancement Endpoint - Text-Based Diagrams

This document contains simplified text-based versions of the enhancement flow diagrams for easy viewing in chat or text environments.

## 1. High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                             │
│                    [Client Application]                         │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│                        API LAYER                               │
│  [POST /extractions/{id}/enhance] ──► [extraction.py]          │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│                     SERVICE LAYER                              │
│  [ExtractionService] ──► [Redis Service Methods]               │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│                      LLM LAYER                                 │
│  [prompt_utils.py] ──► [content_enhancer.j2] ──► [Azure OpenAI]│
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│                   DATA STORAGE                                 │
│         [PostgreSQL Database] ◄──► [Redis Cache]               │
└─────────────────────────────────────────────────────────────────┘
```

## 2. PostgreSQL Source Tables & Query Conditions

```
PostgreSQL Database:
├── Core Tables (Filtered by cluster/customer/material_type)
│   ├── customers
│   │   ├── cluster, customer, id, currency
│   │   └── WHERE cluster ILIKE '%{cluster}%' AND customer ILIKE '%{customer}%'
│   │
│   ├── suppliers  
│   │   ├── cluster, vendor_code, currency, supplier_name
│   │   └── WHERE cluster ILIKE '%{cluster}%'
│   │
│   └── material_security_group
│       ├── cluster, customer, material_type, security_group
│       └── WHERE cluster ILIKE '%{cluster}%' AND customer ILIKE '%{customer}%' 
│           AND material_type ILIKE '%{material_type}%'
│
└── Reference Tables (Full table scans)
    ├── material_groups → material_group, material_sub_group
    ├── composition → short_code, composition_material  
    └── fabric_contents → fabric_content_code, fabric_content_code_description
```

## 3. Redis Storage Structure

```
Redis Key Pattern: db_query:{cluster}:{customer}:{material_type}:{timestamp}

Master Key: db_query:US:AloYoga:Fabric:20231201_143022:master
├── query_info: {"cluster": "US", "customer": "AloYoga", ...}
└── table_keys: {
    "customers": "db_query:US:AloYoga:Fabric:20231201_143022:customers",
    "suppliers": "db_query:US:AloYoga:Fabric:20231201_143022:supplier",
    "material_security_groups": "db_query:US:AloYoga:Fabric:20231201_143022:material_security_group",
    "material_groups": "db_query:US:AloYoga:Fabric:20231201_143022:material_groups",
    "composition": "db_query:US:AloYoga:Fabric:20231201_143022:composition",
    "fabric_contents": "db_query:US:AloYoga:Fabric:20231201_143022:fabric_contents"
}

Each Table Hash:
├── data: [{"field1": "value1", "field2": "value2"}, ...]
├── metadata: {"table_name": "customers", "row_count": 15, ...}
└── TTL: 86400 seconds (24 hours)
```

## 4. Enhancement Processing Flow

```
Client Request
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ POST /extractions/{id}/enhance                              │
│ Body: {"data": {"target_mappings": [...]}}                 │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. Get Extraction Record                                    │
│    ├── extraction = get_extraction_by_id(extraction_id)    │
│    ├── cluster = extraction.cluster                        │
│    ├── customer = extraction.customer                      │
│    └── material_type = extraction.material_type            │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Extract Parameters from Target Mappings                 │
│    ├── supplier_name (from "Supplier" field)               │
│    ├── short_code (from "Material Sub Group" field)        │
│    ├── fabric_content_code_description (from "Composition")│
│    └── material_group (from "Material Description" field)  │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Retrieve Redis Data                                      │
│    ├── Pattern: db_query:{cluster}:{customer}:{type}:*     │
│    ├── Get latest timestamp key                            │
│    ├── Retrieve all table data                             │
│    └── Apply filters based on extracted parameters         │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. LLM Enhancement                                          │
│    ├── Load content_enhancer.j2 template                   │
│    ├── Render with target_mappings + redis_data            │
│    ├── Call Azure OpenAI                                   │
│    └── Parse JSON response                                  │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Return Enhanced Response                                 │
│    ├── data: original target_mappings                      │
│    ├── redis_data: filtered Redis results                  │
│    └── llm_enhancement: enhanced mappings with confidence  │
└─────────────────────────────────────────────────────────────┘
```

## 5. LLM Enhancement Rules Engine

```
Input: Target Mappings + Redis Data
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│                 ENHANCEMENT RULES                           │
├─────────────────────────────────────────────────────────────┤
│ Redis-Based Enhancements (if data available):              │
│                                                             │
│ Supplier          → suppliers.vendor_code                   │
│ Customer          → customers.id                            │
│ Currency          → suppliers.currency                      │
│ Material Type     → material_security_groups.material_type │
│ Material Sec Grp  → material_security_groups.security_group│
│ Material Sub Grp  → composition.composition_material       │
│ Composition       → fabric_contents.fabric_content_code    │
│ Material Group    → material_groups (comma-separated)      │
│ Cluster           → customers.cluster                       │
├─────────────────────────────────────────────────────────────┤
│ Normalization Rules (always applied):                      │
│                                                             │
│ Width UOM: "inches" → '"'                                  │
│ UOM: "Yd"/"Yds" → "Yards"                                 │
│ Material Master Grid: "can't specify" → "No Grid"         │
│ Source Type: empty → "Nominated"                           │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
Output: Enhanced Mappings with Confidence Levels
[
  {"target_field": "Supplier", "target_value": "SUP001", "target_confidence": "enhanced"},
  {"target_field": "UOM", "target_value": "Yards", "target_confidence": "enhanced"},
  {"target_field": "Material Type", "target_value": "Fabric", "target_confidence": "original"}
]
```

## 6. Complete Data Lifecycle

```
Phase 1: Document Upload & Background Processing
┌─────────────────────────────────────────────────────────────┐
│ POST /extractions/                                          │
│ Headers: X-Cluster, X-Customer, X-Material-Type            │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ Background Task: Query 6 PostgreSQL Tables                 │
│ ├── customers (filtered by cluster + customer)             │
│ ├── suppliers (filtered by cluster)                        │
│ ├── material_security_group (filtered by all 3)            │
│ ├── material_groups (full scan)                            │
│ ├── composition (full scan)                                │
│ └── fabric_contents (full scan)                            │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ Store in Redis with 24-hour TTL                            │
│ Key: db_query:{cluster}:{customer}:{type}:{timestamp}      │
└─────────────────────────────────────────────────────────────┘

Phase 2: Template Mapping
┌─────────────────────────────────────────────────────────────┐
│ Select Template → Map Content → Generate Target Mappings   │
└─────────────────────────────────────────────────────────────┘

Phase 3: Enhancement
┌─────────────────────────────────────────────────────────────┐
│ POST /extractions/{id}/enhance                              │
│ ├── Retrieve Redis data (with filtering)                   │
│ ├── Apply LLM enhancement rules                            │
│ └── Return enhanced mappings                               │
└─────────────────────────────────────────────────────────────┘
```

## 7. Redis Filtering Logic Example

```
Input Parameters:
├── cluster: "US"
├── customer: "AloYoga" 
├── material_type: "Fabric"
├── supplier_name: "ABC Company"
├── material_group: "Weft Knit"

Redis Retrieval & Filtering:
├── Find keys: db_query:US:AloYoga:Fabric:*:master
├── Get latest timestamp key
├── Retrieve table data:
│   ├── customers: [raw data] → no filtering
│   ├── suppliers: [raw data] → filter by "ABC Company"
│   ├── material_security_groups: [raw data] → no filtering  
│   ├── material_groups: [raw data] → filter by "Weft Knit" similarity
│   ├── composition: [raw data] → no filtering
│   └── fabric_contents: [raw data] → no filtering

Filtered Output:
├── customers: [{"id": "CUST123", "cluster": "US", ...}]
├── suppliers: [{"vendor_code": "SUP001", "supplier_name": "ABC Company", ...}]
├── material_security_groups: [{"security_group": "Active_AloYoga", ...}]
├── material_groups: ["SJ", "Interlock", "Single Jersey"]  # Similar to "Weft Knit"
├── composition: []  # No short_code filter provided
└── fabric_contents: []  # No fabric_content_code_description filter provided
```

## 8. Sequence Diagram (Text Format)

```
Client → API: POST /extractions/{id}/enhance {target_mappings: [...]}
API → Service: get_extraction_by_id(extraction_id)
Service → DB: SELECT * FROM extractions WHERE id = ?
DB → Service: extraction record (cluster, customer, material_type)
Service → API: extraction object

Note: Extract parameters from target_mappings:
      - supplier_name, short_code, fabric_content_code_description, material_group

API → Service: get_all_table_results_from_redis(params...)
Service → Redis: Search for keys matching pattern
Redis → Service: Redis data or None
Service → API: redis_data

API → LLM: process_content_enhancement(target_mappings, redis_data)
Note: Uses content_enhancer.j2 template
      Applies enhancement rules
      Returns enhanced mappings
LLM → API: llm_enhancement_response

API → Client: EnhanceExtractionResponse {data, redis_data, llm_enhancement}
```

## 9. Field Enhancement Examples

### Example 1: Supplier Enhancement
```json
// Input Target Mapping
{
  "target_field": "Supplier",
  "target_value": "ABC Company"
}

// Redis Data (suppliers table)
{
  "suppliers": [
    {"vendor_code": "SUP001", "currency": "USD", "supplier_name": "ABC Company"}
  ]
}

// Enhanced Output
{
  "target_field": "Supplier",
  "target_value": "SUP001",
  "target_confidence": "enhanced"
}
```

### Example 2: UOM Normalization
```json
// Input Target Mapping
{
  "target_field": "UOM",
  "target_value": "Yds"
}

// Enhanced Output (no Redis needed)
{
  "target_field": "UOM", 
  "target_value": "Yards",
  "target_confidence": "enhanced"
}
```

### Example 3: Material Groups Processing
```json
// Input Target Mapping
{
  "target_field": "Material Group",
  "target_value": "Weft Knit"
}

// Redis Data (material_groups table)
{
  "material_groups": ["SJ", "Interlock", "Single Jersey"]
}

// Enhanced Output
{
  "target_field": "Material Group",
  "target_value": "SJ,Interlock,Single Jersey",
  "target_confidence": "enhanced"
}
```

## 10. Error Handling Flow

```
Error Scenarios & Fallback Actions:

Redis Connection Failed
    │
    ▼
Continue without Redis data (redis_data = None)
    │
    ▼
Keep original target_mappings (confidence = "original")

No Redis Data Found
    │
    ▼
Return original values with confidence = "original"

LLM Processing Error
    │
    ▼
Return error in llm_enhancement (status = "error")
    │
    ▼
Include error details and partial results

JSON Parse Error
    │
    ▼
Return graceful degradation with error details
```

## 11. Redis Key Lifecycle

```
Key Creation:
Background Task → Generate Timestamp → Create Hash Keys → Set 24h TTL

Key Usage:
Pattern Search → Get Latest Key → Retrieve Data → Apply Filters

Key Expiration:
24 Hours Later → Automatic Deletion → Memory Cleanup
```

## Summary

These text-based diagrams provide a clear overview of the DocIQ enhancement endpoint's data flow, from PostgreSQL sources through Redis caching to AI-powered field enhancement. The system processes manufacturing data through multiple layers of filtering, caching, and intelligent enhancement to improve data quality and completeness.

