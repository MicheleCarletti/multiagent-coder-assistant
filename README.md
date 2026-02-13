# Multiagent Code Generation System

A sophisticated AI-powered system that automatically generates production-ready Python projects from natural language specifications using a multi-agent architecture.

## Overview

This project demonstrates a complete code generation pipeline using three specialized AI agents:

1. **RequirementsAgent** - Interactively gathers project requirements from users and produces a detailed `SPEC.md` file
2. **CoderAgent** - Generates production-ready Python code based on specifications, including source code, tests, and project metadata
3. **ValidatorAgent** - Tests and validates the generated code to ensure it meets all requirements

The orchestrator coordinates these agents into a seamless workflow that transforms user requirements into a fully functional Python project delivered as `deliverable.zip`.

## Key Features

- **Automated Code Generation**: Turn natural language specifications into complete Python projects
- **Test Generation**: Automatically create pytest test suites from acceptance criteria
- **Interactive Requirements**: Chat-based dialog to clarify requirements with the user
- **Validation**: Automated testing and validation of generated code
- **Project Packaging**: Output is automatically packaged as a deliverable ZIP file
- **Comprehensive Logging**: Detailed logs for every execution phase (stored in `./logs/`)

## Project Structure

```
coder_project/
├── src/
│   ├── agents/
│   │   ├── coder_agent.py          # Code generation agent
│   │   ├── requirements_agent.py    # Requirements gathering agent
│   │   └── validator_agent.py       # Code validation agent
│   └── orchestrator/
│       └── orechestrator.py         # Main orchestrator that coordinates agents
├── ui/
│   └── styles.css                   # Styles for web app
│   └── templates.py                 # Templates for web app
├── specs/
│   └── SPEC.md                      # Auto-generated specifications
├── main_UI.py                       # Web app entry point
├── run.sh                           # Launch the web application
├── generated_project/               # Auto-generated project output
├── validation_workspace/            # Test execution environment
├── logs/                            # Execution logs
├── requirements.txt                 # Python dependencies
└── README.md                        # This file
```

## Prerequisites

- **Python 3.11+** (Python 3.12 recommended)
- **Azure OpenAI** subscription with a deployed model (e.g., `gpt-4.1`)
- **Azure CLI** installed and authenticated (`az login`)
- **pip** package manager

## Installation

### Step 1: Create and Activate Virtual Environment (PowerShell)

```powershell
# Create virtual environment
python -m venv .venv

# Activate it
.\.venv\Scripts\Activate.ps1

```

### Step 2: Install Dependencies

```powershell
# Upgrade pip
python -m pip install --upgrade pip

# Install project dependencies
pip install -r requirements.txt
```

### Step 3: Configure Azure Credentials

Ensure you are authenticated with Azure:

```powershell
az login
```

If you have an Azure API_KEY you can use it without login required. Ensure to add it as environment variable

You must also set the Azure OpenAI endpoint. You can do this in two ways:

**Option A: Set Environment Variable (Temporary)**
```powershell
$env:AZURE_AI_PROJECT_KEY = "YOUR_API_KEY"
$env:AZURE_AI_PROJECT_ENDPOINT = "https://<your-resource>.openai.azure.com/"
$env:AZURE_AI_MODEL_DEPLOYMENT_NAME = "gpt-4.1" # or the model deployed in your Azure
```

**Option B: Create .env File (Recommended)**
Create a `.env` file in the project root:
```
AZURE_AI_PROJECT_KEY="YOUR_API_KEY"
AZURE_AI_PROJECT_ENDPOINT=https://<your-resource>.openai.azure.com/
AZURE_AI_MODEL_DEPLOYMENT_NAME = "gpt-4.1" # or the model deployed in your Azure
```

## Running the Orchestrator

### From Web App

The main entry point for the streamlit-powered application.

```powershell
run.sh
```

### From CLI

The main entry point from CLI.

```powershell
# From the project root with virtual environment activated
python  ./src/orchestrator/orechestrator.py
```

### Interactive Workflow

When you run the orchestrator, you'll enter an interactive session:

1. **Phase 1: Requirements Gathering**
   - The system will prompt you to describe your project
   - Have a conversation with the RequirementsAgent to clarify requirements
   - A `SPEC.md` file will be automatically generated

2. **Phase 2: Code Generation**
   - The CoderAgent reads `SPEC.md` and generates the complete project
   - Source code, tests, and configuration files are created
   - Output is saved in `./generated_project/`

