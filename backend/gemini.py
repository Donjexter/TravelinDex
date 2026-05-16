import os
import json
import re
import random
import asyncio
import httpx
import instaloader
from typing import List, Dict, Optional
from urllib.parse import quote_plus

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_URL = (
"https://generativelanguage.googleapis.com/v1beta/models/"
"gemini-3.1-flash-lite:generateContent"
)

PROMPT_TEMPLATE = """You are a travel assistant.

Extract ONLY real travel-related places explicitly mentioned in the content.

Prioritize:

1. Tagged locations
1. Restaurants
1. Cafes
1. Hotels
1. Attractions
1. Sightseeing
1. Retail
1. Hiking

Rules:

- Only include places clearly mentioned
- Do not infer unnamed locations
- Ignore vague references
- summary max 20 words
- Return ONLY raw JSON.
  Do NOT use markdown.
  Do NOT wrap in '''json
  Do NOT explain anything.
- If no places found, return []

Format:
[
{{
"name": "Place Name",
"city": "City",
"country": "Country",
"type": "restaurant|cafe|attraction|hotel|sightseeing|retail|hiking",
"summary": "Short specific reason to visit",
"maps_query": "Place Name City Country"
}}
]

CONTENT:
{input}
"""

# —————————–

# INSTAGRAM SCRAPER SETUP

# —————————–

L = instaloader.Instaloader(
download_pictures=False,
download_videos=False,
download_video_thumbnails=False,
save_metadata=False,
compress_json=False,
)

CAPTION_MIN_LENGTH = 150  # trigger OCR when caption shorter than this

def extract_shortcode(url: str) -> str:
match = re.search(r"/(?:p|reel|tv)/([^/?#&]+)", url)
if not match:
raise ValueError("Invalid Instagram URL")
return match.group(1)

async def download_image_bytes(url: str) -> Optional[bytes]:
"""Download image bytes from a URL."""
try:
async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
headers = {
"User-Agent": (
"Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
"AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 "
"Mobile/15E148 Safari/604.1"
)
}
resp = await client.get(url, headers=headers)
if resp.status_code == 200:
return resp.content
except Exception as e:
print(f"Image download failed: {e}")
return None

def ocr_image_bytes(image_bytes: bytes) -> str:
"""
Run OCR on raw image bytes.
Tries easyocr first (better accuracy), falls back to pytesseract.
Returns extracted text or empty string.
"""
ocr_text = ""

'''
# --- Try easyocr ---
try:
    import easyocr
    import numpy as np
    from PIL import Image
    import io

    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img_np = np.array(img)

    # Initialise reader (English; cached after first call)
    reader = easyocr.Reader(["en"], gpu=False, verbose=False)
    results = reader.readtext(img_np, detail=0, paragraph=True)
    ocr_text = " ".join(results).strip()

except ImportError:
    pass  # easyocr not installed, try pytesseract
except Exception as e:
    print(f"easyocr failed: {e}")

if ocr_text:
    return ocr_text

# --- Fallback: pytesseract ---
try:
    import pytesseract
    from PIL import Image
    import io

    img = Image.open(io.BytesIO(image_bytes))
    ocr_text = pytesseract.image_to_string(img).strip()
except ImportError:
    print("Neither easyocr nor pytesseract is installed. Skipping OCR.")
except Exception as e:
    print(f"pytesseract failed: {e}")

return ocr_text
'''

async def ocr_post_images(post) -> str:
"""
Download and OCR all images from a post (single or carousel).
Returns combined OCR text, or empty string if nothing useful found.
"""
image_urls: List[str] = []

'''
try:
    if post.typename == "GraphSidecar":
        # Carousel — collect all node image URLs
        nodes = await asyncio.to_thread(
            lambda: list(post.get_sidecar_nodes())
        )
        for node in nodes:
            if not node.is_video:
                image_urls.append(node.display_url)
    elif not post.is_video:
        # Single image
        image_urls.append(post.url)
except Exception as e:
    print(f"Could not collect image URLs: {e}")
    return ""

if not image_urls:
    return ""

print(f"\n[OCR] Downloading {len(image_urls)} image(s)…")

ocr_parts: List[str] = []
for i, url in enumerate(image_urls):
    img_bytes = await download_image_bytes(url)
    if not img_bytes:
        continue
    text = await asyncio.to_thread(ocr_image_bytes, img_bytes)
    if text:
        print(f"[OCR] Image {i+1}: {text[:120]}…")
        ocr_parts.append(text)

return "\n".join(ocr_parts).strip()
'''

async def fetch_instagram_caption(url: str) -> str:
try:
await asyncio.sleep(random.uniform(1, 2))
shortcode = extract_shortcode(url)
post = await asyncio.to_thread(
instaloader.Post.from_shortcode,
L.context,
shortcode
)

'''
    caption = post.caption or ""
    hashtags = " ".join(post.caption_hashtags)

    location = "None"
    if post.location:
        location = (
            f"Name: {post.location.name}\n"
            f"Slug: {post.location.slug}"
        )

    # --- OCR if caption is short ---
    ocr_section = ""
    if len(caption.strip()) < CAPTION_MIN_LENGTH:
        print(
            f"[OCR] Caption is short ({len(caption.strip())} chars), "
            "running OCR on post images…"
        )
        ocr_text = await ocr_post_images(post)
        if ocr_text:
            ocr_section = (
                "\n\nText extracted from post images "
                "(ignore if nonsensical or irrelevant — "
                "may include background signage, menus, or unrelated text):\n"
                + ocr_text
            )

    content = (
        f"Instagram Post\n\n"
        f"Username:\n{post.owner_username}\n\n"
        f"Post Type:\n{'Reel' if post.is_video else 'Post'}\n\n"
        f"Caption:\n{caption}\n\n"
        f"Hashtags:\n{hashtags}\n\n"
        f"Tagged Location:\n{location}"
        f"{ocr_section}"
    )

    print("\n========== INSTAGRAM SCRAPE ==========\n")
    print(content)
    print("\n======================================\n")

    return content.strip()

except Exception as e:
    print(f"Instagram scraping failed: {e}")
    return ""
'''

async def fetch_url_content(url: str) -> str:
if "instagram.com" in url:
return await fetch_instagram_caption(url)
try:
async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
headers = {
"User-Agent": "Mozilla/5.0 (compatible; TravelInDex/1.0)"
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

'''
content = text
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
    if r.startswith("'''"):
        parts = r.split("'''")
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
'''
