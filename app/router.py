import json
import os
from datetime import datetime, timezone
from typing import Dict, Any

from .llm_client import call_llm
from .prompts import INTENT_PROMPTS, CLASSIFIER_SYSTEM_PROMPT, SUPPORTED_INTENTS


DEFAULT_CLASSIFICATION = {"intent": "unclear", "confidence": 0.0}


def _parse_classifier_response(raw: str) -> Dict[str, Any]:
    """Best-effort parsing of the classifier JSON response.

    Handles common cases such as extra text, Markdown code fences, or
    explanations around the JSON. On any failure, returns the default
    'unclear' result without raising.
    """

    if not raw:
        return DEFAULT_CLASSIFICATION.copy()

    text = raw.strip()

    # Strip Markdown code fences if present
    if text.startswith("```"):
        # Remove leading fence and optional language tag
        lines = text.splitlines()
        if lines:
            lines = lines[1:]
        # Remove trailing fence if present
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    # First, try to parse directly
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Try to extract the JSON object between the first '{' and last '}'
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = text[start : end + 1]
            try:
                data = json.loads(candidate)
            except json.JSONDecodeError:
                return DEFAULT_CLASSIFICATION.copy()
        else:
            return DEFAULT_CLASSIFICATION.copy()

    if not isinstance(data, dict):
        return DEFAULT_CLASSIFICATION.copy()

    intent = data.get("intent", "unclear")
    confidence_raw = data.get("confidence", 0.0)

    if not isinstance(intent, str):
        intent = "unclear"

    # Normalize intent to the supported set if possible
    intent = intent.strip().lower()
    if intent not in SUPPORTED_INTENTS:
        intent = "unclear"

    # Best-effort conversion of confidence to float
    try:
        confidence = float(confidence_raw)
    except (TypeError, ValueError):
        confidence = 0.0

    # Clamp to [0.0, 1.0]
    if confidence < 0.0:
        confidence = 0.0
    if confidence > 1.0:
        confidence = 1.0

    return {"intent": intent, "confidence": confidence}


def classify_intent(message: str) -> Dict[str, Any]:
    """Classify the user's intent using a lightweight LLM call.

    Returns a dict with keys 'intent' (str) and 'confidence' (float). Any
    malformed or non-JSON response results in a safe default of
    {"intent": "unclear", "confidence": 0.0}.
    """

    classifier_model = os.getenv("CLASSIFIER_MODEL") or os.getenv("GROQ_MODEL")
    raw = call_llm(CLASSIFIER_SYSTEM_PROMPT, message, model=classifier_model)
    result = _parse_classifier_response(raw)
    return result


def _log_routing_decision(
    *, intent: str, confidence: float, user_message: str, final_response: str
) -> None:
    """Append a single JSON object representing one routing decision.

    The log file uses JSON Lines format, one object per line.
    """

    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "intent": intent,
        "confidence": confidence,
        "user_message": user_message,
        "final_response": final_response,
    }

    log_path = os.getenv("ROUTE_LOG_PATH", "route_log.jsonl")

    try:
        # Ensure directory exists if a nested path is provided
        log_dir = os.path.dirname(log_path)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    except (OSError, PermissionError):
        # Fallback to /tmp in serverless/read-only environments like Vercel
        try:
            tmp_path = os.path.join("/tmp", "route_log.jsonl")
            with open(tmp_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception:
            pass


def route_and_respond(message: str, intent_obj: Dict[str, Any]) -> str:
    """Route the message to the appropriate expert persona and respond.

    Parameters
    ----------
    message: str
        The original user message.
    intent_obj: Dict[str, Any]
        Output from classify_intent, with at least 'intent' and 'confidence'.

    Returns
    -------
    str
        The final response text.
    """

    intent_label = str(intent_obj.get("intent", "unclear")).strip().lower()
    confidence = float(intent_obj.get("confidence", 0.0) or 0.0)

    # Optional confidence threshold: below this, treat as 'unclear'.
    threshold_env = os.getenv("CONFIDENCE_THRESHOLD")
    try:
        threshold = float(threshold_env) if threshold_env is not None else 0.7
    except ValueError:
        threshold = 0.7

    if intent_label != "unclear" and confidence < threshold:
        intent_label = "unclear"

    if intent_label == "unclear":
        final_response = (
            "I am not completely sure what you need help with. "
            "Are you asking for assistance with coding, data analysis, "
            "writing feedback, or career advice? Please clarify so I can "
            "route your request to the right assistant."
        )
        _log_routing_decision(
            intent=intent_label,
            confidence=confidence,
            user_message=message,
            final_response=final_response,
        )
        return final_response

    system_prompt = INTENT_PROMPTS.get(intent_label)

    # Fallback safety: if we somehow lack a prompt, treat as unclear.
    if not system_prompt:
        final_response = (
            "I could not find a suitable expert persona for your request. "
            "Can you confirm whether this is about coding, data analysis, "
            "writing feedback, or career advice?"
        )
        _log_routing_decision(
            intent="unclear",
            confidence=confidence,
            user_message=message,
            final_response=final_response,
        )
        return final_response

    # Use the expert system prompt for the final response
    response_text = call_llm(system_prompt, message)
    final_response = response_text.strip() if response_text else ""

    _log_routing_decision(
        intent=intent_label,
        confidence=confidence,
        user_message=message,
        final_response=final_response,
    )

    return final_response
