import os
from dotenv import load_dotenv

print("=== Testing Environment Variable Loading ===")

# Load environment variables
load_dotenv()

print("\n1. All environment variables that start with 'AZURE_OPENAI':")
azure_vars = {k: v for k, v in os.environ.items() if k.startswith('AZURE_OPENAI')}
for key, value in azure_vars.items():
    if 'KEY' in key:
        masked_value = "***" + value[-4:] if value else "None"
        print(f"  {key}: {masked_value}")
    else:
        print(f"  {key}: {value}")

print("\n2. All environment variables that start with 'MISTRAL':")
mistral_vars = {k: v for k, v in os.environ.items() if k.startswith('MISTRAL')}
for key, value in mistral_vars.items():
    if 'KEY' in key:
        masked_value = "***" + value[-4:] if value else "None"
        print(f"  {key}: {masked_value}")
    else:
        print(f"  {key}: {value}")

print("\n3. Testing specific variable access:")
print(f"  MISTRAL_API_KEY: {'***' + os.getenv('MISTRAL_API_KEY', 'None')[-4:] if os.getenv('MISTRAL_API_KEY') else 'None'}")
print(f"  AZURE_OPENAI_API_KEY: {'***' + os.getenv('AZURE_OPENAI_API_KEY', 'None')[-4:] if os.getenv('AZURE_OPENAI_API_KEY') else 'None'}")

print("\n4. Testing if we can import parser.py:")
try:
    from common.utils.parser import client as mistral_client
    print(f"  ✓ Parser imported successfully, Mistral client: {mistral_client is not None}")
except Exception as e:
    print(f"  ✗ Error importing parser: {e}")

print("\n5. Testing if we can import llm_connections.py:")
try:
    from common.utils.llm_connections import client as azure_client
    print(f"  ✓ LLM connections imported successfully, Azure client: {azure_client is not None}")
except Exception as e:
    print(f"  ✗ Error importing llm_connections: {e}") 