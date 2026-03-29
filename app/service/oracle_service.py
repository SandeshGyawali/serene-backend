import json
import re
from datetime import datetime, timedelta, timezone
from google import genai
from google.genai import types as genai_types
from app.core.config import get_settings
from app.utils.oracle_prompt import ORACLE_SYSTEM_PROMPT, SCHEDULE_OPTIMIZER_PROMPT, build_chat_context
from app.service.oracle_tools import TaskOracleTools
from sqlalchemy.orm import Session

settings = get_settings()
_client = None

MODEL = "models/gemini-2.5-flash"


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


def _get_nepal_time() -> str:
    # Nepal is UTC +5:45
    off = timezone(timedelta(hours=5, minutes=45))
    return datetime.now(off).strftime("%H:%M")


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
    db: Session = None,
) -> dict:
    """
    history: list of {"sender": "user"|"serene", "text": str} — all prior messages in this session.
    """
    client = _get_client()
    now_nepal = _get_nepal_time()
    context = build_chat_context(username, user_xp, level, tasks, streak, current_time=now_nepal)
    system = ORACLE_SYSTEM_PROMPT + f"\n\n{context}"

    contents = _build_contents(history or [], user_input)

    tools_helper = None
    tools_list = None
    if db:
        tools_helper = TaskOracleTools(db, username)
        tools_list = tools_helper.get_tools()

    try:
        config = genai_types.GenerateContentConfig(
            system_instruction=system,
            temperature=0.7,
            max_output_tokens=1024,
            tools=tools_list
        )
        response = client.models.generate_content(
            model=MODEL,
            contents=contents,
            config=config,
        )
        
        if response.function_calls:
            contents.append(response.candidates[0].content)
            
            func_response_parts = []
            if tools_helper:
                for fc in response.function_calls:
                     result_str = tools_helper.execute_tool(fc.name, fc.args)
                     func_response_parts.append(
                         genai_types.Part.from_function_response(
                             name=fc.name,
                             response={"result": result_str}
                         )
                     )
            contents.append(genai_types.Content(role="user", parts=func_response_parts))
            
            response = client.models.generate_content(
                model=MODEL,
                contents=contents,
                config=config,
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


def optimize_schedule_after_chat(
    username: str,
    analysis: dict,
    tasks: list,
    db: Session
) -> dict:
    """Invoked after conversation analysis. Autonomously edits user's schedule if needed."""
    from app.service import task_service
    
    # CRITICAL: Snapshot current tasks before making ANY changes
    task_service.save_planner_snapshot(db, username)
    
    client = _get_client()
    
    # Build schedule snippet
    schedule_text = "\n".join([f"- {t['time']} | {t['activity']}" for t in tasks])
    now_nepal = _get_nepal_time()
    
    prompt = f"""CURRENT TIME (NEPAL): {now_nepal}

LATEST CONVERSATION ANALYSIS:
{json.dumps(analysis, indent=2)}

CURRENT SCHEDULE FOR TODAY:
{schedule_text or '(no tasks today)'}

Based on this, review the schedule. Call tools if you need to create, edit, or delete tasks.
Include a JSON summary in the format specified in your system prompt."""

    tools_helper = TaskOracleTools(db, username)
    tools_list = tools_helper.get_tools()
    
    contents = [
        genai_types.Content(role="user", parts=[genai_types.Part(text=prompt)])
    ]
    
    try:
        config = genai_types.GenerateContentConfig(
            system_instruction=SCHEDULE_OPTIMIZER_PROMPT,
            temperature=0.3,
            max_output_tokens=1024,
            tools=tools_list
        )
        response = client.models.generate_content(
            model=MODEL,
            contents=contents,
            config=config,
        )
        
        # Tool execution loop
        if response.function_calls:
            contents.append(response.candidates[0].content)
            
            func_response_parts = []
            for fc in response.function_calls:
                 result_str = tools_helper.execute_tool(fc.name, fc.args)
                 func_response_parts.append(
                     genai_types.Part.from_function_response(
                         name=fc.name,
                         response={"result": result_str}
                     )
                 )
            contents.append(genai_types.Content(role="user", parts=func_response_parts))
            
            response = client.models.generate_content(
                model=MODEL,
                contents=contents,
                config=config,
            )

        return _extract_json(response.text)
    except Exception as e:
        return {"summary": "Schedule optimizer error.", "changes_made": [f"Error: {str(e)[:100]}"]}
