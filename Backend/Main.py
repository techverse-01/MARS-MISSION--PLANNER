
import math
import xml.etree.ElementTree as ET
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from fastapi.responses import JSONResponse

# ============================================================
# PART 1 — APPLICATION SETUP
# ============================================================

app = FastAPI(
    title="MARS GPS",
    description="Mars Exploration and Navigation API",
    version="2.0.0"
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
        "version": "2.0.0"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "message": "Mars GPS backend is running"
    }


# ============================================================
# PART 2 — COORDINATES AND DISTANCE CALCULATIONS
# ============================================================

MARS_RADIUS_KM = 3389.5


class MarsCoordinate(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


def calculate_mars_distance(
    start: MarsCoordinate,
    destination: MarsCoordinate
) -> float:

    lat1 = math.radians(start.latitude)
    lat2 = math.radians(destination.latitude)

    delta_lat = math.radians(
        destination.latitude - start.latitude
    )

    delta_lon = math.radians(
        destination.longitude - start.longitude
    )

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(delta_lon / 2) ** 2
    )

    a = min(1.0, max(0.0, a))

    central_angle = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a)
    )

    return MARS_RADIUS_KM * central_angle


@app.post("/mars/coordinates")
def validate_coordinates(coordinate: MarsCoordinate):
    return {
        "valid": True,
        "latitude": coordinate.latitude,
        "longitude": coordinate.longitude,
        "planet": "Mars"
    }


class DistanceRequest(BaseModel):
    start: MarsCoordinate
    destination: MarsCoordinate


@app.post("/mars/distance")
def mars_distance(request: DistanceRequest):

    distance = calculate_mars_distance(
        request.start,
        request.destination
    )

    return {
        "distance_km": round(distance, 3),
        "planet": "Mars",
        "method": "Great-circle distance"
    }


# ============================================================
# PART 3 — NASA MAP LAYERS
# ============================================================

NASA_MARS_LAYERS = {
    "viking": {
        "name": "Viking Global Mosaic",
        "instrument": "Viking Orbiter",
        "type": "Surface imagery",
        "source": "NASA Mars Trek",
        "capabilities_url": (
            "https://api.nasa.gov/mars-wmts/catalog/"
            "Mars_Viking_MDIM21_ClrMosaic_global_232m/"
            "1.0.0/WMTSCapabilities.xml"
        )
    },
    "mola": {
        "name": "MOLA Elevation",
        "instrument": "Mars Orbiter Laser Altimeter",
        "type": "Elevation",
        "source": "NASA Mars Trek",
        "capabilities_url": (
            "https://api.nasa.gov/mars-wmts/catalog/"
            "Mars_MGS_MOLA_DEM_mosaic_global_463m_8/"
            "1.0.0/WMTSCapabilities.xml"
        )
    },
    "themis_day": {
        "name": "THEMIS Daytime Infrared",
        "instrument": "THEMIS",
        "type": "Thermal imagery",
        "source": "NASA Mars Trek",
        "capabilities_url": (
            "https://api.nasa.gov/mars-wmts/catalog/"
            "Mars_MO_THEMIS-IR-Day_mosaic_global_100m_v12_clon0_ly/"
            "1.0.0/WMTSCapabilities.xml"
        )
    },
    "hirise": {
        "name": "HiRISE Curiosity Mosaic",
        "instrument": "HiRISE",
        "type": "High-resolution imagery",
        "source": "NASA Mars Trek",
        "capabilities_url": (
            "https://api.nasa.gov/mars-wmts/catalog/"
            "curiosity_hirise_mosaic/1.0.0/WMTSCapabilities.xml"
        )
    },
    "ctx": {
        "name": "CTX Curiosity Mosaic",
        "instrument": "CTX",
        "type": "Orbital imagery",
        "source": "NASA Mars Trek",
        "capabilities_url": (
            "https://api.nasa.gov/mars-wmts/catalog/"
            "curiosity_ctx_mosaic/1.0.0/WMTSCapabilities.xml"
        )
    }
}


