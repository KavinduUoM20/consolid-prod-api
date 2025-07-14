"""
LLM connections for Azure OpenAI integration
"""
import os
from openai import AzureOpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Check for required environment variables
required_vars = {
    "AZURE_OPENAI_API_KEY": os.getenv("AZURE_OPENAI_API_KEY"),
    "AZURE_OPENAI_API_VERSION": os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
    "AZURE_OPENAI_ENDPOINT": os.getenv("AZURE_OPENAI_ENDPOINT"),
    "AZURE_OPENAI_DEPLOYMENT": os.getenv("AZURE_OPENAI_DEPLOYMENT")
}

missing_vars = [key for key, value in required_vars.items() if not value]
if missing_vars:
    raise ValueError(
        f"Missing required environment variables: {', '.join(missing_vars)}\n"
        "Please add these to your .env file:\n"
        "AZURE_OPENAI_API_KEY=your_api_key\n"
        "AZURE_OPENAI_ENDPOINT=your_endpoint (e.g., https://your-resource.openai.azure.com/)\n"
        "AZURE_OPENAI_DEPLOYMENT=your_deployment_name\n"
        "AZURE_OPENAI_API_VERSION=2024-02-15-preview (or your preferred version)"
    )

client = AzureOpenAI(
    api_key=required_vars["AZURE_OPENAI_API_KEY"],
    api_version=required_vars["AZURE_OPENAI_API_VERSION"],
    azure_endpoint=required_vars["AZURE_OPENAI_ENDPOINT"]
)

def ask_llm(prompt):
    try:
        completion = client.chat.completions.create(
            model=required_vars["AZURE_OPENAI_DEPLOYMENT"],
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3  # Lower temperature for more focused responses
        )
        return completion.choices[0].message.content
    except Exception as e:
        error_msg = f"Error calling Azure OpenAI: {str(e)}"
        print(error_msg)  # For logging
        raise Exception(error_msg)


def ask_llm_with_system_prompt(system_prompt: str, user_prompt: str, temperature: float = 0.3, max_tokens: int = None) -> str:
    """
    Ask Azure OpenAI LLM with a system prompt and user prompt
    
    Args:
        system_prompt: The system prompt that defines the LLM's behavior
        user_prompt: The user's question or prompt
        temperature: Controls randomness (0.0 = deterministic, 1.0 = very random)
        max_tokens: Maximum number of tokens in the response (optional)
        
    Returns:
        The LLM's response as a string
        
    Raises:
        Exception: If there's an error calling Azure OpenAI
    """
    try:
        # Prepare the request parameters
        request_params = {
            "model": required_vars["AZURE_OPENAI_DEPLOYMENT"],
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature
        }
        
        # Add max_tokens if specified
        if max_tokens:
            request_params["max_tokens"] = max_tokens
        
        # Make the API call
        completion = client.chat.completions.create(**request_params)
        
        return completion.choices[0].message.content
        
    except Exception as e:
        error_msg = f"Error calling Azure OpenAI: {str(e)}"
        print(error_msg)  # For logging
        raise Exception(error_msg)


def is_llm_available() -> bool:
    """
    Check if LLM is available by testing the connection
    
    Returns:
        True if LLM is available, False otherwise
    """
    try:
        # Simple test prompt
        test_response = ask_llm("Hello")
        return True
    except Exception:
        return False 