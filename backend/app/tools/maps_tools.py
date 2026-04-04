import httpx
import asyncio
import math
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from app.config.settings import settings
from app.core.state import RouteInfo

logger = logging.getLogger(__name__)

# ========================= INPUT SCHEMAS ========================= #

class LocationInput(BaseModel):
    """Input schema for single location queries."""
    location: str = Field(..., description="Location name (e.g., 'London', 'New York, USA')")

class RouteInput(BaseModel):
    """Input schema for route queries."""
    origin: str = Field(..., description="Starting location name")
    destination: str = Field(..., description="Destination location name")
    transport_mode: str = Field(
        default="driving",
        description="Transport mode: 'driving', 'walking', 'cycling', or 'public_transport'"
    )

class TravelOptionsInput(BaseModel):
    """Input schema for comprehensive travel options."""
    origin: str = Field(..., description="Starting location name")
    destination: str = Field(..., description="Destination location name")
    date: str = Field(..., description="Travel date in YYYY-MM-DD format")
    checkin: Optional[str] = Field(None, description="Hotel check-in date (YYYY-MM-DD)")
    checkout: Optional[str] = Field(None, description="Hotel check-out date (YYYY-MM-DD)")

class FlightInput(BaseModel):
    """Input schema for flight searches."""
    origin_code: str = Field(..., description="Origin airport code (e.g., 'DEL', 'BOM')")
    dest_code: str = Field(..., description="Destination airport code")
    date: str = Field(..., description="Departure date in YYYY-MM-DD format")

class TrainInput(BaseModel):
    """Input schema for train searches."""
    from_station: str = Field(..., description="Origin station code")
    to_station: str = Field(..., description="Destination station code")
    date: str = Field(..., description="Journey date in YYYY-MM-DD format")

class BusInput(BaseModel):
    """Input schema for bus searches."""
    origin: str = Field(..., description="Origin city name")
    destination: str = Field(..., description="Destination city name")
    date: str = Field(..., description="Journey date in YYYY-MM-DD format")

class HotelInput(BaseModel):
    """Input schema for hotel searches."""
    location: str = Field(..., description="Location to search for hotels")
    checkin: str = Field(..., description="Check-in date (YYYY-MM-DD)")
    checkout: str = Field(..., description="Check-out date (YYYY-MM-DD)")

# ========================= HELPER FUNCTIONS ========================= #

