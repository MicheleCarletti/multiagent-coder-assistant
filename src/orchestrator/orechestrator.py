# orchestrator.py
import errno
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import asyncio
import logging
from logging import Logger
import stat
from datetime import datetime
import os
import dotenv
import shutil
from typing import Optional
from agent_framework.azure import AzureOpenAIChatClient
from azure.identity import AzureCliCredential
from azure.core.credentials import AzureKeyCredential

from src.agents.requirements_agent import  RequirementsAgent
from src.agents.coder_agent import CoderAgent
from src.agents.validator_agent import ValidatorAgent


# Configuration
ZIP_FILE = "./deliverable.zip"
SPEC_FILE = "./specs/SPEC.md"
VALIDATION_FILE = "./VALIDATION.md"
TEST_DIR = "./validation_workspace"
FIXED_ZIP = "./deliverable_fixed.zip"
OUT_DIR = "./generated_project"
LOG_DIR = "./logs"


class Orchestrator:
    """
    Orchestrator to run code generator workflow.

    RequirementsAgent -> CoderAgent -> ValidatorAgent

    """

    def __init__(
            self,
            api_key: Optional[AzureKeyCredential] = None,
            endpoint: Optional[str] = None,
            deployment_name: str = "gpt-4.1",
            credential: Optional[AzureCliCredential] = None
    ):
        """
        Initializes the Orchestrator.
        :param api_key: The Azure API key (use env variable if None)
        :param endpoint: Azure OpenAI endpoint (use env variable if None)
        :param deployment_name: Model deployment name (default gpt-4.1)
        :param credential: Azure credential (use AzureCliCredential if None)
        """
        endpoint = endpoint or os.environ.get("AZURE_AI_PROJECT_ENDPOINT")
        if not endpoint:
            raise ValueError(
                "Endpoint not specified.Please set AZURE_AI_PROJECT_ENDPOINT environment variable or pass it as a parameter."
            )
        credential = credential or AzureCliCredential()
        key = api_key or os.environ.get("AZURE_AI_PROJECT_KEY")
        self.client = AzureOpenAIChatClient(
            api_key=key,
            credential=credential,
            endpoint=endpoint,
            deployment_name=deployment_name
        )
        self.requirements_agent = RequirementsAgent(self.client).agent
        self.coder_agent = CoderAgent(self.client).agent
        self.validator_agent = ValidatorAgent(self.client).agent
        self.logger = self._setup_logging()

    @staticmethod
    def _setup_logging() -> Logger:
        """
        Configures logging with two handlers:
            - StreamHandler: prints to terminal (INFO level, minimal format)
            - FileHandler: writes to ./logs/orchestrator_<timestamps>.log (DEBUG level, detailed format)
        :return: Configured logger instance
        """
        os.makedirs(LOG_DIR, exist_ok=True)

        logger = logging.getLogger("orchestrator")
        logger.setLevel(logging.DEBUG)

        # Do not duplicate handlers if the logger is re-initialized
        logger.handlers.clear()

        # Terminal handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter("%(message)s"))

        # File log handler
        log_filename = os.path.join(LOG_DIR,
                                    f"orchestrator_{datetime.now().strftime('%Y%m%d-%H%M%S')}.log"
                                    )
        file_handler = logging.FileHandler(log_filename, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)-8s] %(message)s",
                                                    datefmt="%Y-%m-%d %H:%M:%S"
                                                    ))
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

        return logger

    def prepare_environment(self) -> None:
        """
        Prepare the environment cleaning up previous executions.
        In case of failure, tries to manage the permission
        """
        paths_to_clean = [ZIP_FILE, FIXED_ZIP, OUT_DIR, TEST_DIR, SPEC_FILE, VALIDATION_FILE, "./deliverable_fixed.zip"]

        def _on_rmtree_error(func, path: str, exc_info) -> None:
            """
            Error handler for shutil.rmtree
            In case of permission error, removes read-only flag and retries.
            """
            exc = exc_info[1]
            if exc.errno == errno.EACCES:
                self.logger.debug(f"Permission error on {path}, clearing read-only flag and retrying...")
                os.chmod(path, stat.S_IWRITE | stat.S_IREAD | stat.S_IEXEC)
                # Retry the operation
                func(path)
            else:
                self.logger.warning(f"Failed to remove {path}: {exc}")  # Generic error
                raise

        for path in paths_to_clean:
            if os.path.exists(path):
                try:
                    if os.path.isdir(path):
                        shutil.rmtree(path, onerror=_on_rmtree_error)
                    else:
                        os.remove(path)
                    self.logger.debug(f"Removed {path}")
                except Exception as e:
                    self.logger.warning(f"Could not remove {path}: {e}")

        # Create output directory
        os.makedirs(OUT_DIR, exist_ok=True)

    async def run(self, user_request: str, clean_start: bool = True) -> dict:
        """
        Run the orchestrator workflow:
            1. User defines requirements with RequirementsAgent
            2. Requirements are written to SPEC.md
            3. CoderAgent generates project based on SPEC.md
            4. ValidatorAgent tests and validates the generated project
        :param user_request: User input
        :param clean_start: If True clean previous outputs before running.
        :return:
            dict contents:
                - success: bool
                - conversation: List[ChatMessage]
                - artifacts: dict with paths of generated files
                - summary: str with execution's sum-up
        """

        if clean_start:
            self.prepare_environment()

        # Step 1: Requirements Agent
        self.logger.info("\n" + "=" * 80)
        self.logger.info("PHASE 1: INTERACTIVE REQUIREMENTS GATHERING")
        self.logger.info("=" * 80 + "\n")

        self.logger.info(f"User_request: {user_request}")

        # Start conversation
        conversation_history = [user_request]

        while not os.path.exists(SPEC_FILE):
            # Get agent response
            response = await self.requirements_agent.run(conversation_history)

            # Display agent response
            self.logger.info(f"\nRequirements Agent:\n{response.text}\n")

            # Check if SPEC.md was created
            if os.path.exists(SPEC_FILE):
                self.logger.info(f" SPEC.md created! Moving to code generation...\n")
                break

            # Agent is asking a question - get user input
            self.logger.info("-" * 80)
            user_answer = input("Your answer: ").strip()
            self.logger.debug(f"user_answer: {user_answer}")

            if not user_answer:
                user_answer = "I don't have more info. Please proceed with reasonable assumptions."

            # Update conversation history
            conversation_history.append(response.text)
            conversation_history.append(user_answer)

        # Step 2: CoderAgent
        self.logger.info("=" * 80)
        self.logger.info("PHASE 2: CODE GENERATION")
        self.logger.info("=" * 80 + "\n")

        coder_prompt = """
        Read the SPEC.md file using read_spec_file, analyze the requirements, and generate a complete production-ready Python project.
        Create all necessary files using create_project_file and then create the zip deliverable using create_zip.
        """
        self.logger.info("Starting code generation...\n")
        coder_response = await self.coder_agent.run(coder_prompt)
        self.logger.info(f"Coder Agent Response:\n{coder_response.text}\n")

        # Verify that deliverable was created
        if not os.path.exists(ZIP_FILE):
            self.logger.warning(f"Failed creating the deliverable.zip\n")
            return {
                "success": False,
                "conversation": conversation_history + [coder_prompt, coder_response.text],
                "artifacts": self.get_artifacts(),
                "summary": "Code generation failed: deliverable.zip not created"
            }

        self.logger.info(f"Code generation completed! Deliverable created at {ZIP_FILE}\n")

        # Step 3: ValidatorAgent
        self.logger.info("=" * 80)
        self.logger.info("PHASE 3: VALIDATION")
        self.logger.info("=" * 80 + "\n")

        validator_prompt = """
        Validate the deliverable.zip project. Be thorough but fair in assessment.
        Take a limited amount of time for validation (save tokens as much as possible)
        """
        self.logger.info("Starting validation...\n")
        validator_response = await self.validator_agent.run(validator_prompt)
        self.logger.info(f"Validator Agent Response:\n{validator_response.text}\n")


        # Verify artifacts
        artifacts = self.get_artifacts()

        # All artifacts are presents
        success = all([
            artifacts["spec"],
            artifacts["deliverable"],
            artifacts["validation"]
        ])

        # Create a summary
        if success:
            summary = "Workflow completed successfully. All artifacts generated."
        else:
            missing = [k for k, v in artifacts.items() if v is None]
            summary = f"Workflow incomplete. Missing artifacts: {', '.join(missing)}."

        # Build complete conversation history
        final_conversation = conversation_history + [
            coder_prompt,
            coder_response.text,
            validator_prompt,
            validator_response.text
        ]

        return {
            "success": success,
            "conversation": final_conversation,
            "artifacts": artifacts,
            "summary": summary
        }

    @staticmethod
    def get_artifacts() -> dict:
        """
        Returns the paths of generated artifacts.
        :return: dict with paths of generated files (None if not generated)
        """
        return {
            "spec": SPEC_FILE if os.path.exists(SPEC_FILE) else None,
            "deliverable": ZIP_FILE if os.path.exists(ZIP_FILE) else None,
            "validation": VALIDATION_FILE if os.path.exists(VALIDATION_FILE) else None,
            "source": OUT_DIR if os.path.exists(OUT_DIR) else None
        }

if __name__ == "__main__":
    async def main():
        dotenv.load_dotenv()
        endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
        model = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME")

        orchestrator = Orchestrator(
            endpoint=endpoint,
            deployment_name=model
        )

        orchestrator.logger.info("\n" + "=" * 80)
        orchestrator.logger.info("ORCHESTRATOR STARTED")
        orchestrator.logger.info("=" * 80 + "\n")
        orchestrator.logger.info("\nWhat do you wanna build?\n")

        user_input = input("Your request: ").strip()

        result = await orchestrator.run(user_input)

        orchestrator.logger.info("\n" + "=" * 80)
        orchestrator.logger.info("ORCHESTRATOR SUMMARY")
        orchestrator.logger.info("=" * 80 + "\n")
        orchestrator.logger.info(f"Success: {result['success']}")
        orchestrator.logger.info(f"Artifacts: {result['artifacts']}")
        orchestrator.logger.info(f"Summary: {result['summary']}\n")

    asyncio.run(main())