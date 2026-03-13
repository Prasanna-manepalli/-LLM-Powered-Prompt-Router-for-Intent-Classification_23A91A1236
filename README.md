# LLM-Powered Prompt Router

This project implements an LLM-powered prompt router that classifies a user's intent and then routes the request to one of several specialized expert personas. It is written in Python and uses the Groq Python SDK for LLM access.

## Features

- Two-step flow: **classify, then respond**
- At least four expert personas (code, data, writing, career)
- Robust JSON-based intent classification with graceful fallback to `unclear`
- Routing and response generation using persona-specific system prompts
- Clarification questions for `unclear` intents (no guessing)
- JSON Lines logging to `route_log.jsonl`
- Simple CLI for interactive use or batch testing
- Dockerfile and docker-compose configuration

## Project Structure

- `app/prompts.py` – Expert persona prompts and classifier system prompt
- `app/llm_client.py` – Thin wrapper around the Groq chat completions API
- `app/router.py` – `classify_intent` and `route_and_respond` implementations plus logging
- `main.py` – CLI entrypoint (interactive mode and batch test mode)
- `requirements.txt` – Python dependencies
- `Dockerfile` – Container image definition
- `docker-compose.yml` – Simple service definition to run batch tests
- `.env.example` – Example environment variable configuration

## Setup (Local Python)

1. **Create and populate your environment file:**

  Copy the template and fill in your Groq API key:

  ```bash
  cp .env.example .env
  # then edit .env and set GROQ_API_KEY
  ```

2. **Create a virtual environment (recommended):**

   ```bash
   python -m venv .venv
   .venv\\Scripts\\activate  # Windows (PowerShell or CMD)
   # source .venv/bin/activate  # macOS / Linux
   ```

3. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. The application uses `python-dotenv` to load `.env` automatically, so you usually do **not** need to export environment variables manually.

## Running the Application

### Interactive CLI

Run the main script without arguments to enter interactive mode:

```bash
python main.py
```

- Type your message and press Enter
- The program will print the classified intent and the routed response
- Type `quit` or `exit` to leave the CLI

### Batch Test Mode

Run with `--batch-test` to classify and route a set of predefined messages (the ones listed in the assignment). This also populates `route_log.jsonl`.

```bash
python main.py --batch-test
```

Each request will be:

- Classified by `classify_intent`
- Routed via `route_and_respond`
- Logged as one JSON object per line in `route_log.jsonl`

### Simple Web UI (FastAPI)

You can also run a small web interface that lets you type messages in the
browser and see the detected intent, confidence, and final response.

1. Make sure dependencies are installed and `.env` is configured.

2. Start the web server (local Python):

  ```bash
  uvicorn app.web:app --reload
  ```

3. Open your browser at:

  - http://127.0.0.1:8000/

4. Type a message and submit. Each request still logs to `route_log.jsonl`.

## Docker Usage

Build and run with Docker:

```bash
docker build -t prompt-router .
# Ensure GROQ_API_KEY is set in your `.env` file
docker run --rm --env-file .env prompt-router
```

Or via Docker Compose:

```bash
docker-compose up --build prompt-router-web
```

This runs `python main.py --batch-test` inside the container and writes `route_log.jsonl` into the project directory (mounted as a volume).

## Core Functions

### `classify_intent(message: str) -> dict`

- Calls the LLM with a focused classifier system prompt from `app/prompts.py`
- Expects a JSON response of the form:

  ```json
  { "intent": "string", "confidence": 0.0 }
  ```

- Uses robust parsing to handle:
  - Markdown code fences
  - Extra text around the JSON
  - Malformed or non-JSON replies
- On any parsing error, returns:

  ```json
  { "intent": "unclear", "confidence": 0.0 }
  ```

### `route_and_respond(message: str, intent: dict) -> str`

- Takes the original message and the classifier output
- Applies a configurable confidence threshold (via `CONFIDENCE_THRESHOLD`, default `0.7`)
  - If below the threshold, the intent is treated as `unclear`
- If the final intent is `unclear`:
  - Returns a clarification question that invites the user to specify whether
    the request is about coding, data analysis, writing feedback, or career
    advice
- Otherwise:
  - Looks up the persona prompt in `INTENT_PROMPTS`
  - Makes a second LLM call using that system prompt plus the user message
  - Returns the generated text
- In all cases, calls are logged via `_log_routing_decision` into `route_log.jsonl`

## Logging

- The log file is `route_log.jsonl` by default (configurable with `ROUTE_LOG_PATH`)
- Each line is a standalone JSON object with at least:

  ```json
  {
    "timestamp": "...",
    "intent": "code|data|writing|career|unclear",
    "confidence": 0.0,
    "user_message": "...",
    "final_response": "..."
  }
  ```

- This format is convenient for downstream analytics and debugging.

## Extensibility

- To add another expert persona, update `INTENT_PROMPTS` and `SUPPORTED_INTENTS`
  in `app/prompts.py`, and extend the classifier instructions in
  `CLASSIFIER_SYSTEM_PROMPT`.
- You can also swap out the LLM provider by editing `app/llm_client.py` to
  integrate with another API, as long as it returns a text response.

## Notes

- Do **not** commit your real `GROQ_API_KEY` to version control.
- This project currently exposes a CLI; adding a FastAPI or Flask web API on top
  of `classify_intent` and `route_and_respond` would be a straightforward
  extension if needed.
