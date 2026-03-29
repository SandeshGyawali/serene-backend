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


def _extract_json(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return {"message": text, "action": "none", "actionData": None}


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
        return raw.get("message") or response.text
    except Exception as e:
        return f"Oracle error: {str(e)[:300]}"