@app.get("/nasa/layers")
def get_nasa_layers():
    return {
        "provider": "NASA Mars Trek",
        "count": len(NASA_MARS_LAYERS),
        "layers": NASA_MARS_LAYERS
    }


@app.get("/nasa/layers/{layer_id}")
def get_nasa_layer(layer_id: str):

    layer = NASA_MARS_LAYERS.get(layer_id)

    if not layer:
        raise HTTPException(
            status_code=404,
            detail="NASA Mars layer not found"
        )

    return {
        "layer_id": layer_id,
        **layer
    }


# ============================================================
# PART 4 — NASA MAP SERVICE CAPABILITIES
# ============================================================

@app.get("/nasa/layers/{layer_id}/capabilities")
async def get_nasa_layer_capabilities(layer_id: str):

    layer = NASA_MARS_LAYERS.get(layer_id)

    if not layer:
        raise HTTPException(
            status_code=404,
            detail="NASA Mars layer not found"
        )

    try:
        async with httpx.AsyncClient(
            timeout=25.0,
            follow_redirects=True
        ) as client:

            response = await client.get(
                layer["capabilities_url"]
            )

            response.raise_for_status()

        root = ET.fromstring(response.text)

        service_title = None
        available_layers = []

        for element in root.iter():

            tag = element.tag.split("}")[-1]

            if tag == "Title" and service_title is None:
                service_title = element.text

            if tag == "Layer":

                layer_info = {}

                for child in element:
                    child_tag = child.tag.split("}")[-1]

                    if child_tag == "Identifier":
                        layer_info["identifier"] = child.text

                    elif child_tag == "Title":
                        layer_info["title"] = child.text

                if layer_info:
                    available_layers.append(layer_info)

        return {
            "status": "connected",
            "layer_id": layer_id,
            "service_title": service_title,
            "available_layers": available_layers
        }

    except httpx.HTTPError:
        raise HTTPException(
            status_code=502,
            detail="NASA map service could not be reached"
        )

    except ET.ParseError:
        raise HTTPException(
            status_code=502,
            detail="NASA returned invalid capabilities data"
        )


# ============================================================
# PART 5 — ROUTE DISTANCE AND TIME ESTIMATION
# ============================================================

class MarsRouteRequest(BaseModel):
    start: MarsCoordinate
    destination: MarsCoordinate

    waypoints: list[MarsCoordinate] = Field(
        default_factory=list,
        max_length=20
    )

    walking_speed_kmh: float = Field(
        default=4.0,
        gt=0,
        le=10
    )


@app.post("/mars/route/estimate")
def estimate_mars_route(route: MarsRouteRequest):

    points = (
        [route.start]
        + route.waypoints
        + [route.destination]
    )

    legs = []
    total_distance = 0.0

    for index in range(len(points) - 1):

        distance = calculate_mars_distance(
            points[index],
            points[index + 1]
        )

        total_distance += distance

        legs.append({
            "leg": index + 1,
            "distance_km": round(distance, 3)
        })

    estimated_hours = (
        total_distance / route.walking_speed_kmh
    )

    return {
        "status": "route_estimated",
        "planet": "Mars",
        "total_distance_km": round(total_distance, 3),
        "walking_speed_kmh": route.walking_speed_kmh,
        "estimated_travel_hours": round(
            estimated_hours, 2
        ),
        "number_of_waypoints": len(route.waypoints),
        "legs": legs,
        "warning": (
            "Straight-line distance estimate only. "
            "Terrain and obstacles are not included."
        )
    }


# ============================================================
# PART 6 — ROUTE PLANNING LIMIT CHECK
# ============================================================

class MarsSafetyRequest(BaseModel):
    start: MarsCoordinate
    destination: MarsCoordinate

    walking_speed_kmh: float = Field(
        default=4.0,
        gt=0,
        le=10
    )

    max_distance_km: float = Field(
        default=10.0,
        gt=0,
        le=100
    )

    max_travel_hours: float = Field(
        default=4.0,
        gt=0,
        le=24
    )


