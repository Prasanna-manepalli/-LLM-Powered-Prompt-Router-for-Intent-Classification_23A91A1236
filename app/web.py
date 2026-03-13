from typing import Optional

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse

from .router import classify_intent, route_and_respond


app = FastAPI(title="LLM Prompt Router UI")


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>LLM Prompt Router</title>
  <style>
    body {{ font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 2rem; background: #0f172a; color: #e5e7eb; }}
    h1 {{ color: #f97316; }}
    form {{ margin-bottom: 2rem; }}
    textarea {{ width: 100%; min-height: 120px; padding: 0.75rem; border-radius: 0.5rem; border: 1px solid #475569; background: #020617; color: #e5e7eb; resize: vertical; }}
    button {{ margin-top: 0.75rem; padding: 0.6rem 1.2rem; border-radius: 999px; border: none; background: #f97316; color: #0f172a; font-weight: 600; cursor: pointer; }}
    button:hover {{ background: #fb923c; }}
    .card {{ border-radius: 0.75rem; padding: 1rem 1.25rem; background: #020617; border: 1px solid #1f2937; margin-bottom: 1.25rem; }}
    .label {{ font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.08em; color: #9ca3af; margin-bottom: 0.25rem; }}
    .value {{ font-weight: 600; }}
    .muted {{ color: #9ca3af; font-size: 0.9rem; }}
    .response {{ white-space: pre-wrap; margin-top: 0.5rem; }}
  </style>
</head>
<body>
  <h1>LLM Prompt Router</h1>
  <p class="muted">Enter any message. The system will classify your intent, route it to the appropriate expert persona, and show the response.</p>
  <form method="post" action="/">
    <textarea name="message" placeholder="Ask a question about code, data, writing, or careers...">{message}</textarea>
    <br />
    <button type="submit">Send</button>
  </form>

  {result_section}
</body>
</html>
"""


def render_page(
    *, message: str = "", intent: Optional[str] = None,
    confidence: Optional[float] = None, response: Optional[str] = None
) -> HTMLResponse:
    if intent is None:
        result_html = ""
    else:
        confidence_str = f"{confidence:.2f}" if confidence is not None else "-"
        result_html = f"""
        <div class=\"card\">
          <div class=\"label\">Detected Intent</div>
          <div class=\"value\">{intent}</div>
          <div class=\"label\" style=\"margin-top:0.5rem;\">Confidence</div>
          <div class=\"value\">{confidence_str}</div>
          <div class=\"label\" style=\"margin-top:0.75rem;\">Response</div>
          <div class=\"response\">{response}</div>
        </div>
        """

    html = HTML_TEMPLATE.format(
        message=(message or ""),
        result_section=result_html,
    )
    return HTMLResponse(content=html)


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    """Render the empty form on initial page load."""

    return render_page()


@app.post("/", response_class=HTMLResponse)
async def handle_submit(message: str = Form(...)) -> HTMLResponse:
    """Handle form submissions: classify and route the user message."""

    message = message.strip()
    if not message:
        return render_page()

    intent_obj = classify_intent(message)
    response_text = route_and_respond(message, intent_obj)

    return render_page(
        message=message,
        intent=str(intent_obj.get("intent")),
        confidence=float(intent_obj.get("confidence", 0.0) or 0.0),
        response=response_text,
    )
