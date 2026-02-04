# validator_agent.py

import asyncio
import dotenv
import os
import subprocess
import zipfile
import shutil
import datetime
from typing import Annotated, Dict
from pydantic import Field
from agent_framework import ai_function
from agent_framework.azure import AzureOpenAIChatClient
from azure.identity import AzureCliCredential

# Configuration
ZIP_FILE = "./deliverable.zip"
SPEC_FILE = "./specs/SPEC.md"
VALIDATION_FILE = "./VALIDATION.md"
WORK_DIR = "./validation_workspace"
FIXED_ZIP = "./deliverable_fixed.zip"

VALIDATOR_INSTRUCTIONS = """
You are a principal QA engineer and Python expert.

Input: deliverable.zip containing a Python project to validate.

Task: Perform comprehensive validation of the Python project:
1) Unzip and inspect the project structure
2) Install dependencies (preferably in a venv or as editable install)
3) Run static analysis (ruff, flake8, pylint if available)
4) Run pytest with coverage if possible
5) Compare implementation against SPEC.md requirements
6) Generate a comprehensive VALIDATION.md report

Process:
1) Use unzip_project to extract deliverable.zip
2) Use read_spec to read the original SPEC.md for comparison
3) Use install_project to set up the environment and install dependencies
4) Use run_linters to execute static analysis tools
5) Use run_tests to execute pytest and gather results
6) Use compare_to_spec to analyze gaps between implementation and requirements
7) Use create_validation_report to generate VALIDATION.md with:
   - Executive summary (pass/fail)
   - Project structure analysis
   - Test results (passed/failed/skipped)
   - Linting/static analysis results
   - Coverage information (if available)
   - Gaps vs SPEC.md requirements
   - Recommendations for improvements
8) If trivial fixes are needed AND safe, use fix_and_rezip to create a fixed version
9) Return the validation report and any fixed artifacts

Guidelines:
- Be thorough but fair in assessment
- Take a limited amount of time for validation (save tokens as much as possible)
- Provide actionable feedback
- Highlight both strengths and weaknesses
- Only attempt fixes if they're trivial and safe (typos, formatting, minor bugs)
- For complex issues, recommend but don't implement
"""

@ai_function(
    name="unzip_project",
    description="Unzips the provided deliverable.zip file into a working directory.",
)
def unzip_project() -> str:
    """
    Unzips the provided deliverable.zip file into a validation workspace
    :return: Status message indicating success or failure.
    """

    if not os.path.exists(ZIP_FILE):
        return f"Error: {ZIP_FILE} does not exist."

    # Clean workspace
    if os.path.exists(WORK_DIR):
        shutil.rmtree(WORK_DIR)
    os.makedirs(WORK_DIR)

    # Extract zip
    try:
        with zipfile.ZipFile(ZIP_FILE, "r") as zip_ref:
            zip_ref.extractall(WORK_DIR)

        # Build structure tree
        structure = []
        for root, dirs, files in os.walk(WORK_DIR):
            level = root.replace(WORK_DIR, '').count(os.sep)
            indent = '  ' * level
            folder_name = os.path.basename(root) or 'project_root'
            structure.append(f"{indent}{folder_name}/")
            subindent = '  ' * (level + 1)
            for f in sorted(files):
                structure.append(f"{subindent}|-- {f}")
        return f"Project extracted to {WORK_DIR}\n\nProject structure:\n" + "\n".join(structure)
    except Exception as e:
        return f"Error extracting {ZIP_FILE}: {str(e)}"

@ai_function(
    name="read_spec",
    description="Reads the SPEC.md file for validation comparison.",
)
def read_specs() -> str:
    """
    Reads the SPEC.md file for validation comparison.
    :return: Message indicating success or failure.
    """

    if not os.path.exists(SPEC_FILE):
        return f"Error: {SPEC_FILE} does not exist."

    try:
        with open(SPEC_FILE, "r", encoding="utf-8") as f:
            content = f.read()
        return f"SPEC.md read successfully. Content length: {len(content)} characters."
    except Exception as e:
        return f"Error reading {SPEC_FILE}: {str(e)}"