@app.post("/mars/route/safety-check")
def check_mars_route_safety(request: MarsSafetyRequest):

    distance = calculate_mars_distance(
        request.start,
        request.destination
    )

    travel_hours = (
        distance / request.walking_speed_kmh
    )

    distance_ok = distance <= request.max_distance_km
    time_ok = travel_hours <= request.max_travel_hours

    return {
        "planet": "Mars",
        "distance_km": round(distance, 3),
        "estimated_travel_hours": round(travel_hours, 2),
        "distance_limit_km": request.max_distance_km,
        "time_limit_hours": request.max_travel_hours,
        "fits_planning_limits": distance_ok and time_ok,
        "warnings": [
            "This is a planning-limit check, not a safety certification.",
            "Terrain, weather, radiation and obstacles are not checked."
        ]
    }


# ============================================================
# PART 7 — TERRAIN ELEVATION PROFILE
# ============================================================

class ElevationProfileRequest(BaseModel):
    elevations_m: list[float] = Field(
        min_length=2,
        max_length=500
    )

    spacing_km: float = Field(
        gt=0,
        le=100
    )


@app.post("/mars/terrain/profile")
def analyze_elevation_profile(
    request: ElevationProfileRequest
):

    elevations = request.elevations_m

    changes = [
        elevations[i + 1] - elevations[i]
        for i in range(len(elevations) - 1)
    ]

    total_distance = (
        request.spacing_km * (len(elevations) - 1)
    )

    total_elevation_change = sum(
        abs(change) for change in changes
    )

    maximum_rise = max(changes)
    maximum_drop = min(changes)

    average_absolute_change = (
        total_elevation_change / len(changes)
    )

    return {
        "planet": "Mars",
        "sample_count": len(elevations),
        "distance_km": round(total_distance, 3),
        "minimum_elevation_m": min(elevations),
        "maximum_elevation_m": max(elevations),
        "total_absolute_elevation_change_m": round(
            total_elevation_change, 2
        ),
        "average_absolute_change_per_segment_m": round(
            average_absolute_change, 2
        ),
        "largest_rise_m": round(maximum_rise, 2),
        "largest_drop_m": round(maximum_drop, 2),
        "data_note": (
            "Analysis uses elevation samples supplied in the request. "
            "It does not fetch elevation samples from NASA."
        )
    }


# ============================================================
# PART 8 — TERRAIN DIFFICULTY ESTIMATE
# ============================================================

class TerrainDifficultyRequest(BaseModel):
    elevations_m: list[float] = Field(
        min_length=2,
        max_length=500
    )

    spacing_km: float = Field(
        gt=0,
        le=100
    )


@app.post("/mars/terrain/difficulty")
def estimate_terrain_difficulty(
    request: TerrainDifficultyRequest
):

    elevations = request.elevations_m

    segment_distance_m = request.spacing_km * 1000

    slopes = []

    for i in range(len(elevations) - 1):

        vertical_change = abs(
            elevations[i + 1] - elevations[i]
        )

        slope_percent = (
            vertical_change / segment_distance_m
        ) * 100

        slopes.append(slope_percent)

    average_slope = sum(slopes) / len(slopes)
    maximum_slope = max(slopes)

    if maximum_slope < 5:
        difficulty = "LOW"
    elif maximum_slope < 15:
        difficulty = "MODERATE"
    else:
        difficulty = "HIGH"

    return {
        "terrain_difficulty_estimate": difficulty,
        "average_slope_percent": round(average_slope, 2),
        "maximum_slope_percent": round(maximum_slope, 2),
        "segment_slopes_percent": [
            round(slope, 2) for slope in slopes
        ],
        "warning": (
            "Simplified slope classification only. "
            "It is not a validated astronaut mobility model."
        )
    }


# ============================================================
# PART 9 — HAZARD LOCATION CHECKING
# ============================================================

