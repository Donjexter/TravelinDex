from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn
import logging

from db import save_places, get_places_by_trip, get_trips_by_device
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


class SaveRequest(BaseModel):
    text: Optional[str] = None
    url: Optional[str] = None
    trip_id: str
    device_id: str


@app.get("/health")
def health():
    return {"status": "ok", "service": "TravelInDex"}


@app.post("/save/debug")
async def save_debug(request: Request):
    body = await request.body()
    logger.info(f"RAW BODY: {body.decode()}")
    return {"raw": body.decode()}


@app.post("/save")
async def save(request: Request):
    body = await request.body()
    logger.info(f"RAW BODY RECEIVED: {body.decode()}")
    
    import json
    try:
        data = json.loads(body)
    except Exception as e:
        logger.error(f"JSON parse error: {e}")
        raise HTTPException(status_code=422, detail=f"Invalid JSON: {e}")

    logger.info(f"PARSED DATA: {data}")

    trip_id = data.get("trip_id", "")
    device_id = data.get("device_id", "")
    text = data.get("text", "") or data.get("url", "") or ""

    if not trip_id or not device_id:
        raise HTTPException(status_code=422, detail=f"Missing trip_id or device_id. Got: {data}")

    places = await extract_places(text)
    if not places:
        places = [{"name": "Saved from Instagram", "city": "", "country": "", "type": "attraction"}]

    saved = await save_places(
        places=places,
        trip_id=trip_id,
        device_id=device_id,
        source_url=data.get("url", ""),
    )
    return {"saved": len(saved), "places": saved}


@app.get("/trip/{trip_id}")
async def get_trip(trip_id: str, device_id: str = Query(...)):
    places = await get_places_by_trip(trip_id=trip_id, device_id=device_id)
    return places


@app.get("/trips/{device_id}")
async def get_trips(device_id: str):
    trips = await get_trips_by_device(device_id=device_id)
    return trips


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
