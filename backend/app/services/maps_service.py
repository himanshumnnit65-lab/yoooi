import httpx
import asyncio
from typing import List, Optional, Dict, Any
from app.config.settings import settings
from app.core.state import RouteInfo
import logging

logger = logging.getLogger(__name__)


class MapsService:
    """Service for fetching routing and geocoding data from OpenRouteService"""
    
    def __init__(self):
        self.api_key = settings.openroute_api_key
        self.base_url = "https://api.openrouteservice.org"
        
        # Transport modes mapping
        self.transport_modes = {
            "driving": "driving-car",
            "walking": "foot-walking", 
            "cycling": "cycling-regular",
            "public_transport": "driving-car"  # Fallback to driving for now
        }
    
    async def geocode_location(self, location: str) -> Optional[Dict[str, Any]]:
        """Get coordinates and details for a location using geocoding"""
        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": self.api_key
                }
                params = {
                    "text": location,
                    "size": 1,
                    "layers": "locality,region,country"
                }
                
                response = await client.get(
                    f"{self.base_url}/geocode/search", 
                    headers=headers,
                    params=params
                )
                response.raise_for_status()
                
                data = response.json()
                features = data.get("features", [])
                
                if not features:
                    logger.error(f"Location not found: {location}")
                    return None
                
                feature = features[0]
                coordinates = feature["geometry"]["coordinates"]  # [lon, lat]
                properties = feature["properties"]
                
                return {
                    "coordinates": [coordinates[1], coordinates[0]],  # Convert to [lat, lon]
                    "name": properties.get("name", location),
                    "region": properties.get("region", ""),
                    "country": properties.get("country", ""),
                    "confidence": properties.get("confidence", 0)
                }
        
        except Exception as e:
            logger.error(f"Failed to geocode location {location}: {str(e)}")
            # Fallback to a simple coordinate lookup service or return None
            return await self._fallback_geocoding(location)
    
    async def get_route(
        self, 
        start_coords: List[float], 
        end_coords: List[float], 
        transport_mode: str = "driving"
    ) -> Optional[Dict[str, Any]]:
        """Get route information between two coordinate points"""
        try:
            # Map transport mode to OpenRouteService profile
            profile = self.transport_modes.get(transport_mode, "driving-car")
            
            async with httpx.AsyncClient() as client:
                # Coordinates should be in [lon, lat] format for the API
                coordinates = [
                    [start_coords[1], start_coords[0]],  # Convert [lat, lon] to [lon, lat]
                    [end_coords[1], end_coords[0]]
                ]
                
                headers = {
                    "Authorization": self.api_key,
                    "Content-Type": "application/json"
                }
                
                payload = {
                    "coordinates": coordinates,
                    "instructions": True,
                    "geometry": True,
                    "elevation": False
                }
                
                # Try the v2 endpoint first
                try:
                    response = await client.post(
                        f"{self.base_url}/v2/directions/{profile}/geojson",
                        headers=headers,
                        json=payload,
                        timeout=30.0
                    )
                    response.raise_for_status()
                    return response.json()
                except Exception as e:
                    logger.warning(f"v2 endpoint failed, trying alternative: {str(e)}")
                    
                    # Try alternative endpoint structure
                    response = await client.post(
                        f"{self.base_url}/directions/{profile}/geojson",
                        headers=headers,
                        json=payload,
                        timeout=30.0
                    )
                    response.raise_for_status()
                    return response.json()
        
        except Exception as e:
            logger.error(f"Failed to get route: {str(e)}")
            # Return fallback route calculation
            return await self._calculate_fallback_route(start_coords, end_coords, transport_mode)
    
    async def _calculate_fallback_route(
        self, 
        start_coords: List[float], 
        end_coords: List[float], 
        transport_mode: str
    ) -> Dict[str, Any]:
        """Calculate basic route information using straight-line distance"""
        try:
            # Calculate straight-line distance using Haversine formula
            import math
            
            lat1, lon1 = math.radians(start_coords[0]), math.radians(start_coords[1])
            lat2, lon2 = math.radians(end_coords[0]), math.radians(end_coords[1])
            
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            
            a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
            c = 2 * math.asin(math.sqrt(a))
            
            # Earth's radius in kilometers
            r = 6371
            distance_km = c * r
            
            # Estimate duration based on transport mode
            speed_kmh = {
                "driving": 50,
                "walking": 5,
                "cycling": 15,
                "public_transport": 35
            }
            
            estimated_speed = speed_kmh.get(transport_mode, 50)
            duration_hours = distance_km / estimated_speed
            duration_seconds = duration_hours * 3600
            
            # Create fallback GeoJSON-like structure
            return {
                "features": [
                    {
                        "properties": {
                            "summary": {
                                "distance": distance_km * 1000,  # Convert to meters
                                "duration": duration_seconds
                            },
                            "segments": [
                                {
                                    "steps": [
                                        {
                                            "instruction": f"Travel approximately {distance_km:.1f} km to destination"
                                        }
                                    ]
                                }
                            ]
                        }
                    }
                ]
            }
            
        except Exception as e:
            logger.error(f"Fallback route calculation failed: {str(e)}")
            # Return minimal fallback
            return {
                "features": [
                    {
                        "properties": {
                            "summary": {
                                "distance": 10000,  # 10km default
                                "duration": 1800    # 30 minutes default
                            },
                            "segments": [
                                {
                                    "steps": [
                                        {
                                            "instruction": "Route calculation unavailable"
                                        }
                                    ]
                                }
                            ]
                        }
                    }
                ]
            }
    
    async def get_route_matrix(
        self,
        locations: List[List[float]],
        transport_mode: str = "driving"
    ) -> Optional[Dict[str, Any]]:
        """Get distance and duration matrix between multiple locations"""
        try:
            profile = self.transport_modes.get(transport_mode, "driving-car")
            
            async with httpx.AsyncClient() as client:
                # Convert [lat, lon] to [lon, lat] for all locations
                coordinates = [[loc[1], loc[0]] for loc in locations]
                
                headers = {
                    "Authorization": self.api_key,
                    "Content-Type": "application/json"
                }
                
                payload = {
                    "locations": coordinates,
                    "metrics": ["distance", "duration"]
                }
                
                response = await client.post(
                    f"{self.base_url}/v2/matrix/{profile}",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                
                return response.json()
        
        except Exception as e:
            logger.error(f"Failed to get route matrix: {str(e)}")
            return None
    
    def parse_route_data(self, route_data: Dict[str, Any], transport_mode: str = "driving") -> RouteInfo:
        """Parse OpenRouteService route response into RouteInfo object"""
        try:
            features = route_data.get("features", [])
            if not features:
                raise ValueError("No route features found")
            
            route_feature = features[0]
            properties = route_feature.get("properties", {})
            
            # Extract summary information
            summary = properties.get("summary", {})
            distance_meters = summary.get("distance", 0)
            duration_seconds = summary.get("duration", 0)
            
            # Convert distance to appropriate units
            if distance_meters >= 1000:
                distance_str = f"{distance_meters / 1000:.1f} km"
            else:
                distance_str = f"{distance_meters:.0f} m"
            
            # Convert duration to human readable format
            duration_str = self._format_duration(duration_seconds)
            
            # Extract turn-by-turn instructions
            segments = properties.get("segments", [])
            steps = []
            
            for segment in segments:
                segment_steps = segment.get("steps", [])
                for step in segment_steps:
                    instruction = step.get("instruction", "")
                    if instruction and instruction not in steps:
                        steps.append(instruction)
            
            # If no detailed steps, create basic route description
            if not steps:
                steps = [f"Travel from origin to destination via {transport_mode}"]
            
            return RouteInfo(
                distance=distance_str,
                duration=duration_str,
                steps=steps[:10],  # Limit to first 10 steps to avoid overwhelming
                traffic_info=None,  # OpenRouteService doesn't provide real-time traffic
                transport_mode=transport_mode
            )
            
        except Exception as e:
            logger.error(f"Failed to parse route data: {str(e)}")
            # Return fallback route info
            return RouteInfo(
                distance="Unknown distance",
                duration="Unknown duration", 
                steps=["Route calculation failed"],
                traffic_info=None,
                transport_mode=transport_mode
            )
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration from seconds to human readable string"""
        if seconds < 60:
            return f"{int(seconds)} seconds"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            remaining_seconds = int(seconds % 60)
            if remaining_seconds > 0:
                return f"{minutes}m {remaining_seconds}s"
            return f"{minutes} minutes"
        else:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            if minutes > 0:
                return f"{hours}h {minutes}m"
            return f"{hours} hours"
    
    async def get_route_between_locations(
        self, 
        origin: str, 
        destination: str, 
        transport_mode: str = "driving"
    ) -> Optional[RouteInfo]:
        """Get route information between two location names"""
        # First geocode both locations
        origin_data = await self.geocode_location(origin)
        destination_data = await self.geocode_location(destination)
        
        if not origin_data or not destination_data:
            logger.error("Failed to geocode one or both locations")
            return None
        
        # Get route between coordinates
        route_data = await self.get_route(
            origin_data["coordinates"],
            destination_data["coordinates"],
            transport_mode
        )
        
        if not route_data:
            return None
        
        # Parse and return route information
        route_info = self.parse_route_data(route_data, transport_mode)
        
        # Add location names to the route info for context
        if route_info.steps:
            route_info.steps[0] = f"Start from {origin_data['name']}"
            route_info.steps.append(f"Arrive at {destination_data['name']}")
        
        return route_info
    
    async def get_multiple_route_options(
        self, 
        origin: str, 
        destination: str
    ) -> Dict[str, Optional[RouteInfo]]:
        """Get route options for different transport modes"""
        transport_modes = ["driving", "walking", "cycling"]
        routes = {}
        
        # Use asyncio.gather to fetch routes concurrently
        tasks = [
            self.get_route_between_locations(origin, destination, mode)
            for mode in transport_modes
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for mode, result in zip(transport_modes, results):
            if isinstance(result, Exception):
                logger.error(f"Failed to get {mode} route: {result}")
                routes[mode] = None
            else:
                routes[mode] = result
        
        return routes