class MarsHazard(BaseModel):
    name: str
    location: MarsCoordinate
    radius_km: float = Field(
        default=1.0,
        gt=0,
        le=100
    )
    description: str = ""


class HazardCheckRequest(BaseModel):
    route: list[MarsCoordinate] = Field(
        min_length=2,
        max_length=100
    )

    hazards: list[MarsHazard] = Field(
        default_factory=list,
        max_length=100
    )


def distance_to_route_segment(
    point: MarsCoordinate,
    start: MarsCoordinate,
    end: MarsCoordinate
) -> float:

    reference_lat = math.radians(
        (start.latitude + end.latitude + point.latitude) / 3
    )

    def project(coordinate):

        x = (
            MARS_RADIUS_KM
            * math.radians(coordinate.longitude)
            * math.cos(reference_lat)
        )

        y = (
            MARS_RADIUS_KM
            * math.radians(coordinate.latitude)
        )

        return x, y

    px, py = project(point)
    ax, ay = project(start)
    bx, by = project(end)

    dx = bx - ax
    dy = by - ay

    length_squared = dx * dx + dy * dy

    if length_squared == 0:
        return math.sqrt(
            (px - ax) ** 2 + (py - ay) ** 2
        )

    t = (
        (px - ax) * dx + (py - ay) * dy
    ) / length_squared

    t = max(0.0, min(1.0, t))

    nearest_x = ax + t * dx
    nearest_y = ay + t * dy

    return math.sqrt(
        (px - nearest_x) ** 2
        + (py - nearest_y) ** 2
    )


@app.post("/mars/hazards/check")
def check_route_hazards(request: HazardCheckRequest):

    detected = []

    for hazard in request.hazards:

        nearest_distance = min(
            distance_to_route_segment(
                hazard.location,
                request.route[i],
                request.route[i + 1]
            )
            for i in range(len(request.route) - 1)
        )

        if nearest_distance <= hazard.radius_km:

            detected.append({
                "hazard": hazard.name,
                "description": hazard.description,
                "distance_from_route_km": round(
                    nearest_distance, 3
                ),
                "hazard_radius_km": hazard.radius_km
            })

    return {
        "hazards_checked": len(request.hazards),
        "hazards_near_route": len(detected),
        "detected_hazards": detected,
        "warning": (
            "Only hazards supplied in this request are checked. "
            "This is not a complete Mars hazard database."
        )
    }


# ============================================================
# PART 10 — SCIENCE POINTS OF INTEREST
# ============================================================

class SciencePoint(BaseModel):
    name: str
    location: MarsCoordinate
    category: str
    description: str = ""


SCIENCE_POINTS = []


@app.post("/mars/science-points")
def add_science_point(point: SciencePoint):

    SCIENCE_POINTS.append(point.model_dump())

    return {
        "status": "added",
        "science_point": point.model_dump(),
        "total_points": len(SCIENCE_POINTS)
    }


@app.get("/mars/science-points")
def get_science_points():
    return {
        "count": len(SCIENCE_POINTS),
        "science_points": SCIENCE_POINTS,
        "data_note": (
            "These are user-added points, not a verified "
            "NASA science-site database."
        )
    }


# ============================================================
# PART 11 — ROUTE PLANNING WITH HAZARD CHECKS
# ============================================================

class SmartRouteRequest(BaseModel):
    start: MarsCoordinate
    destination: MarsCoordinate

    waypoints: list[MarsCoordinate] = Field(
        default_factory=list,
        max_length=20
    )

    hazards: list[MarsHazard] = Field(
        default_factory=list,
        max_length=100
    )

    walking_speed_kmh: float = Field(
        default=4.0,
        gt=0,
        le=10
    )


