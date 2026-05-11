import os
import json
import httpx
from typing import List, Dict
from urllib.parse import quote_plus
import re
import instaloader

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.5-flash:generateContent"
)

PROMPT_TEMPLATE = """You are a travel assistant.

Extract ONLY real travel-related places explicitly mentioned in the content.

Prioritize:
1. Tagged locations
2. Restaurants
3. Cafes
4. Hotels
5. Attractions

Rules:
- Only include places clearly mentioned
- Do not infer unnamed locations
- Ignore vague references
- summary max 20 words
- Return ONLY valid JSON
- If no places found, return []

Format:
[
  {
    "name": "Place Name",
    "city": "City",
    "country": "Country",
    "type": "restaurant|cafe|attraction|hotel",
    "summary": "Short specific reason to visit",
    "maps_query": "Place Name City Country"
  }
]

CONTENT:
{input}
"""

L = instaloader.Instaloader(
    download_pictures=False,
    download_videos=False,
    download_video_thumbnails=False,
    save_metadata=False,
    compress_json=False,
)

def extract_shortcode(url: str) -> str:
    """
    Extract Instagram shortcode from URL.
    Example:
    https://www.instagram.com/p/ABC123/
    -> ABC123
    """
    match = re.search(r"/(?:p|reel)/([^/?]+)/", url)

    if not match:
        raise ValueError("Invalid Instagram URL")

    return match.group(1)


async def fetch_instagram_caption(url: str) -> str:
    """
    Fetch Instagram caption and location using Instaloader.
    """

    try:
        shortcode = extract_shortcode(url)

        post = instaloader.Post.from_shortcode(
            L.context,
            shortcode
        )

        caption = post.caption or ""

        location = ""

        if post.location:
            location = f"""
Location:
Name: {post.location.name}
Slug: {post.location.slug}
"""

        hashtags = " ".join(post.caption_hashtags)

        return f"""
Instagram Post

Caption:
{caption}

Hashtags:
{hashtags}

{location}
"""

    except Exception as e:
        print(f"Instagram scraping failed: {e}")

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
            content = f"URL: {text}\n\nPage content:\n{fetched}"
    
    print("\n========== CONTENT SENT TO GEMINI ==========\n")
    print(content)
    print("\n===========================================\n")

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
