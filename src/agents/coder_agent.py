# coder_agenty.py

import asyncio
import os
import dotenv
import zipfile
from typing import Annotated
from pydantic import Field
from agent_framework import ai_function
from agent_framework.azure import AzureOpenAIChatClient
from azure.identity import AzureCliCredential

SPECS_FILE = "./specs/SPEC.md"  # The file where the specifications are located
OUTPUT_DIR = "./generated_project"
ZIP_FILE = "./deliverable.zip"

CODER_INSTRUCTIONS = """
You are a principal Python engineer.

Input: SPEC.md requirements produced by the Requirements Agent.

Task: Generate a production-ready Python project with the following structure:
- src/ directory with the main application code
- tests/ directory with pytest test suite based on acceptance tests from SPEC
- pyproject.toml or setup.cfg for project configuration
- README.md with clear instructions to run locally
- .gitignore for Python projects
- Clean code with type hints and logging
- Minimal CI-ready pytest suite from acceptance tests

Process:
1) First, use read_spec_file to read the SPEC.md file
2) Analyze the requirements and plan the project structure
3) Create all necessary files using create_project_file for each file
4) After all files are created, use create_zip to package the project
5) Confirm completion

Guidelines:
- Use modern Python practices (type hints, dataclasses, pathlib, etc.)
- Include proper error handling and logging
- Write clean, maintainable code following PEP 8
- Create meaningful tests based on Given-When-Then acceptance criteria
- If you have to import modules from other directories (e.g., import src.stuff) make sure to set the correct path
- Use the python Path module to ensure setting the correct path when importing modules from other directories
- Include a comprehensive README with setup and run instructions
"""

@ai_function(
    name="read_spec_file",
    description="Reads the project specifications from the SPEC.md file and returns its content as a string.",
)
def read_spec_file() -> str:
    """
    Reads the project specifications from the SPEC.md file and returns its content as a string.
    :return: The content of the SPEC.md file.
    """
    if not os.path.exists(SPECS_FILE):
        return f"Error: {SPECS_FILE} does not exist."

    with open(SPECS_FILE, "r", encoding="utf-8") as file:
        content = file.read()
    return f"Successfully read SPEC.md: ({len(content)} characters)\n\nContent:\n{content}"

@ai_function(
    name="create_project_file",
    description="Creates a file in the project directory structure",
)
def create_project_file(
    file_path: Annotated[str, Field(description="The relative path of the file to create within the project directory (e.g., src/main.py)")],
    content: Annotated[str, Field(description="The complete content to write into the file")],
) -> str:
    """
    Creates a file in the project directory structure.
    :param file_path: Relative path where the file should be created.
    :param content: The content to write into the file.
    :return: A confirmation message.
    """
    full_path = os.path.join(OUTPUT_DIR, file_path) # Create full path
    os.makedirs(os.path.dirname(full_path), exist_ok=True)  # Ensure parent dir exists

    with open(full_path, "w", encoding="utf-8") as file:
        file.write(content)
    return f"File created successfully at {full_path} ({len(content)} characters)"

@ai_function(
    name="create_zip",
    description="Creates a zip file of the generated project directory.",
)
def create_zip() -> str:
    """
    Creates a zip file of the generated project directory.
    :return: Confirmation message with zip file location
    """
    if not os.path.exists(OUTPUT_DIR):
        return f"Error: {OUTPUT_DIR} does not exist."

    # Create a zip file
    with zipfile.ZipFile(ZIP_FILE, "w", zipfile.ZIP_DEFLATED) as zip:
        # Walk through the project directory and add files to the zip
        for root, dirs, files in os.walk(OUTPUT_DIR):
            for file in files:
                file_path = os.path.join(root, file)
                # Add file to zip with relative path
                arcname = os.path.relpath(file_path, OUTPUT_DIR)
                zip.write(file_path, arcname=arcname)

    # Get the file size in MB
    size_mb = os.path.getsize(ZIP_FILE) / (1024 * 1024)
    return f"Successfully created deliverable.zip at {os.path.abspath(ZIP_FILE)} ({size_mb:.2f} MB)"

class CoderAgent:
    """
    An agent that generates production-ready Python code from specifications
    """
    def __init__(self, client: AzureOpenAIChatClient):
        self.agent = client.as_agent(
            name="CoderAgent",
            instructions=CODER_INSTRUCTIONS,
            tools=[read_spec_file, create_project_file, create_zip]
        )


if __name__ == "__main__":
    async def main():
        dotenv.load_dotenv()
        endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
        model = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME")

        # Clean up previous outputs
        if os.path.exists(OUTPUT_DIR):
            import shutil
            shutil.rmtree(OUTPUT_DIR)

        if os.path.exists(ZIP_FILE):
            os.remove(ZIP_FILE)

        # Create output directory
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        client = AzureOpenAIChatClient(
            credential=AzureCliCredential(),
            endpoint=endpoint,
            deployment_name=model
        )

        coder_agent = CoderAgent(client)

        print("=" * 80)
        print("CODER AGENT - Python Project Generator")
        print("=" * 80)
        print()

        user_input = "Please read the SPEC.md file and generate a complete, production-ready Python project based on the requirements. Create all necessary files and then zip the project as deliverable.zip.Do not ask further questions."

        print(f"User Input: {user_input}\n")
        print("-" * 80)

        response = await coder_agent.agent.run(user_input)
        print(f"\nAgent Response:\n{response.text}")
        print("\n" + "=" * 80)

        # Verify outputs
        if os.path.exists(ZIP_FILE):
            print(f"Deliverable created: {os.path.abspath(ZIP_FILE)}")

            # List files in project
            if os.path.exists(OUTPUT_DIR):
                print(f"\nProject structure created in: {os.path.abspath(OUTPUT_DIR)}")
                print("\nGenerated files:")
                for root, dirs, files in os.walk(OUTPUT_DIR):
                    level = root.replace(OUTPUT_DIR, '').count(os.sep)
                    indent = ' ' * 2 * level
                    print(f"{indent}{os.path.basename(root)}/")
                    subindent = ' ' * 2 * (level + 1)
                    for file in files:
                        print(f"{subindent}{file}")
        else:
            print(f"Error: Deliverable not found at {ZIP_FILE}")
            print("The agent may need more guidance or the SPEC.md file may be missing.")

    asyncio.run(main())




