import os
import json
import httpx
from typing import List, Dict
from urllib.parse import quote_plus

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.5-flash:generateContent"
)

PROMPT_TEMPLATE = """You are a travel assistant. Extract travel locations from the content below.

Return ONLY a valid JSON array. No markdown, no explanation, no preamble.

Format:
[
  {{
    "name": "Place Name",
    "city": "City",
    "country": "Country",
    "type": "restaurant|cafe|attraction|hotel",
    "summary": "One compelling sentence about why this place is worth visiting, max 20 words",
    "maps_query": "Place Name City Country"
  }}
]

Rules:
- Only include real, identifiable places
- summary must be specific and useful, not generic
- maps_query should be the best search string to find this on Google Maps
- If no places found, return: []

CONTENT:
{input}"""


FACEBOOK_TOKEN = os.getenv("1971481300174118|kmQNkM2g080YILdzyEaSGIJNYQU")

async def fetch_instagram_caption(url: str) -> str:
    """Fetch Instagram post caption via oEmbed API."""
    try:
        oembed_url = (
            f"https://graph.facebook.com/v18.0/instagram_oembed"
            f"?url={url}&access_token={FACEBOOK_TOKEN}&fields=author_name,title"
        )
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(oembed_url)
            if resp.status_code == 200:
                data = resp.json()
                title = data.get("title", "")
                author = data.get("author_name", "")
                if title:
                    return f"Instagram post by {author}: {title}"
    except Exception:
        pass
    return url


async def fetch_url_content(url: str) -> str:
    """Fetch content from URL — uses oEmbed for Instagram."""
    if "instagram.com" in url:
        return await fetch_instagram_caption(url)
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            headers = {"User-Agent": "Mozilla/5.0 (compatible; TravelInDex/1.0)"}
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                return resp.text[:3000]
    except Exception:
        pass
    return url


async def extract_places(text: str) -> List[Dict]:
    """Call Gemini 2.5 Flash to extract structured travel locations."""
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY not set")

    # If input looks like a URL, try to fetch its content first
    content = text
    if text.strip().startswith("http"):
        fetched = await fetch_url_content(text.strip())
        if fetched != text:
            content = f"URL: {text}\n\nPage content: {fetched}"

    payload = {
        "contents": [
            {
                "parts": [{"text": PROMPT_TEMPLATE.format(input=content[:4000])}]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 1024,
        },
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{GEMINI_URL}?key={GEMINI_API_KEY}",
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

    raw = data["candidates"][0]["content"]["parts"][0]["text"].strip()

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        places = json.loads(raw)
        if not isinstance(places, list):
            return []
        cleaned = []
        for p in places:
            if isinstance(p, dict) and p.get("name"):
                maps_query = p.get("maps_query") or f"{p.get('name', '')} {p.get('city', '')} {p.get('country', '')}".strip()
                maps_url = f"https://www.google.com/maps/search/?api=1&query={quote_plus(maps_query)}"
                cleaned.append({
                    "name": str(p.get("name", "")).strip(),
                    "city": str(p.get("city", "")).strip(),
                    "country": str(p.get("country", "")).strip(),
                    "type": str(p.get("type", "attraction")).strip().lower(),
                    "summary": str(p.get("summary", "")).strip(),
                    "maps_url": maps_url,
                })
        return cleaned
    except json.JSONDecodeError:
        return []
