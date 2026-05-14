# db.py

import os
from typing import List, Dict, Optional
from supabase import create_client, Client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

_client: Optional[Client] = None


# ---------------------------------------------------
# CLIENT
# ---------------------------------------------------

def get_client() -> Client:

    global _client

    if _client is None:

        if not SUPABASE_URL or not SUPABASE_KEY:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_SERVICE_KEY must be set"
            )

        _client = create_client(
            SUPABASE_URL,
            SUPABASE_KEY
        )

    return _client


# ---------------------------------------------------
# SAVE PLACES
# ---------------------------------------------------

async def save_places(
    places: List[Dict],
    trip_id: str,
    device_id: str,
    password: str,
    source_url: Optional[str],
) -> List[Dict]:

    db = get_client()

    rows = []

    for p in places:

        rows.append({
            "trip_id": trip_id,
            "name": p.get("name", ""),
            "city": p.get("city", ""),
            "country": p.get("country", ""),
            "type": p.get("type", "attraction"),
            "summary": p.get("summary", ""),
            "maps_url": p.get("maps_url", ""),
            "source_url": source_url or "",
            "device_id": device_id,
            "password": password,
        })

    result = (
        db.table("places")
        .insert(rows)
        .execute()
    )

    return result.data or []


# ---------------------------------------------------
# GET PLACES
# ---------------------------------------------------

async def get_places_by_trip(
    trip_id: str,
    device_id: str,
    password: str
) -> List[Dict]:

    db = get_client()

    result = (
        db.table("places")
        .select("*")
        .eq("trip_id", trip_id)
        .eq("device_id", device_id)
        .eq("password", password)
        .neq("name", "__trip_created__")
        .order("created_at", desc=True)
        .execute()
    )

    return result.data or []


# ---------------------------------------------------
# GET TRIPS
# ---------------------------------------------------

async def get_trips_by_device(
    device_id: str,
    password: str
) -> List[str]:

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

        trip = row.get("trip_id")

        if trip and trip not in seen:
            seen.add(trip)
            trips.append(trip)

    return sorted(trips)


# ---------------------------------------------------
# CREATE TRIP
# ---------------------------------------------------

async def create_trip(
    trip_id: str,
    device_id: str,
    password: str
) -> Dict:

    db = get_client()

    result = (
        db.table("places")
        .insert({
            "trip_id": trip_id,
            "name": "__trip_created__",
            "city": "",
            "country": "",
            "type": "system",
            "summary": "",
            "maps_url": "",
            "source_url": "",
            "device_id": device_id,
            "password": password,
        })
        .execute()
    )

    return result.data[0] if result.data else {}


# ---------------------------------------------------
# RENAME TRIP
# ---------------------------------------------------

async def rename_trip_db(
    old_trip_id: str,
    new_trip_id: str,
    device_id: str,
    password: str
):

    db = get_client()

    (
        db.table("places")
        .update({
            "trip_id": new_trip_id
        })
        .eq("trip_id", old_trip_id)
        .eq("device_id", device_id)
        .eq("password", password)
        .execute()
    )


# ---------------------------------------------------
# DELETE TRIP
# ---------------------------------------------------

async def delete_trip_db(
    trip_id: str,
    device_id: str,
    password: str
):

    db = get_client()

    (
        db.table("places")
        .delete()
        .eq("trip_id", trip_id)
        .eq("device_id", device_id)
        .eq("password", password)
        .execute()
    )


# ---------------------------------------------------
# DELETE PLACE
# ---------------------------------------------------

async def delete_place_db(
    place_id: str,
    device_id: str,
    password: str
):

    db = get_client()

    (
        db.table("places")
        .delete()
        .eq("id", place_id)
        .eq("device_id", device_id)
        .eq("password", password)
        .execute()
    )


# ---------------------------------------------------
# MOVE PLACE
# ---------------------------------------------------

async def move_place_db(
    place_id: str,
    new_trip_id: str,
    device_id: str,
    password: str
):

    db = get_client()

    (
        db.table("places")
        .update({
            "trip_id": new_trip_id
        })
        .eq("id", place_id)
        .eq("device_id", device_id)
        .eq("password", password)
        .execute()
    )


# ---------------------------------------------------
# UPDATE PLACE
# ---------------------------------------------------

async def update_place_db(
    place_id: str,
    device_id: str,
    password: str,
    updates: dict
):

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
