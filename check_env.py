import os
from pathlib import Path

# Get the .env file path
env_file = Path(".env")

print(f"=== Checking .env file: {env_file.absolute()} ===")
print(f"File exists: {env_file.exists()}")
print(f"File size: {env_file.stat().st_size if env_file.exists() else 'N/A'} bytes")

if env_file.exists():
    print("\n=== .env file contents ===")
    with open(env_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if line and not line.startswith('#'):
                # Mask API keys for security
                if 'KEY' in line or 'SECRET' in line:
                    if '=' in line:
                        key, value = line.split('=', 1)
                        if value.strip():
                            masked_value = "***" + value.strip()[-4:]
                            print(f"{i:2d}: {key}={masked_value}")
                        else:
                            print(f"{i:2d}: {key}=")
                    else:
                        print(f"{i:2d}: {line}")
                else:
                    print(f"{i:2d}: {line}")
            elif line.startswith('#'):
                print(f"{i:2d}: {line}")
            else:
                print(f"{i:2d}: (empty line)")

print("\n=== Looking for Azure OpenAI variables ===")
azure_vars_found = []
if env_file.exists():
    with open(env_file, 'r', encoding='utf-8') as f:
        content = f.read()
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#') and 'AZURE_OPENAI' in line.upper():
                azure_vars_found.append(line)

if azure_vars_found:
    print("Found Azure OpenAI variables:")
    for var in azure_vars_found:
        print(f"  {var}")
else:
    print("No Azure OpenAI variables found in .env file")
    print("\nYou need to add these variables to your .env file:")
    print("AZURE_OPENAI_API_KEY=your_api_key_here")
    print("AZURE_OPENAI_ENDPOINT=your_endpoint_here")
    print("AZURE_OPENAI_DEPLOYMENT=your_deployment_name_here")
    print("AZURE_OPENAI_API_VERSION=2024-02-15-preview") 