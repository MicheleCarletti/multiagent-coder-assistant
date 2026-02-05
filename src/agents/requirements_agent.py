# requirements_agent.py

import asyncio
import dotenv
import os
from typing import Annotated
from pydantic import Field
from agent_framework import ai_function
from agent_framework.azure import AzureOpenAIChatClient
from azure.identity import AzureCliCredential

FILE_NAME = "./specs/SPEC.md"   # The file where the requirements will be saved

REQ_INSTRUCTIONS = """
You are a senior product analyst & software architect.
Goal: interview the user to extract COMPLETE, TESTABLE requirements to build a Python deliverable.

Process:
1) Ask concise, blocking questions across: goal, inputs, outputs, data, APIs, constraints, security, performance, UX/CLI, packaging, tests, delivery.
2) When information is ambiguous or missing, ask follow-ups.
3) If the user says to keep the project simple, do not ask further questions.
4) Produce a single Markdown file named SPEC.md with:
   - Executive summary
   - Scope (in/out)
   - Detailed requirements (functional/non-functional)
   - API/CLI contracts, data schemas
   - Acceptance tests (Given-When-Then)
   - Assumptions & risks
   - Milestones
Write SPEC.md to the working directory using the Code Interpreter.
Return only the file reference when done.
"""
@ai_function()
def save_file(content: Annotated[str, Field(description="Project requirements to be written in the markdown file")]) -> str:
    """
    Saves the project requirements to a file.
    :param content: The content to be saved.:
    :return:
    """
    os.makedirs(os.path.dirname(FILE_NAME) if os.path.dirname(FILE_NAME) else ".", exist_ok=True)
    with open(FILE_NAME, "w") as f:
        f.write(content)
    return f"File saved successfully to {FILE_NAME}"

class RequirementsAgent:
    """
    An agent that generates complete, testable requirements for a Python deliverable by interviewing the user.
    """
    def __init__(self, client: AzureOpenAIChatClient):
        self.agent = client.as_agent(
            name="RequirementsAgent",
            instructions=REQ_INSTRUCTIONS,
            tools=[save_file]
        )



if __name__ == "__main__":
    async def main():
        dotenv.load_dotenv()
        endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
        model = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME")


        client = AzureOpenAIChatClient(
            credential=AzureCliCredential(),
            endpoint=endpoint,
            deployment_name=model
        )

        req_agent = RequirementsAgent(client)
        agent = req_agent.agent

        user_input = "I need a Python script that print Hello World! in the terminal. DO not ask further questions."
        response = await agent.run(user_input)
        print(response)

        # Check if file was created
        if os.path.exists(FILE_NAME):
            print(f"\n✓ File created at {FILE_NAME}")
        else:
            print(f"\n✗ File not found at {FILE_NAME}")

    asyncio.run(main())