3. **Phase 3: Validation**
   - The ValidatorAgent runs pytest tests on the generated code
   - Validates that the code meets all requirements
   - Generates a `VALIDATION.md` report

4. **Deliverable**
   - The complete project is packaged as `./deliverable.zip`
   - All logs are saved in `./logs/`

### Example Session

```powershell
PS C:\path\to\coder_project> python -m src.orchestrator.orechestrator

================================================================================
ORCHESTRATOR - Multi-Agent Code Generation System
================================================================================

User Request (describe your project requirements):
I need a Python program that reads two numbers and prints their sum.

================================================================================
PHASE 1: INTERACTIVE REQUIREMENTS GATHERING
================================================================================

RequirementsAgent: Do you need any specific error handling?
Your answer: No, just basic functionality.

RequirementsAgent: Should the program use any external libraries?
Your answer: No, standard Python only.

SPEC.md created! Moving to code generation...

================================================================================
PHASE 2: CODE GENERATION
================================================================================

CoderAgent: Generating project structure...
CoderAgent: Creating source files...
CoderAgent: Creating test suite...
CoderAgent: Packaging deliverable...

================================================================================
PHASE 3: VALIDATION
================================================================================

ValidatorAgent: Running pytest...
Test Results: 4/4 tests passed ✓

Deliverable created: C:\path\to\coder_project\deliverable.zip
```

## Output Files and Directories

After running the orchestrator, you'll find:

- **`./generated_project/`** - The complete generated Python project
  - `src/` - Application source code
  - `tests/` - Pytest test suite
  - `pyproject.toml` - Project metadata and dependencies
  - `README.md` - Instructions for the generated project

- **`./deliverable.zip`** - Compressed package ready for distribution

- **`./SPEC.md`** - Generated project specifications

- **`./VALIDATION.md`** - Test validation report

- **`./logs/orchestrator_YYYYMMDD-HHMMSS.log`** - Detailed execution log

## Troubleshooting

### Issue: "Endpoint not specified" Error

**Solution**: Set the `AZURE_AI_PROJECT_ENDPOINT` environment variable:
```powershell
$env:AZURE_AI_PROJECT_ENDPOINT = "https://<your-resource>.openai.azure.com/"
```

### Issue: "You do not have an active Azure subscription"

**Solution**: Authenticate with Azure CLI:
```powershell
az login
```

### Issue: Permission Denied on Generated Files

**Solution**: The orchestrator automatically handles permission issues, but if you encounter problems:
```powershell
Remove-Item -Path ./generated_project -Recurse -Force
Remove-Item -Path ./deliverable.zip -Force
```

Then re-run the orchestrator.

### Issue: Import Errors or Module Not Found

**Solution**: Ensure you're running from the project root and have activated the virtual environment:
```powershell
# Verify you're in the correct directory
cd C:\path\to\coder_project

# Verify virtual environment is active (should see (.venv) in prompt)
.\.venv\Scripts\Activate.ps1
```

## Development

### Adding Custom Agents

To extend the system with additional agents:

1. Create a new file in `src/agents/` (e.g., `custom_agent.py`)
2. Implement your agent following the pattern in existing agents
3. Integrate it into `src/orchestrator/orechestrator.py`

### Running Individual Agents

You can run each agent independently for testing:

```powershell
# Coder Agent (requires SPEC.md to exist)
python ./src/agents/coder_agent.py

# Validator Agent (requires generated_project/ to exist)
python ./src/agents/validator_agent.py
```

## Performance Considerations

- Initial requirements gathering: 1-3 minutes (depends on conversation length)
- Code generation: 2-5 minutes (depends on project complexity)
- Validation: 1-2 minutes (depends on test suite size)
- **Total workflow time: 5-10 minutes** for typical projects

## Best Practices

1. **Clear Requirements**: Provide detailed, clear requirements for better code generation
2. **Iterative Refinement**: Use multiple conversations to refine specifications
3. **Review Generated Code**: Always review the generated code in `./generated_project/`
4. **Test Locally**: Before using generated code in production, test it locally:
   ```powershell
   cd ./generated_project
   pip install -e .
   pytest
   ```
5. **Version Control**: Commit the generated project to git with a meaningful message

## Contributing

To contribute improvements:

1. Create a feature branch
2. Make your changes
3. Test thoroughly
4. Submit a pull request with a detailed description

