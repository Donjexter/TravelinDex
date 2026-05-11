from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn
import logging
import json
from db import save_places, get_places_by_trip, get_trips_by_device, create_trip
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

class CreateTripRequest(BaseModel):
    trip_id: str
    device_id: str


@app.get("/health")
def health():
    return {"status": "ok", "service": "TravelInDex"}


@app.post("/trips/create")
async def create_trip_endpoint(req: CreateTripRequest):
    """Create a new empty trip board."""
    await create_trip(trip_id=req.trip_id, device_id=req.device_id)
    return {"created": True, "trip_id": req.trip_id}


@app.post("/save")
async def save(request: Request):
    """Receive shared text + URL, extract places via Gemini, save to DB."""
    body = await request.body()
    logger.info(f"RAW BODY: {body.decode()}")

    try:
        data = json.loads(body)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid JSON: {e}")

    trip_id = data.get("trip_id", "")
    device_id = data.get("device_id", "")
    text = data.get("text", "") or ""
    url = data.get("url", "") or ""

    if not trip_id or not device_id:
        raise HTTPException(status_code=422, detail="Missing trip_id or device_id")

    # Handle "New Trip" sentinel — don't save, just return the create URL
    if trip_id in ("__new__", "➕ New Trip"):
        from datetime import datetime
        trip_id = f"My Trip {datetime.now().strftime('%b %Y')}"
        await create_trip(trip_id=trip_id, device_id=device_id)
        # fall through — trip_id is now a real name, saving continues below

    content = text or url or ""
    places = await extract_places(content)

    if not places:
        places = [{
            "name": "Saved from Instagram",
            "city": "", "country": "",
            "type": "attraction",
            "summary": "No location details could be extracted.",
            "maps_url": "",
        }]

    saved = await save_places(
        places=places,
        trip_id=trip_id,
        device_id=device_id,
        source_url=url,
    )
    return {"saved": len(saved), "places": saved}


@app.get("/trip/{trip_id}")
async def get_trip(trip_id: str, device_id: str = Query(...)):
    places = await get_places_by_trip(trip_id=trip_id, device_id=device_id)
    return places


@app.get("/trips/{device_id}")
async def get_trips(device_id: str):
    trips = await get_trips_by_device(device_id=device_id)
    trips.append("➕ New Trip")
    return trips


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