@ai_function(
    name="install_project",
    description="Installs the Python project dependencies in the working directory.",
)
def install_project() -> str:
    """
    Installs the Python project dependencies in the working directory.
    :return: Status message indicating success or failure.
    """

    if not os.path.exists(WORK_DIR):
        return f"Error: {WORK_DIR} does not exist."

    # Find the project root where pyproject.toml or setup.py exists
    project_root = None
    for root, dirs, files in os.walk(WORK_DIR):
        if 'pyproject.toml' in files or 'setup.py' in files or 'setup.cfg' in files:
            project_root = root
            break

    if not project_root:
        # Check for requirements.txt
        for root, dirs, files in os.walk(WORK_DIR):
            if 'requirements.txt' in files:
                project_root = root
                break
    if not project_root:
        return f"Warning: no setup.py, pyproject.toml, or requirements.txt found. Skipping installation."

    output_lines = [f"Found project root: {project_root}"]

    try:
        # Try editable instal first
        if os.path.exists(os.path.join(project_root, 'pyproject.toml')) or os.path.exists(os.path.join(project_root, 'setup.py')):
            result = subprocess.run(
                ["pip", "install", "-e", ".", "--quiet"],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=120
            )
            if result.returncode == 0:
                output_lines.append("Project installed successfully in editable mode.")
            else:
                output_lines.append(f"Editable install failed: {result.stderr[:200]}")
                # Try requirements.txt as fallback
                if os.path.exists(os.path.join(project_root, 'requirements.txt')):
                    result = subprocess.run(
                        ["pip", "install", "-r", "requirements.txt", "--quiet"],
                        cwd=project_root,
                        capture_output=True,
                        text=True,
                        timeout=120
                    )
                    if result.returncode == 0:
                        output_lines.append("Dependencies installed successfully from requirements.txt.")
                    else:
                        output_lines.append(f"Requirements install failed: {result.stderr[:200]}")

        # Try to install dev/test dependencies
        result = subprocess.run(
            ["pip", "install", "pytest", "pytest-cov", "ruff", "--quiet"],
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode == 0:
            output_lines.append("Installed testing tools (pytest, ruff).")

        return "\n".join(output_lines)

    except subprocess.TimeoutExpired:
        return "Error: Installation process timed out."
    except Exception as e:
        return f"Error during installation: {str(e)}"

@ai_function(
    name="run_linters",
    description="Runs static analysis tools (ruff, flake8, pylint) on the project.",
)
def run_linters() -> str:
    """
    Runs static analysis tools (ruff, flake8, pylint) on the project.
    :return: Linting results.
    """

    if not os.path.exists(WORK_DIR):
        return f"Error: {WORK_DIR} does not exist."

    # Find source directories
    src_dirs = []
    for root, dirs, files in os.walk(WORK_DIR):
        if 'src' in dirs:
            src_dirs.append(os.path.join(root, 'src'))
        # Also check for top-level Python files
        if any(f.endswith('.py') for f in files):
            src_dirs.append(root)
            break

    if not src_dirs:
        return f"Error: No Python files found."

    results = []

    # Try Ruff
    try:
        for src_dir in src_dirs:
            result = subprocess.run(
                ["ruff", "check", src_dir],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                results.append(f"Ruff: No issues found in {src_dir}.")
            else:
                issue_count = len(result.stdout.split('\n')) - 1
                results.append(f"Ruff: Found {issue_count} issues in {src_dir}")
                results.append(f"\n{result.stdout[:500]}")
    except subprocess.TimeoutExpired:
        results.append("Error: Ruff timed out.")
    except FileNotFoundError:
        results.append("Ruff not installed, skipping.")
    except Exception as e:
        results.append(f"Error running Ruff: {str(e)[:100]}")

    return "\n".join(results) if results else "No linters available."

@ai_function(
    name="run_tests",
    description="Runs pytest on the project and collects test results and coverage.",
)
def run_tests() -> str:
    """
    Run pytest on the project and collects test results and coverage.
    :return: Test results including passed/failed/skipped counts and output.
    """
    if not os.path.exists(WORK_DIR):
        return f"Error: {WORK_DIR} does not exist."

    # Find the project root with tests
    test_root = None
    for root, dirs, files in os.walk(WORK_DIR):
        if 'tests' in dirs or any(f.startswith('test_') and f.endswith('.py') for f in files):
            test_root = root
            break
    if not test_root:
        return "Warning: No tests directory or test files found."

    results = []

    try:
        # Run pytest with verbose output and coverage
        result = subprocess.run(
            ["pytest", "-v", "--tb=short", "--cov", "--cov-report=term-missing"],
            cwd=test_root,
            capture_output=True,
            text=True,
            timeout=120
        )
        output = result.stdout + result.stderr

        # Parse results
        passed = output.count(' PASSED')
        failed = output.count(' FAILED')
        skipped = output.count(' SKIPPED')
        errors = output.count(' ERROR')

        results.append(f"{"OK" if result.returncode == 0 else "FAILED"} Pytest Results:")
        results.append(f"  Passed: {passed}")
        results.append(f"  Failed: {failed}")
        results.append(f"  Skipped: {skipped}")
        results.append(f"  Errors: {errors}")
        results.append(f"\nExit code: {result.returncode}")

        # Include relevant output
        if failed > 0 or errors > 0:
            results.append(f"\n Test failures/errors:\n\n{output[:1000]}\n")
        else:
            results.append(f"\n Test output:\n\n{output[:1000]}\n")
        return "\n".join(results)

    except FileNotFoundError:
        return  f"Error: pytest not installed."
    except subprocess.TimeoutExpired:
        return f"Error: tests timeout."
    except Exception as e:
        return f"Error running tests: {str(e)[:100]}"

@ai_function(
    name="compare_to_spec",
    description="Compares the project implementation against the SPEC.md requirements.",
)
def compare_to_spec(
        implementation_summary: Annotated[str, Field(description="Summary of what was implemented in the project")],
) -> str:
    """
    Compares the project implementation against the SPEC.md requirements.
    :param implementation_summary: Summary of what was implemented in the project.
    :return: Comparison results.
    """
    if not os.path.exists(SPEC_FILE):
        return f"Error: {SPEC_FILE} does not exist."
    with open(SPEC_FILE, "r", encoding="utf-8") as f:
        spec_content = f.read()

    # Return both for agent to analyze
    return f"""Specification requirements:
    {spec_content}
    Implementation summary:
    {implementation_summary}
    
    Analyze and identify:
    1. Requirements that are fully met
    2. Requirements that are partially met
    3. Requirements that are missing
    4. Additional features beyond the spec
    """

@ai_function(
    name="create_validation_report",
    description="Creates the VALIDATION.md report summarizing the validation results.",
)
def create_validation_report(
        summary: Annotated[str, Field(description="Executive summary (PASS/FAIL/PARTIAL)")],
        structure_analysis: Annotated[str, Field(description="Analysis of project structure")],
        test_results: Annotated[str, Field(description="Tests execution results")],
        lint_results: Annotated[str, Field(description="Static analysis results")],
        coverage_info: Annotated[str, Field(description="Code coverage information")],
        spec_gaps: Annotated[str, Field(description="Gaps versus SPEC.md requirements")],
        recommendations: Annotated[str, Field(description="Recommendations for improvements")],
) -> str:
    """
    Creates the VALIDATION.md report summarizing the validation results.
    :param summary: Overall validation summary.
    :param structure_analysis: Analysis of project structure.
    :param test_results: Tests execution results.
    :param lint_results: Static analysis results.
    :param coverage_info: Code coverage information.
    :param spec_gaps: Gaps versus SPEC.md requirements.
    :param recommendations: Recommendations for improvements.
    :return: Confirmation message.
    """
    content = f"""# Validation Report
    
    **Generated**: {datetime.datetime.now().isoformat()}
    
    **Project**: deliverable.zip
    
    ---
    
    ## Executive Summary
    
    {summary}
    
    ---
    
    ## Project Structure Analysis
    
    {structure_analysis}
    
    ---
    ## Test Results
    
    {test_results}
    
    ---
    
    ## Static Analysis (Linting)
    
    {lint_results}
    
    ---
    
    ## Coverage Information
    
    {coverage_info}
    
    ---
    
    ## Requirements Gap Analysis
    
    {spec_gaps}
    
    ---
    ## Recommendations
    
    {recommendations}
    
    ---
    
    ## Validation Artifacts
    - Original: `{ZIP_FILE}`
    - Workspace: `{WORK_DIR}`
    - Validation Report: `{VALIDATION_FILE}`
    """
    with open(VALIDATION_FILE, "w", encoding="utf-8") as f:
        f.write(content)
    return f"Validation report created at {VALIDATION_FILE}"

@ai_function(
    name="fix_and_rezip",
    description="Applies trivial fixes to the project and creates a new zip file.",
)
def fix_and_rezip(
        files_to_fix: Annotated[Dict[str, str], Field(description="Dictionary of file paths and their corrected content")],
) -> str:
    """
    Applies trivial fixes to the project and creates a new deliverable_fixed.zip file.
    Only use for safe, minor fixes (typos, formatting, small bugs).
    :param files_to_fix: Dictionary of {relative_file_path: corrected_content}
    :return: Status message
    """
    if not os.path.exists(WORK_DIR):
        return f"Error: {WORK_DIR} does not exist."
    if not files_to_fix:
        return "No fixes provided."

    try:
        # Apply fixes
        fixed_count = 0
        for rel_path, content in files_to_fix.items():
            full_path = os.path.join(WORK_DIR, rel_path)
            if os.path.exists(full_path):
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(content)
                fixed_count += 1

        # Create new zip
        with zipfile.ZipFile(FIXED_ZIP, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(WORK_DIR):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, WORK_DIR)
                    zipf.write(file_path, arcname=arcname)
        return f"Applied {fixed_count} fixes and created {FIXED_ZIP}"

    except Exception as e:
        return f"Error during fixing and rezipping: {str(e)}"

class ValidatorAgent:
    """
    An agent that validates a Python project deliverable against specifications.
    """
    def __init__(self, client: AzureOpenAIChatClient):
        self.agent = client.as_agent(
            name="ValidatorAgent",
            instructions=VALIDATOR_INSTRUCTIONS,
            tools=[
                unzip_project,
                read_specs,
                install_project,
                run_linters,
                run_tests,
                compare_to_spec,
                create_validation_report,
                fix_and_rezip
            ]
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

        validator_agent = ValidatorAgent(client).agent

        print("=" * 80)
        print("VALIDATOR AGENT - Project Validation & Testing")
        print("=" * 80)
        print()

        user_input = "Please validate the deliverable.zip project"

        print(f"User: {user_input}\n")
        print("-" * 80)

        response = await validator_agent.run(user_input)
        print(f"\nAgent Response:\n{response.text}")

        print("\n" + "=" * 80)

        # Verify outputs
        if os.path.exists(VALIDATION_FILE):
            print(f"Validation report created: {os.path.abspath(VALIDATION_FILE)}")
            with open(VALIDATION_FILE, "r") as f:
                print(f"\n{f.read()}")
        else:
            print(f"Validation report not found at {VALIDATION_FILE}")

        if os.path.exists(FIXED_ZIP):
            print(f"\nFixed deliverable created: {os.path.abspath(FIXED_ZIP)}")

    asyncio.run(main())
