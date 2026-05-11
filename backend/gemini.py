import os
import json
import re
import random
import asyncio
import httpx
import instaloader

from typing import List, Dict
from urllib.parse import quote_plus

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
- Return ONLY raw JSON.

Do NOT use markdown.
Do NOT wrap in ```json
Do NOT explain anything.
- If no places found, return []

Format:
[
  {{
    "name": "Place Name",
    "city": "City",
    "country": "Country",
    "type": "restaurant|cafe|attraction|hotel",
    "summary": "Short specific reason to visit",
    "maps_query": "Place Name City Country"
  }}
]

CONTENT:
{input}
"""
# -----------------------------
# INSTAGRAM SCRAPER SETUP
# -----------------------------

L = instaloader.Instaloader(
    download_pictures=False,
    download_videos=False,
    download_video_thumbnails=False,
    save_metadata=False,
    compress_json=False,
)

# Optional future login if Instagram rate-limits
# L.login("username", "password")


def extract_shortcode(url: str) -> str:
    """
    Extract shortcode from Instagram URL.

    Supports:
    /p/
    /reel/
    /tv/
    """

    match = re.search(
        r"/(?:p|reel|tv)/([^/?#&]+)",
        url
    )

    if not match:
        raise ValueError("Invalid Instagram URL")

    return match.group(1)


async def fetch_instagram_caption(url: str) -> str:
    """
    Fetch Instagram caption + metadata using Instaloader.
    """

    try:
        # Small delay to reduce rate limiting
        await asyncio.sleep(random.uniform(1, 2))

        shortcode = extract_shortcode(url)

        post = await asyncio.to_thread(
            instaloader.Post.from_shortcode,
            L.context,
            shortcode
        )

        caption = post.caption or ""

        hashtags = " ".join(post.caption_hashtags)

        location = "None"

        if post.location:
            location = f"""
Name: {post.location.name}
Slug: {post.location.slug}
"""

        content = f"""
Instagram Post

Username:
{post.owner_username}

Post Type:
{"Reel" if post.is_video else "Post"}

Caption:
{caption}

Hashtags:
{hashtags}

Tagged Location:
{location}
"""

        print("\n========== INSTAGRAM SCRAPE ==========\n")
        print(content)
        print("\n======================================\n")

        return content.strip()

    except Exception as e:
        print(f"Instagram scraping failed: {e}")
        return ""


async def fetch_url_content(url: str) -> str:
    """
    Fetch content from URL.
    Uses specialized Instagram scraper for Instagram links.
    """

    if "instagram.com" in url:
        return await fetch_instagram_caption(url)

    try:
        async with httpx.AsyncClient(
            timeout=10,
            follow_redirects=True
        ) as client:

            headers = {
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(compatible; TravelInDex/1.0)"
                )
            }

            resp = await client.get(url, headers=headers)

            if resp.status_code == 200:
                return resp.text[:3000]

    except Exception as e:
        print(f"URL fetch failed: {e}")

    return ""


async def extract_places(text: str) -> List[Dict]:

    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY not set")

    content = text

    # If URL → fetch first
    if text.strip().startswith("http"):
        fetched = await fetch_url_content(text.strip())
        if fetched:
            content = fetched

    print("\n========== CONTENT SENT TO GEMINI ==========\n")
    print(content)
    print("\n============================================\n")

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": PROMPT_TEMPLATE.format(
                            input=content[:4000]
                        )
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0,
            "maxOutputTokens": 2048
        }
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{GEMINI_URL}?key={GEMINI_API_KEY}",
            json=payload,
        )

        resp.raise_for_status()
        data = resp.json()

    raw = (
        data["candidates"][0]
        ["content"]["parts"][0]
        ["text"]
        .strip()
    )

    print("\n========== RAW GEMINI OUTPUT ==========\n")
    print(raw)
    print("\n=======================================\n")

    # ---------------- CLEAN JSON ----------------

    def clean_json(r: str) -> str:
        r = r.strip()

        if r.startswith("```"):
            parts = r.split("```")
            r = parts[1] if len(parts) > 1 else r

            if r.startswith("json"):
                r = r[4:]

        return r.strip()

    places = []

    try:
        cleaned_raw = clean_json(raw)
        places = json.loads(cleaned_raw)

    except json.JSONDecodeError:
        print("Primary JSON parse failed. Trying recovery...")

        try:
            start = raw.find("[")
            end = raw.rfind("]")

            if start != -1 and end != -1:
                places = json.loads(raw[start:end + 1])
            else:
                return []

        except Exception as e:
            print(f"Recovery failed: {e}")
            return []

    if not isinstance(places, list):
        return []

    cleaned = []

    for p in places:

        if isinstance(p, dict) and p.get("name"):

            maps_query = (
                p.get("maps_query")
                or f"{p.get('name','')} {p.get('city','')} {p.get('country','')}"
            ).strip()

            maps_url = (
                "https://www.google.com/maps/search/?api=1&query="
                + quote_plus(maps_query)
            )

            cleaned.append({
                "name": str(p.get("name", "")).strip(),
                "city": str(p.get("city", "")).strip(),
                "country": str(p.get("country", "")).strip(),
                "type": str(p.get("type", "attraction")).strip().lower(),
                "summary": str(p.get("summary", "")).strip(),
                "maps_url": maps_url,
            })

    return cleaned

    except json.JSONDecodeError as e:

        print(f"JSON parse failed: {e}")

        return []
