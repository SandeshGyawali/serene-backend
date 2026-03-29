"""
Analyzes a completed conversation session using Gemini.
Extracts: core problem, initial feelings/energy, final feelings/energy, key mindset shift.
"""
import json
import re
from google import genai
from google.genai import types as genai_types
from app.core.config import get_settings

settings = get_settings()

ANALYSIS_PROMPT = """You are a clinical-insight AI and tactical life coach. You will be given a transcript of a therapy/coaching conversation between a user and an AI companion called Serene.

Analyze the conversation carefully and return a JSON object with exactly these fields:

{
  "core_problem": "<1-2 sentences: what was the user's actual problem or concern?>",
  "initial_feelings": "<comma-separated emotional states the user expressed at the start, e.g. 'anxious, overwhelmed, self-critical'>",
  "initial_energy": "<one of: very_low | low | neutral | high | very_high — based on their tone and words at the start>",
  "final_feelings": "<comma-separated emotional states toward the end of the conversation>",
  "final_energy": "<one of: very_low | low | neutral | high | very_high — based on their tone at the end>",
  "mindset_shift": "<1-2 sentences: what perspective shift or insight emerged during the conversation, if any>",
  "progress_made": "<one of: significant | moderate | slight | none — how much positive movement happened>",
  "recommendations": ["<2-3 short actionable suggestions for the user going forward>"],
  "new_tasks": [
    {
      "activity": "<short task name, e.g. 'Morning Breathing Exercise'>",
      "time": "<HH:MM in 24-hour format, e.g. '07:00'>",
      "xp": <integer between 30 and 100 based on effort>
    }
  ]
}

For the new_tasks field: generate 3-5 personalized daily tasks based on the user's mental state, core problem, and what would genuinely help them.
- If the user is anxious: include grounding, breathing, and mindfulness tasks.
- If the user is depressed or low energy: include small wins, movement, and social connection tasks.
- If the user is in growth mode: include challenging, skill-building tasks.
- Space tasks across the day (morning, afternoon, evening).
- Keep activity names concise and actionable (under 8 words).

Only return valid JSON. No extra text."""


def analyze_session(messages: list[dict]) -> dict:
    """
    messages: list of {sender, text, timestamp}
    Returns the analysis dict.
    """
    if not messages:
        return _empty_analysis()

    # Build readable transcript
    transcript_lines = []
    for m in messages:
        label = "User" if m["sender"] == "user" else "Serene (AI)"
        transcript_lines.append(f"{label}: {m['text']}")
    transcript = "\n".join(transcript_lines)

    prompt = f"Here is the conversation transcript:\n\n{transcript}\n\nNow analyze it."

    try:
        client = genai.Client(api_key=settings.gemini_api_key)
        response = client.models.generate_content(
            model="models/gemini-2.5-flash",
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                system_instruction=ANALYSIS_PROMPT,
                response_mime_type="application/json",
                temperature=0.3,
                max_output_tokens=1024,
            ),
        )
        text = response.text.strip()
        # strip markdown fences if present
        fenced = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if fenced:
            text = fenced.group(1)
        return json.loads(text)
    except json.JSONDecodeError:
        return {"raw": text, "error": "Could not parse analysis JSON"}
    except Exception as e:
        return {"error": str(e)[:300]}


def _empty_analysis() -> dict:
    return {
        "core_problem": "Not enough conversation to analyze.",
        "initial_feelings": "unknown",
        "initial_energy": "neutral",
        "final_feelings": "unknown",
        "final_energy": "neutral",
        "mindset_shift": "No significant shift detected.",
        "progress_made": "none",
        "recommendations": [],
        "new_tasks": [],
    }
