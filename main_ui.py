# main.py

import asyncio
import os
import time
from pathlib import Path

import dotenv
import streamlit as st

from ui import templates as T
from src.orchestrator.orechestrator import Orchestrator

# Config PATHS
SPEC_FILE = "./specs/SPEC.md"
ZIP_FILE = "./deliverable.zip"
VALIDATION_FILE = "./VALIDATION.md"
LOG_DIR = "./logs"

# Streamlit page config
st.set_page_config(
    page_title="Coder Assistant",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Load .css file
CSS_PATH = Path(__file__).parent / "./ui/styles.css"
st.markdown(f"<style>{CSS_PATH.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

# Async helper
def run_async(coro):
    """ Run an async coroutine from sync Streamlit code"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, coro).result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)

# Log file helper
def get_latest_log_file() -> str | None:
    log_dir = Path(LOG_DIR)
    if not log_dir.exists():
        return None
    logs = sorted(log_dir.glob("orchestrator_*.log"), key=os.path.getmtime)
    return  str(logs[-1]) if logs else None

def read_log(path: str | None) -> list[str]:
    if not path or not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return f.read().splitlines()

# Session-state init
SESSION_DEFAULTS = {
    "phase":            1,  # 1=requirements | 2=coding | 3=validation | 4=done
    "chat_messages":    [], # [{role, text}, ...]
    "conversation_history": [], # raw list fed to the agent
    "orchestrator":     None,
    "log_file":         None,
    "error":            None,
}

def init_session():
    for k,v, in SESSION_DEFAULTS.items():
        if k not in st.session_state:
            st.session_state[k] = v

# Phase handlers
# Phase 1: requirements
def phase_requirements(orchestrator_col):
    """ Phase 1 - interactive chat with RequirementsAgent"""
    with orchestrator_col:
        st.markdown(T.section_title("📝","What do you wanna build?"), unsafe_allow_html=True)

        if st.session_state["chat_messages"]:
            st.markdown(T.chat_area(st.session_state["chat_messages"]), unsafe_allow_html=True)

        # Use a dynamic key to force streamlit's chat widget initialization at every user's message
        if "input_counter" not in st.session_state:
            st.session_state["input_counter"] = 0


        user_input = st.text_input(
            "Your message",
            label_visibility="collapsed",
            placeholder="e.g., I need a REST API with authentication...",
            key=f"req_input_{st.session_state['input_counter']}",   # Dynamic key
            on_change=lambda: st.session_state.update({"input_submitted": True})
        )

        send_clicked = st.button("Send", use_container_width=True)

        # Check if Enter or Send button clicked
        input_submitted = st.session_state.get("input_submitted", False) or send_clicked

        if not (input_submitted and user_input.strip()):
            return

        # Clean flag and buffer
        st.session_state["input_submitted"] = False

        # First message -> boot orchestrator
        if st.session_state["orchestrator"] is None:
            orch = Orchestrator()
            orch.prepare_environment()
            st.session_state["orchestrator"] = orch
            st.session_state["log_file"] = get_latest_log_file()

        orch = st.session_state["orchestrator"]

        # User bubble + agent call
        st.session_state["chat_messages"].append({"role": "user", "text": user_input.strip()})
        st.session_state["conversation_history"].append(user_input.strip())

        # Increase the counter to change the key at the next return
        st.session_state["input_counter"] += 1

        with st.spinner("Requirements Agent is thinking..."):
            response = run_async(
                orch.requirements_agent.run(st.session_state["conversation_history"])
            )
        agent_text = response.text
        orch.logger.info(f"Requirements Agent:\n{agent_text}")

        st.session_state["chat_messages"].append({"role": "agent", "text": agent_text})
        st.session_state["conversation_history"].append(agent_text)

        # if SPEC.md has been created -> phase 2
        if os.path.exists(SPEC_FILE):
            orch.logger.info("SPEC.md created! Moving to code generation…")
            st.session_state["phase"] = 2

        st.rerun()
def phase_coding(orchestrator_col):
    """Phase 2 — run CoderAgent."""
    with orchestrator_col:
        st.markdown(T.section_title("⚙️", "Code Generation"), unsafe_allow_html=True)
        st.markdown(
            T.chat_bubble_agent(
                'The <strong>Coder Agent</strong> is generating your project from the spec…<br>'
                '<em style="color:#64748b">This may take a minute.</em>'
            ),
            unsafe_allow_html=True,
        )

    orch = st.session_state["orchestrator"]
    coder_prompt = (
        "Read the SPEC.md file using read_spec_file, analyze the requirements, "
        "and generate a complete production-ready Python project. "
        "Create all necessary files using create_project_file "
        "and then create the zip deliverable using create_zip."
    )
    orch.logger.info("=" * 60)
    orch.logger.info("PHASE 2: CODE GENERATION")
    orch.logger.info("=" * 60)

    with st.spinner("Generating code…"):
        coder_response = run_async(orch.coder_agent.run(coder_prompt))

    orch.logger.info(f"Coder Agent Response:\n{coder_response.text}")

    if not os.path.exists(ZIP_FILE):
        orch.logger.warning("Failed creating deliverable.zip")
        st.session_state["error"] = "Code generation failed: deliverable.zip was not created."
        st.session_state["phase"] = 4
    else:
        orch.logger.info(f"Code generation completed! Deliverable created at {ZIP_FILE}")
        st.session_state["phase"] = 3

    st.rerun()


def phase_validation(orchestrator_col):
    """Phase 3 — run ValidatorAgent."""
    with orchestrator_col:
        st.markdown(T.section_title("🔍", "Validation"), unsafe_allow_html=True)
        st.markdown(
            T.chat_bubble_agent(
                'The <strong>Validator Agent</strong> is checking your deliverable…<br>'
                '<em style="color:#64748b">Running tests and generating the report.</em>'
            ),
            unsafe_allow_html=True,
        )

    orch = st.session_state["orchestrator"]
    validator_prompt = (
        "Validate the deliverable.zip project. Be thorough but fair in assessment. "
        "Take a limited amount of time for validation (save tokens as much as possible)."
        "You cannot ask anything to the user."
    )
    orch.logger.info("=" * 60)
    orch.logger.info("PHASE 3: VALIDATION")
    orch.logger.info("=" * 60)

    with st.spinner("Validating…"):
        validator_response = run_async(orch.validator_agent.run(validator_prompt))

    orch.logger.info(f"Validator Agent Response:\n{validator_response.text}")
    st.session_state["phase"] = 4
    st.rerun()


def phase_done(orchestrator_col):
    """Phase 4 — results + download."""
    with orchestrator_col:
        error = st.session_state.get("error")

        if error:
            st.markdown(T.chat_bubble_agent(f"⚠️  {error}", extra_classes="error"), unsafe_allow_html=True)
        else:
            st.markdown(T.section_title("✅", "All Done"), unsafe_allow_html=True)
            st.markdown(
                T.chat_bubble_agent("Your project has been generated and validated successfully!", extra_classes="success"),
                unsafe_allow_html=True,
            )

        # artifact cards
        st.markdown(T.section_title("📦", "Artifacts", extra_style="margin-top:18px"), unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(T.artifact_card("📄", "Specification",  "SPEC.md",           os.path.exists(SPEC_FILE)),              unsafe_allow_html=True)
            st.markdown(T.artifact_card("📦", "Deliverable",    "deliverable.zip",    os.path.exists(ZIP_FILE)),               unsafe_allow_html=True)
        with c2:
            st.markdown(T.artifact_card("✅", "Validation",     "VALIDATION.md",      os.path.exists(VALIDATION_FILE)),        unsafe_allow_html=True)
            st.markdown(T.artifact_card("📁", "Source",         "generated_project/", os.path.exists("./generated_project")),  unsafe_allow_html=True)

        # download
        if os.path.exists(ZIP_FILE):
            with open(ZIP_FILE, "rb") as f:
                st.download_button(
                    label="⬇️  Download deliverable.zip",
                    data=f,
                    file_name="deliverable.zip",
                    mime="application/zip",
                    use_container_width=True,
                )

        # restart
        if st.button("🔄  Start a new project", use_container_width=True):
            st.session_state.clear()
            st.rerun()


# Log panel (right column)
def render_log_column(log_col):
    with log_col:
        st.markdown(T.section_title("🖥️", "Live orchestrator log"), unsafe_allow_html=True)

        log_file  = st.session_state.get("log_file") #or get_latest_log_file()
        log_lines = read_log(log_file)

        # Debug info
        if log_file:
            st.caption(f"📁 Log file: `{log_file}` ({len(log_lines)} lines)")
        else:
            st.caption("📁 No log file found in `./logs/`")

        html = T.log_panel(log_lines) if log_lines else T.log_panel_empty()
        st.markdown(html, unsafe_allow_html=True)

        # auto-refresh during coding / validation
        if st.session_state["phase"] in (2, 3):
            time.sleep(2)
            st.rerun()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    dotenv.load_dotenv()
    init_session()

    # header + stepper
    st.markdown(T.header(),                          unsafe_allow_html=True)
    st.markdown(T.stepper(st.session_state["phase"]), unsafe_allow_html=True)

    # layout
    chat_col, log_col = st.columns([3, 2], gap="medium")

    # dispatch for phase
    PHASE_HANDLERS = {
        1: phase_requirements,
        2: phase_coding,
        3: phase_validation,
        4: phase_done,
    }
    PHASE_HANDLERS[st.session_state["phase"]](chat_col)

    # Log panel
    render_log_column(log_col)


if __name__ == "__main__":
    main()




