import os
import json
import httpx
from typing import List, Dict

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.5-flash:generateContent"
)

PROMPT_TEMPLATE = """Extract travel locations from the text below.

Return ONLY a valid JSON array. No markdown, no explanation, no preamble.

Format:
[
  {{"name": "Place Name", "city": "City", "country": "Country", "type": "restaurant|cafe|attraction|hotel"}}
]

Rules:
- Ignore emojis, hashtags, and irrelevant text
- Only include real, identifiable places
- If no places found, return: []

TEXT:
{input}"""


async def extract_places(text: str) -> List[Dict]:
    """Call Gemini 1.5 Flash to extract structured travel locations."""
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY not set")

    payload = {
        "contents": [
            {
                "parts": [{"text": PROMPT_TEMPLATE.format(input=text[:4000])}]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 512,
        },
    }

    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            f"{GEMINI_URL}?key={GEMINI_API_KEY}",
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

    raw = data["candidates"][0]["content"]["parts"][0]["text"].strip()

    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        places = json.loads(raw)
        if not isinstance(places, list):
            return []
        # Validate + clean each entry
        cleaned = []
        for p in places:
            if isinstance(p, dict) and p.get("name"):
                cleaned.append({
                    "name": str(p.get("name", "")).strip(),
                    "city": str(p.get("city", "")).strip(),
                    "country": str(p.get("country", "")).strip(),
                    "type": str(p.get("type", "attraction")).strip().lower(),
                })
        return cleaned
    except json.JSONDecodeError:
        return []
