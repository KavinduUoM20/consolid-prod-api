from fastapi import APIRouter, HTTPException
from datetime import datetime
import json

router = APIRouter()

@router.get("/ocap/health")
async def health_check():
    """Health check endpoint to test LLM connectivity."""
    health_status = {
        "timestamp": datetime.now().isoformat(),
        "service": "ocap-manufacturing-assistant",
        "status": "unknown",
        "checks": {}
    }
    
    # Check 1: Environment Variables
    try:
        from common.utils.llm_connections import required_vars
        
        env_check = {
            "deployment": "SET" if required_vars.get("AZURE_OPENAI_DEPLOYMENT") else "MISSING",
            "endpoint": "SET" if required_vars.get("AZURE_OPENAI_ENDPOINT") else "MISSING",
            "api_version": "SET" if required_vars.get("AZURE_OPENAI_API_VERSION") else "MISSING",
            "api_key": "SET" if required_vars.get("AZURE_OPENAI_API_KEY") else "MISSING"
        }
        
        health_status["checks"]["environment"] = {
            "status": "healthy" if all(v == "SET" for v in env_check.values()) else "unhealthy",
            "details": env_check
        }
        
    except Exception as e:
        health_status["checks"]["environment"] = {
            "status": "error",
            "error": str(e)
        }
    
    # Check 2: LLM Basic Connectivity
    try:
        from common.utils.llm_connections import ask_llm_with_system_prompt
        
        test_response = ask_llm_with_system_prompt(
            system_prompt="You are a test assistant. Respond with exactly: 'HEALTH_CHECK_OK'",
            user_prompt="Health check",
            temperature=0.1
        )
        
        health_status["checks"]["llm_basic"] = {
            "status": "healthy" if "HEALTH_CHECK_OK" in test_response else "unhealthy",
            "response": test_response[:100]
        }
        
    except Exception as e:
        health_status["checks"]["llm_basic"] = {
            "status": "error",
            "error": str(e)
        }
    
    # Check 3: LangChain Components
    try:
        from langchain_openai import AzureChatOpenAI
        from langchain.prompts import PromptTemplate
        from langchain_core.output_parsers import StrOutputParser
        from common.utils.llm_connections import required_vars
        
        # Test LangChain initialization
        llm = AzureChatOpenAI(
            azure_deployment=required_vars["AZURE_OPENAI_DEPLOYMENT"],
            api_version=required_vars["AZURE_OPENAI_API_VERSION"],
            azure_endpoint=required_vars["AZURE_OPENAI_ENDPOINT"],
            api_key=required_vars["AZURE_OPENAI_API_KEY"],
            temperature=0.1,
            timeout=30,
            max_retries=1
        )
        
        template = PromptTemplate(
            input_variables=["test"],
            template="Respond with exactly: 'LANGCHAIN_OK' for: {test}"
        )
        
        chain = template | llm | StrOutputParser()
        result = chain.invoke({"test": "health check"})
        
        health_status["checks"]["langchain"] = {
            "status": "healthy" if "LANGCHAIN_OK" in result else "unhealthy",
            "response": result[:100]
        }
        
    except Exception as e:
        health_status["checks"]["langchain"] = {
            "status": "error",
            "error": str(e)
        }
    
    # Check 4: Manufacturing Assistant Initialization
    try:
        from apps.ocap.services.manufacturing_assistant import ManufacturingTechnicalAssistant
        
        # Try to initialize (but don't process messages)
        assistant = ManufacturingTechnicalAssistant()
        
        health_status["checks"]["assistant_init"] = {
            "status": "healthy",
            "details": "Manufacturing assistant initialized successfully"
        }
        
    except Exception as e:
        health_status["checks"]["assistant_init"] = {
            "status": "error",
            "error": str(e)
        }
    
    # Overall status
    check_statuses = [check.get("status", "error") for check in health_status["checks"].values()]
    if all(status == "healthy" for status in check_statuses):
        health_status["status"] = "healthy"
    elif any(status == "healthy" for status in check_statuses):
        health_status["status"] = "degraded"
    else:
        health_status["status"] = "unhealthy"
    
    # Return appropriate HTTP status
    if health_status["status"] == "unhealthy":
        raise HTTPException(status_code=503, detail=health_status)
    
    return health_status

@router.get("/ocap/test-llm")
async def test_llm_direct():
    """Direct LLM test endpoint."""
    try:
        from apps.ocap.services.manufacturing_assistant import ManufacturingTechnicalAssistant
        
        assistant = ManufacturingTechnicalAssistant()
        response = assistant.process_user_message("Hello, test message")
        
        return {
            "status": "success",
            "response": response,
            "is_fallback": "technical difficulties" in response.lower(),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        import traceback
        return {
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc(),
            "timestamp": datetime.now().isoformat()
        }
