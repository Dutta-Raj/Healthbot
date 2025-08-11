# app.py
import os
from pathlib import Path
import gradio as gr
from database import init_db, add_message, fetch_messages
from dotenv import load_dotenv

# Load .env locally (no effect on HF unless you add a .env)
load_dotenv()

# Initialize DB schema (safe to call every start)
init_db()

# Try to load a templates/index.html if present, else fall back to default HTML
HTML_FILE = Path("templates/index.html")
if HTML_FILE.exists():
    html_content = HTML_FILE.read_text(encoding="utf-8")
else:
    html_content = """
    <div style="text-align:center;">
      <h1>Welcome to My App (Hugging Face Space)</h1>
      <p>This Gradio UI wraps your previous Flask template.</p>
    </div>
    """

def refresh_messages():
    """Helper to return messages as an HTML unordered list."""
    rows = fetch_messages()
    if not rows:
        return "<p><em>No messages yet.</em></p>"
    items = "".join(f"<li>{r[1]}</li>" for r in rows)
    return f"<ul style='text-align:left; max-width:700px; margin:8px auto'>{items}</ul>"

def submit_message(msg):
    msg = (msg or "").strip()
    if not msg:
        return gr.update(value=""), refresh_messages()
    add_message(msg)
    return gr.update(value=""), refresh_messages()

with gr.Blocks() as demo:
    gr.HTML(html_content)
    gr.Markdown("## Messages (backed by DB)")
    # show current messages
    messages_html = gr.HTML(refresh_messages(), elem_id="messages-list")

    with gr.Row():
        msg_input = gr.Textbox(label="New message", placeholder="Type a short message...", lines=1)
        submit_btn = gr.Button("Add")

    # wire interactions
    submit_btn.click(fn=submit_message, inputs=msg_input, outputs=[msg_input, messages_html])
    # also allow pressing enter in textbox to submit
    msg_input.submit(fn=submit_message, inputs=msg_input, outputs=[msg_input, messages_html])

if __name__ == "__main__":
    demo.launch()
