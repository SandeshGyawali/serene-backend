import json
import re
from google import genai
from google.genai import types as genai_types
from app.core.config import get_settings
from app.utils.oracle_prompt import ORACLE_SYSTEM_PROMPT, build_chat_context

settings = get_settings()
_client = None

MODEL = "models/gemini-2.5-flash"


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


def _strip_json_markdown_artifacts(text: str) -> str:
    """Remove ```json ... ``` blocks and trim — for display when the model duplicates JSON."""
    if not text:
        return text
    out = re.sub(r"```(?:json)?\s*[\s\S]*?\s*```", "", text, flags=re.IGNORECASE).strip()
    return out if out else text.strip()


def _try_decode_json_object(raw: str) -> dict | None:
    """Find a JSON object in a string (handles prose + JSON or markdown fences)."""
    raw = raw.strip()
    if not raw:
        return None
    try:
        obj = json.loads(raw)
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        pass
    for m in re.finditer(r"```(?:json)?\s*([\s\S]*?)\s*```", raw, flags=re.IGNORECASE):
        inner = m.group(1).strip()
        if inner.startswith("{"):
            try:
                obj = json.loads(inner)
                if isinstance(obj, dict):
                    return obj
            except json.JSONDecodeError:
                continue
    dec = json.JSONDecoder()
    for i, ch in enumerate(raw):
        if ch != "{":
            continue
        try:
            obj, _ = dec.raw_decode(raw, i)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            continue
    return None


def _finalize_oracle_dict(d: dict) -> dict:
    """Keep only user-facing text in `message` (no duplicate JSON / code fences)."""
    msg = d.get("message")
    if isinstance(msg, str):
        cleaned = _strip_json_markdown_artifacts(msg).strip()
        if cleaned != msg:
            d = {**d, "message": cleaned}
            msg = cleaned
        try:
            inner = json.loads(msg)
            if isinstance(inner, dict) and isinstance(inner.get("message"), str):
                d = {**d, **inner}
                d["message"] = _strip_json_markdown_artifacts(inner["message"]).strip()
        except json.JSONDecodeError:
            pass
    return d


def _extract_json(text: str) -> dict:
    if not text:
        return {"message": "", "action": "none", "actionData": None}
    obj = _try_decode_json_object(text)
    if obj is not None:
        return _finalize_oracle_dict(obj)
    cleaned = _strip_json_markdown_artifacts(text)
    return {"message": cleaned, "action": "none", "actionData": None}


def _build_contents(history: list[dict], current_input: str) -> list:
    """
    Build Gemini contents list from prior messages + new user input.
    history entries: {"sender": "user"|"serene", "text": "..."}
    Gemini roles: "user" | "model"
    """
    contents = []
    for msg in history:
        role = "user" if msg["sender"] == "user" else "model"
        contents.append(
            genai_types.Content(role=role, parts=[genai_types.Part(text=msg["text"])])
        )
    # append the new message
    contents.append(
        genai_types.Content(role="user", parts=[genai_types.Part(text=current_input)])
    )
    return contents


def ask_oracle(
    user_input: str,
    username: str,
    user_xp: int,
    level: int,
    tasks: list,
    streak: int,
    history: list = None,
) -> dict:
    """
    history: list of {"sender": "user"|"serene", "text": str} — all prior messages in this session.
    """
    client = _get_client()
    context = build_chat_context(username, user_xp, level, tasks, streak)
    system = ORACLE_SYSTEM_PROMPT + f"\n\n{context}"

    contents = _build_contents(history or [], user_input)

    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=contents,
            config=genai_types.GenerateContentConfig(
                system_instruction=system,
                temperature=0.7,
                max_output_tokens=1024,
            ),
        )
        return _extract_json(response.text)
    except Exception as e:
        return {"message": f"Oracle error: {str(e)[:300]}", "action": "none", "actionData": None}


def ask_oracle_completion(messages: list) -> str:
    """
    messages: [{"role": "user"|"assistant", "content": str}, ...]
    Maps directly to Gemini multi-turn contents.
    """
    client = _get_client()
    contents = []
    for m in messages:
        role = "user" if m["role"] == "user" else "model"
        contents.append(
            genai_types.Content(role=role, parts=[genai_types.Part(text=m["content"])])
        )
    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=contents,
            config=genai_types.GenerateContentConfig(
                system_instruction=ORACLE_SYSTEM_PROMPT,
                temperature=0.7,
                max_output_tokens=1024,
            ),
        )
        raw = _extract_json(response.text)
        msg = raw.get("message") or response.text
        if isinstance(msg, str):
            msg = _strip_json_markdown_artifacts(msg).strip()
        return msg or response.text
    except Exception as e:
        return f"Oracle error: {str(e)[:300]}"