@app.post("/mars/route/plan")
def plan_mars_route(request: SmartRouteRequest):

    route = (
        [request.start]
        + request.waypoints
        + [request.destination]
    )

    total_distance = sum(
        calculate_mars_distance(
            route[i],
            route[i + 1]
        )
        for i in range(len(route) - 1)
    )

    travel_hours = (
        total_distance / request.walking_speed_kmh
    )

    hazard_result = check_route_hazards(
        HazardCheckRequest(
            route=route,
            hazards=request.hazards
        )
    )

    return {
        "planet": "Mars",
        "route_points": [
            point.model_dump() for point in route
        ],
        "total_distance_km": round(total_distance, 3),
        "estimated_travel_hours": round(
            travel_hours, 2
        ),
        "hazards_near_route": hazard_result[
            "hazards_near_route"
        ],
        "detected_hazards": hazard_result[
            "detected_hazards"
        ],
        "warning": (
            "This is a geometric route estimate, not an "
            "optimized or certified safe route."
        )
    }


# ============================================================
# PART 12 — MISSION PLANNER
# ============================================================

class MissionRequest(BaseModel):
    route_distance_km: float = Field(
        gt=0,
        le=10000
    )

    walking_speed_kmh: float = Field(
        default=4.0,
        gt=0,
        le=10
    )

    exploration_hours: float = Field(
        default=2.0,
        ge=0,
        le=100
    )

    rest_hours: float = Field(
        default=1.0,
        ge=0,
        le=100
    )

    number_of_stops: int = Field(
        default=0,
        ge=0,
        le=100
    )


@app.post("/mars/mission/plan")
def plan_mars_mission(request: MissionRequest):

    travel_hours = (
        request.route_distance_km
        / request.walking_speed_kmh
    )

    total_hours = (
        travel_hours
        + request.exploration_hours
        + request.rest_hours
    )

    return {
        "mission": "Mars Exploration",
        "travel_distance_km": request.route_distance_km,
        "estimated_travel_hours": round(
            travel_hours, 2
        ),
        "exploration_hours": request.exploration_hours,
        "rest_hours": request.rest_hours,
        "number_of_stops": request.number_of_stops,
        "estimated_total_mission_hours": round(
            total_hours, 2
        ),
        "warning": (
            "Planning estimate only. "
            "Life-support, power, radiation and "
            "communications constraints are not included."
        )
    }


# ============================================================
# PART 13 — FRONTEND API INFORMATION
# ============================================================

@app.get("/api/info")
def api_information():
    return {
        "application": "MARS GPS",
        "version": "2.0.0",
        "planet": "Mars",
        "documentation": "/docs",
        "main_features": [
            "NASA map layer metadata",
            "NASA map capabilities",
            "Mars coordinate validation",
            "Distance estimation",
            "Terrain profile analysis",
            "Terrain difficulty estimate",
            "Hazard checking",
            "Science points of interest",
            "Route planning",
            "Mission planning"
        ]
    }


# ============================================================
# PART 14 — SYSTEM STATUS AND ERROR HANDLING
# ============================================================

@app.get("/system/status")
def system_status():
    return {
        "backend": "ONLINE",
        "api": "ACTIVE",
        "planet": "Mars",
        "version": "2.0.0"
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "An unexpected server error occurred."
        }
    )


# ============================================================
# PART 15 — FINAL PROJECT SUMMARY
# ============================================================

@app.get("/project/summary")
def project_summary():
    return {
        "project": "MARS GPS",
        "purpose": (
            "Mars exploration mapping and route-planning prototype"
        ),
        "backend": "FastAPI",
        "status": "RUNNING",
        "features": [
            "NASA map layer metadata",
            "NASA map capabilities",
            "Mars coordinate validation",
            "Distance estimation",
            "Terrain profile analysis",
            "Terrain difficulty estimation",
            "Hazard checking",
            "Science points of interest",
            "Route planning",
            "Mission planning"
        ],
        "limitations": [
            "NASA map layers are service references, not rendered maps.",
            "Elevation analysis uses supplied samples.",
            "Hazard checking uses supplied hazard locations.",
            "Science points are user-added.",
            "Routes are not certified safe for real missions."
        ]
    }
