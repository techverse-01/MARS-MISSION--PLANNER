
import math
from pydantic import BaseModel, Field

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="MARS GPS",
    description="Mars Navigation System API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.get("/")
def home():
    return {
        "system": "MARS GPS",
        "planet": "Mars",
        "status": "ONLINE",
        "version": "1.0.0"
    }

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "message": "Mars GPS backend is running"
    }

# =====================================
# PART 2 - MARS COORDINATE ENGINE
# =====================================

MARS_RADIUS_KM = 3389.5


class MarsCoordinate(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


def calculate_mars_distance(lat1, lon1, lat2, lon2):

    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2)
        * math.sin(dlon / 2) ** 2
    )

    a = max(0, min(1, a))

    c = 2 * math.asin(math.sqrt(a))

    return MARS_RADIUS_KM * c


@app.post("/mars/coordinates")
def mars_coordinates(position: MarsCoordinate):

    return {
        "planet": "Mars",
        "latitude": position.latitude,
        "longitude": position.longitude,
        "coordinate_status": "VALID"
    }


@app.post("/mars/distance")
def mars_distance_api(data: dict):

    try:
        start = MarsCoordinate(**data["start"])
        end = MarsCoordinate(**data["destination"])

    except (KeyError, TypeError, ValueError):
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail="Invalid coordinate information"
        )

    distance = calculate_mars_distance(
        start.latitude,
        start.longitude,
        end.latitude,
        end.longitude
    )

    return {
        "planet": "Mars",
        "distance_km": round(distance, 3),
        "distance_m": round(distance * 1000, 2),
        "calculation": "Great-circle distance",
        "status": "SUCCESS"
    }