class MapsServiceHelpers:
    """Shared helper functions for maps tools."""
    
    # Transport mode mapping
    TRANSPORT_MODES = {
        "driving": "driving-car",
        "walking": "foot-walking",
        "cycling": "cycling-regular",
        "public_transport": "driving-car"  # fallback
    }
    
    # RapidAPI hosts
    SKYSCANNER_HOST = "skyscanner44.p.rapidapi.com"
    TRAINS_HOST = "indian-railway-irctc.p.rapidapi.com"
    BUSES_HOST = "redbus2.p.rapidapi.com"
    HOTELS_HOST = "booking-com.p.rapidapi.com"
    
    @staticmethod
    def calculate_haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points using Haversine formula (returns km)."""
        lat1, lon1 = math.radians(lat1), math.radians(lon1)
        lat2, lon2 = math.radians(lat2), math.radians(lon2)
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        return 6371 * c  # Earth radius in km
    
    @staticmethod
    def estimate_duration(distance_km: float, transport_mode: str) -> float:
        """Estimate duration in seconds based on distance and mode."""
        speeds = {
            "driving": 50,
            "walking": 5,
            "cycling": 15,
            "public_transport": 35
        }
        speed = speeds.get(transport_mode, 50)
        return (distance_km / speed) * 3600
    
    @staticmethod
    def format_distance(distance_m: float) -> str:
        """Format distance in meters to human-readable string."""
        if distance_m >= 1000:
            return f"{distance_m / 1000:.1f} km"
        return f"{distance_m:.0f} m"
    
    @staticmethod
    def format_duration(duration_s: float) -> str:
        """Format duration in seconds to human-readable string."""
        hours = int(duration_s // 3600)
        minutes = int((duration_s % 3600) // 60)
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"
    
    @staticmethod
    def parse_route_data(route_data: Dict[str, Any], transport_mode: str) -> Dict[str, Any]:
        """Parse raw route data into structured format."""
        try:
            if not route_data.get("features"):
                raise ValueError("No route features in response")
            
            feature = route_data["features"][0]
            props = feature.get("properties", {})
            summary = props.get("summary", {})
            
            distance_m = summary.get("distance", 0)
            duration_s = summary.get("duration", 0)
            
            # Extract steps
            steps = []
            segments = props.get("segments", [])
            for segment in segments:
                for step in segment.get("steps", []):
                    instruction = step.get("instruction", "")
                    if instruction:
                        steps.append(instruction)
            
            if not steps:
                steps = ["Route calculated - follow navigation"]
            
            return {
                "distance": MapsServiceHelpers.format_distance(distance_m),
                "duration": MapsServiceHelpers.format_duration(duration_s),
                "distance_meters": distance_m,
                "duration_seconds": duration_s,
                "steps": steps[:10],  # Limit to 10 steps
                "transport_mode": transport_mode
            }
            
        except Exception as e:
            logger.error(f"Route parsing failed: {e}")
            return {
                "distance": "Unknown",
                "duration": "Unknown",
                "steps": ["Route details unavailable"],
                "transport_mode": transport_mode
            }

# ========================= LANGCHAIN TOOLS ========================= #

@tool
async def geocode_location(location: str) -> Dict[str, Any]:
    """Convert a location name to geographic coordinates using OpenRouteService.
    
    Args:
        location: Location name (e.g., 'London, UK' or 'New York')
    
    Returns:
        Dictionary with coordinates, name, region, country, and confidence
    """
    try:
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": settings.openroute_api_key}
            params = {
                "text": location,
                "size": 1,
                "layers": "locality,region,country"
            }
            resp = await client.get(
                "https://api.openrouteservice.org/geocode/search",
                headers=headers,
                params=params,
                timeout=10
            )
            resp.raise_for_status()
            data = resp.json()
            
            if not data.get("features"):
                return {"error": f"Location not found: {location}"}
            
            f = data["features"][0]
            coords = f["geometry"]["coordinates"]
            props = f["properties"]
            
            return {
                "location": location,
                "coordinates": [coords[1], coords[0]],  # [lat, lon]
                "latitude": coords[1],
                "longitude": coords[0],
                "name": props.get("name", location),
                "region": props.get("region", ""),
                "country": props.get("country", ""),
                "confidence": props.get("confidence", 0)
            }
    except Exception as e:
        logger.error(f"Geocoding failed for {location}: {e}")
        return {"error": str(e)}


@tool
async def get_route(origin: str, destination: str, transport_mode: str = "driving") -> Dict[str, Any]:
    """Get route information between two locations.
    
    Args:
        origin: Starting location name
        destination: Destination location name
        transport_mode: Transport mode - 'driving', 'walking', 'cycling', or 'public_transport'
    
    Returns:
        Route information including distance, duration, and turn-by-turn directions
    """
    try:
        # Geocode both locations
        origin_result = await geocode_location.ainvoke({"location": origin})
        dest_result = await geocode_location.ainvoke({"location": destination})
        
        if "error" in origin_result:
            return origin_result
        if "error" in dest_result:
            return dest_result
        
        origin_coords = origin_result["coordinates"]
        dest_coords = dest_result["coordinates"]
        
        # Get route from OpenRouteService
        profile = MapsServiceHelpers.TRANSPORT_MODES.get(transport_mode, "driving-car")
        coords = [
            [origin_coords[1], origin_coords[0]],  # [lon, lat]
            [dest_coords[1], dest_coords[0]]
        ]
        
        headers = {
            "Authorization": settings.openroute_api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "coordinates": coords,
            "instructions": True,
            "geometry": True
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://api.openrouteservice.org/v2/directions/{profile}/geojson",
                headers=headers,
                json=payload,
                timeout=30
            )
            resp.raise_for_status()
            route_data = resp.json()
        
        # Parse route data
        parsed = MapsServiceHelpers.parse_route_data(route_data, transport_mode)
        parsed["origin"] = origin_result["name"]
        parsed["destination"] = dest_result["name"]
        
        return parsed
        
    except Exception as e:
        logger.error(f"Route fetch failed: {e}, using fallback")
        # Fallback calculation
        try:
            origin_result = await geocode_location.ainvoke({"location": origin})
            dest_result = await geocode_location.ainvoke({"location": destination})
            
            if "error" not in origin_result and "error" not in dest_result:
                dist_km = MapsServiceHelpers.calculate_haversine_distance(
                    origin_result["latitude"], origin_result["longitude"],
                    dest_result["latitude"], dest_result["longitude"]
                )
                dur_s = MapsServiceHelpers.estimate_duration(dist_km, transport_mode)
                
                return {
                    "origin": origin,
                    "destination": destination,
                    "distance": MapsServiceHelpers.format_distance(dist_km * 1000),
                    "duration": MapsServiceHelpers.format_duration(dur_s),
                    "distance_meters": dist_km * 1000,
                    "duration_seconds": dur_s,
                    "steps": ["Direct route - detailed navigation unavailable"],
                    "transport_mode": transport_mode,
                    "fallback": True
                }
        except:
            pass
        
        return {"error": str(e)}


@tool
async def get_multiple_routes(origin: str, destination: str) -> Dict[str, Any]:
    """Get route options for all available transport modes (driving, walking, cycling).
    
    Args:
        origin: Starting location name
        destination: Destination location name
    
    Returns:
        Routes for driving, walking, and cycling modes
    """
    modes = ["driving", "walking", "cycling"]
    tasks = [
        get_route.ainvoke({"origin": origin, "destination": destination, "transport_mode": mode})
        for mode in modes
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    routes = {}
    for mode, result in zip(modes, results):
        if isinstance(result, Exception):
            logger.error(f"Failed to get {mode} route: {result}")
            routes[mode] = {"error": str(result)}
        else:
            routes[mode] = result
    
    return {
        "origin": origin,
        "destination": destination,
        "routes": routes
    }


@tool
async def search_flights(origin_code: str, dest_code: str, date: str) -> Dict[str, Any]:
    """Search for flight options between airports.
    
    Args:
        origin_code: Origin airport code (e.g., 'DEL', 'BOM')
        dest_code: Destination airport code
        date: Departure date in YYYY-MM-DD format
    
    Returns:
        List of available flights with pricing and schedules
    """
    try:
        url = f"https://{MapsServiceHelpers.SKYSCANNER_HOST}/search"
        headers = {
            "X-RapidAPI-Key": settings.rapidapi_key,
            "X-RapidAPI-Host": MapsServiceHelpers.SKYSCANNER_HOST
        }
        params = {
            "origin": origin_code,
            "destination": dest_code,
            "departureDate": date,
            "currency": "INR"
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            
            return {
                "origin": origin_code,
                "destination": dest_code,
                "date": date,
                "flights": data.get("itineraries", []),
                "count": len(data.get("itineraries", []))
            }
            
    except Exception as e:
        logger.error(f"Flight search failed: {e}")
        return {"error": str(e)}


@tool
async def search_trains(from_station: str, to_station: str, date: str) -> Dict[str, Any]:
    """Search for train options between stations (Indian Railways).
    
    Args:
        from_station: Origin station code
        to_station: Destination station code
        date: Journey date in YYYY-MM-DD format
    
    Returns:
        List of available trains with schedules and pricing
    """
    try:
        url = f"https://{MapsServiceHelpers.TRAINS_HOST}/trainBetweenStations"
        headers = {
            "X-RapidAPI-Key": settings.rapidapi_key,
            "X-RapidAPI-Host": MapsServiceHelpers.TRAINS_HOST
        }
        params = {
            "fromStationCode": from_station,
            "toStationCode": to_station,
            "dateOfJourney": date
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            
            return {
                "from_station": from_station,
                "to_station": to_station,
                "date": date,
                "trains": data.get("data", []),
                "count": len(data.get("data", []))
            }
            
    except Exception as e:
        logger.error(f"Train search failed: {e}")
        return {"error": str(e)}


@tool
async def search_buses(origin: str, destination: str, date: str) -> Dict[str, Any]:
    """Search for bus options between cities.
    
    Args:
        origin: Origin city name
        destination: Destination city name
        date: Journey date in YYYY-MM-DD format
    
    Returns:
        List of available buses with schedules and pricing
    """
    try:
        url = f"https://{MapsServiceHelpers.BUSES_HOST}/searchBuses"
        headers = {
            "X-RapidAPI-Key": settings.rapidapi_key,
            "X-RapidAPI-Host": MapsServiceHelpers.BUSES_HOST
        }
        params = {
            "fromCity": origin,
            "toCity": destination,
            "doj": date
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            
            return {
                "origin": origin,
                "destination": destination,
                "date": date,
                "buses": data.get("buses", []),
                "count": len(data.get("buses", []))
            }
            
    except Exception as e:
        logger.error(f"Bus search failed: {e}")
        return {"error": str(e)}


@tool
async def search_hotels(location: str, checkin: str, checkout: str) -> Dict[str, Any]:
    """Search for hotels at a location.
    
    Args:
        location: Location to search for hotels
        checkin: Check-in date (YYYY-MM-DD)
        checkout: Check-out date (YYYY-MM-DD)
    
    Returns:
        List of available hotels with pricing and amenities
    """
    try:
        url = f"https://{MapsServiceHelpers.HOTELS_HOST}/v1/hotels/search"
        headers = {
            "X-RapidAPI-Key": settings.rapidapi_key,
            "X-RapidAPI-Host": MapsServiceHelpers.HOTELS_HOST
        }
        params = {
            "location": location,
            "checkin_date": checkin,
            "checkout_date": checkout,
            "currency": "INR"
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            
            return {
                "location": location,
                "checkin": checkin,
                "checkout": checkout,
                "hotels": data.get("result", []),
                "count": len(data.get("result", []))
            }
            
    except Exception as e:
        logger.error(f"Hotel search failed: {e}")
        return {"error": str(e)}


@tool
async def get_comprehensive_travel_options(
    origin: str,
    destination: str,
    date: str,
    checkin: Optional[str] = None,
    checkout: Optional[str] = None
) -> Dict[str, Any]:
    """Get comprehensive travel options including routes, flights, trains, buses, and hotels.
    
    Args:
        origin: Starting location name
        destination: Destination location name
        date: Travel date in YYYY-MM-DD format
        checkin: Hotel check-in date (optional, defaults to travel date)
        checkout: Hotel check-out date (optional, defaults to travel date)
    
    Returns:
        Comprehensive travel information including all transport modes and accommodation
    """
    try:
        # Set default checkin/checkout if not provided
        checkin = checkin or date
        checkout = checkout or date
        
        # Fetch all options in parallel
        tasks = [
            get_route.ainvoke({"origin": origin, "destination": destination, "transport_mode": "driving"}),
            search_flights.ainvoke({"origin_code": origin, "dest_code": destination, "date": date}),
            search_trains.ainvoke({"from_station": origin, "to_station": destination, "date": date}),
            search_buses.ainvoke({"origin": origin, "destination": destination, "date": date}),
            search_hotels.ainvoke({"location": destination, "checkin": checkin, "checkout": checkout})
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            "origin": origin,
            "destination": destination,
            "date": date,
            "driving_route": results[0] if not isinstance(results[0], Exception) else {"error": str(results[0])},
            "flights": results[1] if not isinstance(results[1], Exception) else {"error": str(results[1])},
            "trains": results[2] if not isinstance(results[2], Exception) else {"error": str(results[2])},
            "buses": results[3] if not isinstance(results[3], Exception) else {"error": str(results[3])},
            "hotels": results[4] if not isinstance(results[4], Exception) else {"error": str(results[4])}
        }
        
    except Exception as e:
        logger.error(f"Comprehensive travel options failed: {e}")
        return {"error": str(e)}


# ========================= TOOL LIST FOR AGENT ========================= #

MAPS_TOOLS = [
    geocode_location,
    get_route,
    get_multiple_routes,
    search_flights,
    search_trains,
    search_buses,
    search_hotels,
    get_comprehensive_travel_options
]