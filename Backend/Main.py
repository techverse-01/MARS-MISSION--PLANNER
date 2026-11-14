
import math
from pydantic import BaseModel, Field

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import httpx
import xml.etree.ElementTree as ET


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

# =====================================
# PART 3A - NASA DATA CONFIGURATION
# =====================================

NASA_MARS_LAYERS = {
    "viking": {
        "name": "Viking Global Color Mosaic",
        "instrument": "Viking VIS",
        "type": "surface_imagery",
        "source": "NASA Mars Trek",
        "capabilities_url": (
            "https://api.nasa.gov/mars-wmts/catalog/"
            "Mars_Viking_MDIM21_ClrMosaic_global_232m/"
            "1.0.0/WMTSCapabilities.xml"
        )
    },

    "mola": {
        "name": "MOLA Global Elevation",
        "instrument": "Mars Orbiter Laser Altimeter",
        "type": "elevation",
        "source": "NASA Mars Trek",
        "capabilities_url": (
            "https://api.nasa.gov/mars-wmts/catalog/"
            "Mars_MGS_MOLA_DEM_mosaic_global_463m_8/"
            "1.0.0/WMTSCapabilities.xml"
        )
    },

    "themis_day": {
        "name": "THEMIS Day Infrared",
        "instrument": "Thermal Emission Imaging System",
        "type": "thermal_imagery",
        "source": "NASA Mars Trek",
        "capabilities_url": (
            "https://api.nasa.gov/mars-wmts/catalog/"
            "Mars_MO_THEMIS-IR-Day_mosaic_global_100m_v12_clon0_ly/"
            "1.0.0/WMTSCapabilities.xml"
        )
    },

    "hirise": {
        "name": "HiRISE Curiosity Landing Site Mosaic",
        "instrument": "High Resolution Imaging Science Experiment",
        "type": "high_resolution_imagery",
        "source": "NASA Mars Trek",
        "capabilities_url": (
            "https://api.nasa.gov/mars-wmts/catalog/"
            "curiosity_hirise_mosaic/"
            "1.0.0/WMTSCapabilities.xml"
        )
    },

    "ctx": {
        "name": "CTX Curiosity Landing Site Mosaic",
        "instrument": "Context Camera",
        "type": "regional_imagery",
        "source": "NASA Mars Trek",
        "capabilities_url": (
            "https://api.nasa.gov/mars-wmts/catalog/"
            "curiosity_ctx_mosaic/"
            "1.0.0/WMTSCapabilities.xml"
        )
    }
}

# =====================================
# PART 3B - NASA LAYER ENDPOINTS
# =====================================

@app.get("/nasa/layers")
def get_nasa_layers():

    return {
        "planet": "Mars",
        "provider": "NASA Mars Trek",
        "total_layers": len(NASA_MARS_LAYERS),
        "layers": NASA_MARS_LAYERS
    }


@app.get("/nasa/layers/{layer_id}")
def get_nasa_layer(layer_id: str):

    if layer_id not in NASA_MARS_LAYERS:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=404,
            detail="NASA map layer not found"
        )

    return NASA_MARS_LAYERS[layer_id]

@app.get("/nasa/layers/{layer_id}/capabilities")
async def get_nasa_layer_capabilities(layer_id: str):

    layer = NASA_MARS_LAYERS.get(layer_id)

    if not layer:
        raise HTTPException(
            status_code=404,
            detail="NASA Mars layer not found"
        )

    capabilities_url = layer["capabilities_url"]

    try:
        async with httpx.AsyncClient(
            timeout=25.0,
            follow_redirects=True
        ) as client:

            response = await client.get(capabilities_url)
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
            detail="NASA returned an invalid capabilities document"
        )



