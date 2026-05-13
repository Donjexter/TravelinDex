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


# -----------------------------
# SAVE PLACES (NOW INCLUDES PASSWORD)
# -----------------------------
async def save_places(
    places: List[Dict],
    trip_id: str,
    device_id: str,
    password: str,
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
            "password": password,
            "summary": p.get("summary", ""),
            "maps_url": p.get("maps_url", ""),
        }
        for p in places
    ]

    result = db.table("places").insert(rows).execute()
    return result.data or []


# -----------------------------
# GET PLACES (LOGIN-LOCKED)
# -----------------------------
async def get_places_by_trip(trip_id: str, device_id: str, password: str) -> List[Dict]:
    """Return all places for a trip, scoped to device + password."""
    db = get_client()

    result = (
        db.table("places")
        .select("*")
        .eq("trip_id", trip_id)
        .eq("device_id", device_id)
        .eq("password", password)
        .order("created_at", desc=True)
        .execute()
    )

    return result.data or []


# -----------------------------
# GET TRIPS (LOGIN-LOCKED)
# -----------------------------
async def get_trips_by_device(device_id: str, password: str) -> List[str]:
    """Return unique trip names for a device + password."""
    db = get_client()

    result = (
        db.table("places")
        .select("trip_id")
        .eq("device_id", device_id)
        .eq("password", password)
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


# -----------------------------
# CREATE TRIP (NOW PASSWORD LOCKED)
# -----------------------------
async def create_trip(trip_id: str, device_id: str, password: str) -> Dict:
    """Create an empty trip by inserting a placeholder row."""
    db = get_client()

    result = db.table("places").insert({
        "trip_id": trip_id,
        "name": "__trip_created__",
        "city": "",
        "country": "",
        "type": "system",
        "source_url": "",
        "device_id": device_id,
        "password": password,
        "summary": "",
        "maps_url": "",
    }).execute()

    return result.data[0] if result.data else {}


# -----------------------------
# RENAME TRIP
# -----------------------------
async def rename_trip_db(old_trip_id: str, new_trip_id: str, device_id: str, password: str):
    db = get_client()

    db.table("places").update({"trip_id": new_trip_id}) \
        .eq("trip_id", old_trip_id) \
        .eq("device_id", device_id) \
        .eq("password", password) \
        .execute()


# -----------------------------
# DELETE TRIP
# -----------------------------
async def delete_trip_db(trip_id: str, device_id: str, password: str):
    db = get_client()

    db.table("places").delete() \
        .eq("trip_id", trip_id) \
        .eq("device_id", device_id) \
        .eq("password", password) \
        .execute()


# -----------------------------
# DELETE PLACE
# -----------------------------
async def delete_place_db(place_id: str, device_id: str, password: str):
    db = get_client()

    db.table("places").delete() \
        .eq("id", place_id) \
        .eq("device_id", device_id) \
        .eq("password", password) \
        .execute()


# -----------------------------
# MOVE PLACE
# -----------------------------
async def move_place_db(place_id: str, new_trip_id: str, device_id: str, password: str):
    db = get_client()

    db.table("places").update({"trip_id": new_trip_id}) \
        .eq("id", place_id) \
        .eq("device_id", device_id) \
        .eq("password", password) \
        .execute()


# -----------------------------
# UPDATE PLACE
# -----------------------------
async def update_place_db(place_id: int, device_id: str, password: str, updates: dict):
    db = get_client()

    result = (
        db.table("places")
        .update(updates)
        .eq("id", place_id)
        .eq("device_id", device_id)
        .eq("password", password)
        .execute()
    )

    return bool(result.data)
