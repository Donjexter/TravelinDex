from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn
import logging
import json
from datetime import datetime

from db import (
    save_places,
    get_places_by_trip,
    get_trips_by_device,
    create_trip,
    rename_trip_db,
    delete_trip_db,
    delete_place_db,
    move_place_db,
    update_place_db,
)

from gemini import extract_places

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="TravelInDex API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------
# MODELS
# -----------------------------
class UpdatePlaceRequest(BaseModel):
    device_id: str
    password: str

    name: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    type: Optional[str] = None
    summary: Optional[str] = None


class CreateTripRequest(BaseModel):
    trip_id: str
    device_id: str
    password: str


class RenameRequest(BaseModel):
    old_trip_id: str
    new_trip_id: str
    device_id: str
    password: str


class DeleteTripRequest(BaseModel):
    trip_id: str
    device_id: str
    password: str


class MoveRequest(BaseModel):
    new_trip_id: str
    device_id: str
    password: str


# -----------------------------
# HEALTH
# -----------------------------
@app.get("/health")
def health():
    return {"status": "ok", "service": "TravelInDex"}


# -----------------------------
# CREATE TRIP
# -----------------------------
@app.post("/trips/create")
async def create_trip_endpoint(req: CreateTripRequest):
    await create_trip(
        trip_id=req.trip_id,
        device_id=req.device_id,
        password=req.password,
    )
    return {"created": True, "trip_id": req.trip_id}


# -----------------------------
# SAVE (MAIN SHORTCUT ENTRY)
# -----------------------------
@app.post("/save")
async def save(request: Request):
    body = await request.body()
    logger.info(f"RAW BODY: {body.decode()}")

    try:
        data = json.loads(body)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid JSON: {e}")

    trip_id = data.get("trip_id", "")
    device_id = data.get("device_id", "")
    password = data.get("password", "")
    text = data.get("text", "") or ""
    url = data.get("url", "") or ""

    if not trip_id or not device_id or not password:
        raise HTTPException(
            status_code=422,
            detail="Missing trip_id, device_id or password"
        )

    # Handle new trip sentinel
    if trip_id in ("__new__", "➕ New Trip"):
        trip_id = f"My Trip {datetime.now().strftime('%b %Y')}"
        await create_trip(trip_id=trip_id, device_id=device_id, password=password)

    content = text or url or ""
    places = await extract_places(content)

    if not places:
        places = [{
            "name": "Saved from Instagram",
            "city": "",
            "country": "",
            "type": "attraction",
            "summary": "No location details could be extracted.",
            "maps_url": "",
        }]

    saved = await save_places(
        places=places,
        trip_id=trip_id,
        device_id=device_id,
        password=password,
        source_url=url,
    )

    return {"saved": len(saved), "places": saved}


# -----------------------------
# GET SINGLE TRIP
# -----------------------------
@app.get("/trip/{trip_id}")
async def get_trip(
    trip_id: str,
    device_id: str = Query(...),
    password: str = Query(...)
):
    places = await get_places_by_trip(
        trip_id=trip_id,
        device_id=device_id,
        password=password,
    )
    return places


# -----------------------------
# GET TRIPS LIST
# -----------------------------
@app.get("/trips/{device_id}")
async def get_trips(
    device_id: str,
    password: str = Query(...)
):
    trips = await get_trips_by_device(
        device_id=device_id,
        password=password,
    )
    trips.append("➕ New Trip")
    return trips


# -----------------------------
# RENAME TRIP
# -----------------------------
@app.post("/trips/rename")
async def rename_trip(req: RenameRequest):
    await rename_trip_db(
        req.old_trip_id,
        req.new_trip_id,
        req.device_id,
        req.password,
    )
    return {"renamed": True}


# -----------------------------
# DELETE TRIP
# -----------------------------
@app.post("/trips/delete")
async def delete_trip(req: DeleteTripRequest):
    await delete_trip_db(
        req.trip_id,
        req.device_id,
        req.password,
    )
    return {"deleted": True}


# -----------------------------
# DELETE PLACE
# -----------------------------
@app.delete("/places/{place_id}")
async def delete_place(place_id: str, request: Request):
    data = await request.json()

    await delete_place_db(
        place_id,
        data["device_id"],
        data["password"],
    )

    return {"deleted": True}


# -----------------------------
# MOVE PLACE
# -----------------------------
@app.post("/places/{place_id}/move")
async def move_place(place_id: str, req: MoveRequest):
    await move_place_db(
        place_id,
        req.new_trip_id,
        req.device_id,
        req.password,
    )
    return {"moved": True}


# -----------------------------
# UPDATE PLACE
# -----------------------------
@app.patch("/places/{place_id}")
async def update_place(place_id: int, req: UpdatePlaceRequest):

    updates = {
        "name": req.name,
        "city": req.city,
        "country": req.country,
        "type": req.type,
        "summary": req.summary,
    }

    updates = {k: v for k, v in updates.items() if v is not None}

    success = await update_place_db(
        place_id=place_id,
        device_id=req.device_id,
        password=req.password,
        updates=updates,
    )

    if not success:
        raise HTTPException(status_code=404, detail="Place not found")

    return {
        "success": True,
        "updated_fields": list(updates.keys())
    }


# -----------------------------
# RUN
# -----------------------------
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
