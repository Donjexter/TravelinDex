import os
from typing import List, Dict, Optional
from supabase import create_client, Client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

_client: Optional[Client] = None


def get_client() -> Client:
    global _client
    if _client is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client


async def save_places(
    places: List[Dict],
    trip_id: str,
    device_id: str,
    source_url: Optional[str],
) -> List[Dict]:
    """Insert extracted places into Supabase and return inserted rows."""
    db = get_client()
    rows = [
        {
            "trip_id": trip_id,
            "name": p["name"],
            "city": p.get("city", ""),
            "country": p.get("country", ""),
            "type": p.get("type", "attraction"),
            "source_url": source_url or "",
            "device_id": device_id,
            "summary": p.get("summary", ""),
            "maps_url": p.get("maps_url", ""),
        }
        for p in places
    ]
    result = db.table("places").insert(rows).execute()
    return result.data or []


async def get_places_by_trip(trip_id: str, device_id: str) -> List[Dict]:
    """Return all places for a trip, scoped to device."""
    db = get_client()
    result = (
        db.table("places")
        .select("*")
        .eq("trip_id", trip_id)
        .eq("device_id", device_id)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data or []


async def get_trips_by_device(device_id: str) -> List[str]:
    """Return unique trip names for a device, sorted alphabetically."""
    db = get_client()
    result = (
        db.table("places")
        .select("trip_id")
        .eq("device_id", device_id)
        .execute()
    )
    rows = result.data or []
    seen = set()
    trips = []
    for row in rows:
        t = row.get("trip_id", "")
        if t and t not in seen:
            seen.add(t)
            trips.append(t)
    return sorted(trips)


async def create_trip(trip_id: str, device_id: str) -> Dict:
    """Create an empty trip by inserting a placeholder row."""
    db = get_client()
    result = db.table("places").insert({
        "trip_id": trip_id,
        "name": "__trip_created__",
        "city": "", "country": "",
        "type": "system",
        "source_url": "",
        "device_id": device_id,
        "summary": "",
        "maps_url": "",
    }).execute()
    return result.data[0] if result.data else {}
