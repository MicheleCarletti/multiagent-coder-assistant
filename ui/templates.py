# templates.py
"""
HTML templates for Streamlit application.
Each function returns an HTML string ready to be used with st.markdown(..., unsafe_allow_html=True)
"""

from html import escape


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
def header() -> str:
    return (
        '<div class="app-header">'
        '  <span style="font-size:1.6rem">🚀</span>'
        '  <h1>Code Generator</h1>'
        '  <span class="badge">AI-powered</span>'
        '</div>'
    )


# ---------------------------------------------------------------------------
# Phase stepper
# ---------------------------------------------------------------------------
def stepper(current_phase: int) -> str:
    """
    current_phase: 1=requirements, 2=coding, 3=validation, 4=done
    """
    phases = ["Requirements", "Coding", "Validation"]
    parts: list[str] = []

    for i, label in enumerate(phases, start=1):
        if i < current_phase:
            dot_cls, label_cls, icon = "done", "done", "✓"
        elif i == current_phase:
            dot_cls, label_cls, icon = "active", "active", str(i)
        else:
            dot_cls, label_cls, icon = "", "", str(i)

        parts.append(
            f'<div class="step">'
            f'  <div class="step-dot {dot_cls}">{icon}</div>'
            f'  <span class="step-label {label_cls}">{label}</span>'
            f'</div>'
        )
        if i < len(phases):
            conn_cls = "done" if i < current_phase else ""
            parts.append(f'<div class="step-connector {conn_cls}"></div>')

    return f'<div class="stepper">{"".join(parts)}</div>'


# ---------------------------------------------------------------------------
# Section titles
# ---------------------------------------------------------------------------
def section_title(icon: str, text: str, extra_style: str = "") -> str:
    style = f' style="{extra_style}"' if extra_style else ""
    return f'<p class="section-title"{style}>{icon} {text}</p>'


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------
def chat_area(messages: list[dict]) -> str:
    """messages: list of {role: 'user'|'agent', text: str}"""
    bubbles = []
    for msg in messages:
        css = "user" if msg["role"] == "user" else "agent"
        safe = escape(msg["text"]).replace("\n", "<br>")
        bubbles.append(f'<div class="chat-bubble {css}">{safe}</div>')
    return f'<div class="chat-area">{"".join(bubbles)}</div>'


def chat_bubble_agent(html_body: str, extra_classes: str = "") -> str:
    """Single bubble agent with generic HTML body (e.g., phase 2/3)."""
    cls = f"chat-bubble agent {extra_classes}".strip()
    return f'<div class="{cls}" style="max-width:100%">{html_body}</div>'


# ---------------------------------------------------------------------------
# Log panel
# ---------------------------------------------------------------------------
def _log_line_class(line: str) -> str:
    upper = line.upper()
    if "[WARNING" in upper:  return "log-WARNING"
    if "[ERROR"   in upper:  return "log-ERROR"
    if "[DEBUG"   in upper:  return "log-DEBUG"
    if "PHASE" in upper or line.strip().startswith("==="):
        return "log-phase"
    return "log-INFO"


def log_panel(lines: list[str], max_lines: int = 80) -> str:
    """Log panel with coloured levels."""
    html = []
    for line in lines[-max_lines:]:
        css = _log_line_class(line)
        safe = escape(line)
        html.append(f'<div class="log-line {css}">{safe}</div>')
    return f'<div class="log-panel">{"".join(html)}</div>'


def log_panel_empty() -> str:
    return (
        '<div class="log-panel">'
        '  <div class="log-line log-empty">'
        '    No log yet — start a conversation to see activity here.'
        '  </div>'
        '</div>'
    )


# ---------------------------------------------------------------------------
# Artifact cards
# ---------------------------------------------------------------------------
def artifact_card(icon: str, label: str, name: str, exists: bool) -> str:
    cls = "ok" if exists else "missing"
    return (
        f'<div class="artifact-card {cls}">'
        f'  <span class="icon">{icon}</span>'
        f'  <div>'
        f'    <div class="label">{label}</div>'
        f'    <div class="name">{name}</div>'
        f'  </div>'
        f'</div>'
    )