from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn

from db import save_places, get_places_by_trip, get_trips_by_device
from gemini import extract_places

app = FastAPI(title="TravelInDex API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)


class SaveRequest(BaseModel):
    text: str
    url: Optional[str] = None
    trip_id: str
    device_id: str


@app.get("/health")
def health():
    return {"status": "ok", "service": "TravelInDex"}


@app.post("/save")
async def save(req: SaveRequest):
    """Receive shared text + URL, extract places via Gemini, save to DB."""
    places = await extract_places(req.text)
    if not places:
        raise HTTPException(status_code=422, detail="No travel locations found in the shared content.")

    saved = await save_places(
        places=places,
        trip_id=req.trip_id,
        device_id=req.device_id,
        source_url=req.url,
    )
    return {"saved": len(saved), "places": saved}


@app.get("/trip/{trip_id}")
async def get_trip(trip_id: str, device_id: str = Query(...)):
    """Return all places saved in a specific trip for a device."""
    places = await get_places_by_trip(trip_id=trip_id, device_id=device_id)
    return places


@app.get("/trips/{device_id}")
async def get_trips(device_id: str):
    """Return list of unique trip names for a device."""
    trips = await get_trips_by_device(device_id=device_id)
    return trips


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
