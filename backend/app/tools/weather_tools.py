import httpx
import asyncio
from typing import List, Optional, Dict, Any, Annotated
from datetime import datetime
from collections import defaultdict
import logging
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from app.config.settings import settings
from app.core.state import WeatherInfo, AirPollutionInfo

logger = logging.getLogger(__name__)

# ========================= INPUT SCHEMAS ========================= #

class LocationInput(BaseModel):
    """Input schema for location-based queries."""
    location: str = Field(..., description="City name or location to get coordinates for (e.g., 'London', 'New York')")

class CoordinatesInput(BaseModel):
    """Input schema for coordinate-based queries."""
    lat: float = Field(..., description="Latitude coordinate")
    lon: float = Field(..., description="Longitude coordinate")

class WeatherDatesInput(BaseModel):
    """Input schema for weather forecast with specific dates."""
    location: str = Field(..., description="City name or location")
    dates: List[str] = Field(..., description="List of dates in YYYY-MM-DD format")

# ========================= HELPER FUNCTIONS ========================= #

class WeatherServiceHelpers:
    """Shared helper functions for weather tools."""
    
    @staticmethod
    def aggregate_daily_from_ow(forecast: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
        """Aggregate 3-hour OpenWeather forecast into daily min/max."""
        daily = defaultdict(lambda: {"temp_min": float("inf"), "temp_max": float("-inf")})
        for item in forecast.get("list", []):
            dt = datetime.fromtimestamp(item["dt"])
            date_str = dt.strftime("%Y-%m-%d")
            main = item.get("main", {})
            temp_min = main.get("temp_min", main.get("temp", 0))
            temp_max = main.get("temp_max", main.get("temp", 0))
            daily[date_str]["temp_min"] = min(daily[date_str]["temp_min"], temp_min)
            daily[date_str]["temp_max"] = max(daily[date_str]["temp_max"], temp_max)
        return daily
    
    @staticmethod
    def aggregate_air_pollution_by_day(air_data: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
        """Aggregate air pollution data by day."""
        daily_vals = defaultdict(lambda: {"count": 0, "aqi": 0, "co": 0, "no": 0, "no2": 0, "o3": 0,
                                          "so2": 0, "pm2_5": 0, "pm10": 0, "nh3": 0})
        for item in air_data.get("list", []):
            dt = datetime.fromtimestamp(item["dt"])
            date_str = dt.strftime("%Y-%m-%d")
            comp = item["components"]
            daily_vals[date_str]["count"] += 1
            daily_vals[date_str]["aqi"] += item["main"]["aqi"]
            for k in comp:
                daily_vals[date_str][k] += comp[k]

        result = {}
        for date_str, vals in daily_vals.items():
            count = vals.pop("count")
            averaged = {k: v / count for k, v in vals.items()}
            result[date_str] = averaged
        return result

# ========================= LANGCHAIN TOOLS ========================= #

@tool
async def get_location_coordinates(location: str) -> Dict[str, Any]:
    """Get latitude and longitude coordinates for a given location using OpenWeather geocoding API.
    
    Args:
        location: City name or location string (e.g., 'London, UK' or 'New York')
    
    Returns:
        Dictionary with 'lat' and 'lon' keys, or error message if location not found
    """
    try:
        async with httpx.AsyncClient() as client:
            params = {
                "q": location,
                "limit": 1,
                "appid": settings.openweather_api_key
            }
            resp = await client.get(
                "https://api.openweathermap.org/geo/1.0/direct",
                params=params
            )
            resp.raise_for_status()
            data = resp.json()
            
            if not data:
                return {"error": f"Location not found: {location}"}
            
            return {
                "location": location,
                "lat": data[0]["lat"],
                "lon": data[0]["lon"],
                "name": data[0].get("name"),
                "country": data[0].get("country")
            }
    except Exception as e:
        logger.error(f"Failed to get coordinates for {location}: {e}")
        return {"error": str(e)}


@tool
async def get_current_weather(lat: float, lon: float) -> Dict[str, Any]:
    """Get current weather conditions for specific coordinates.
    
    Args:
        lat: Latitude coordinate
        lon: Longitude coordinate
    
    Returns:
        Current weather data including temperature, humidity, wind, and conditions
    """
    try:
        async with httpx.AsyncClient() as client:
            params = {
                "lat": lat,
                "lon": lon,
                "appid": settings.openweather_api_key,
                "units": "metric"
            }
            resp = await client.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params=params
            )
            resp.raise_for_status()
            data = resp.json()
            
            # Extract key information
            return {
                "temperature": data["main"]["temp"],
                "feels_like": data["main"]["feels_like"],
                "temp_min": data["main"]["temp_min"],
                "temp_max": data["main"]["temp_max"],
                "humidity": data["main"]["humidity"],
                "pressure": data["main"]["pressure"],
                "wind_speed": data["wind"]["speed"],
                "description": data["weather"][0]["description"],
                "condition": data["weather"][0]["main"],
                "timestamp": datetime.fromtimestamp(data["dt"]).isoformat()
            }
    except Exception as e:
        logger.error(f"Failed to get current weather: {e}")
        return {"error": str(e)}


@tool
async def get_5day_forecast(lat: float, lon: float) -> Dict[str, Any]:
    """Get 5-day weather forecast with 3-hour intervals from OpenWeather.
    
    Args:
        lat: Latitude coordinate
        lon: Longitude coordinate
    
    Returns:
        5-day forecast data with 3-hour intervals
    """
    try:
        async with httpx.AsyncClient() as client:
            params = {
                "lat": lat,
                "lon": lon,
                "appid": settings.openweather_api_key,
                "units": "metric"
            }
            resp = await client.get(
                "https://api.openweathermap.org/data/2.5/forecast",
                params=params
            )
            resp.raise_for_status()
            data = resp.json()
            
            # Aggregate by day
            daily_agg = WeatherServiceHelpers.aggregate_daily_from_ow(data)
            
            return {
                "forecast_type": "5-day",
                "daily_summary": daily_agg,
                "raw_data": data
            }
    except Exception as e:
        logger.error(f"Failed to get 5-day forecast: {e}")
        return {"error": str(e)}


@tool
async def get_extended_forecast(lat: float, lon: float) -> Dict[str, Any]:
    """Get 16-day extended weather forecast from Open-Meteo.
    
    Args:
        lat: Latitude coordinate
        lon: Longitude coordinate
    
    Returns:
        16-day daily forecast with max/min temperatures
    """
    try:
        async with httpx.AsyncClient() as client:
            params = {
                "latitude": lat,
                "longitude": lon,
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max",
                "timezone": "auto",
            }
            resp = await client.get(
                "https://api.open-meteo.com/v1/forecast",
                params=params
            )
            resp.raise_for_status()
            data = resp.json()
            
            if "daily" not in data:
                return {"error": "No forecast data available"}
            
            daily = data["daily"]
            forecast = []
            for i in range(len(daily["time"])):
                forecast.append({
                    "date": daily["time"][i],
                    "temp_max": daily["temperature_2m_max"][i],
                    "temp_min": daily["temperature_2m_min"][i],
                    "precipitation": daily.get("precipitation_sum", [None])[i],
                    "precipitation_probability": daily.get("precipitation_probability_max", [None])[i]
                })
            
            return {
                "forecast_type": "16-day",
                "location": {"lat": lat, "lon": lon},
                "daily_forecast": forecast
            }
    except Exception as e:
        logger.error(f"Failed to get extended forecast: {e}")
        return {"error": str(e)}


@tool
async def get_air_quality(lat: float, lon: float) -> Dict[str, Any]:
    """Get current and forecast air quality/pollution data.
    
    Args:
        lat: Latitude coordinate
        lon: Longitude coordinate
    
    Returns:
        Air quality index and pollutant concentrations
    """
    try:
        async with httpx.AsyncClient() as client:
            params = {
                "lat": lat,
                "lon": lon,
                "appid": settings.openweather_api_key
            }
            resp = await client.get(
                "https://api.openweathermap.org/data/2.5/air_pollution/forecast",
                params=params
            )
            resp.raise_for_status()
            data = resp.json()
            
            # Aggregate by day
            daily_air = WeatherServiceHelpers.aggregate_air_pollution_by_day(data)
            
            return {
                "location": {"lat": lat, "lon": lon},
                "daily_air_quality": daily_air,
                "aqi_legend": {
                    "1": "Good",
                    "2": "Fair",
                    "3": "Moderate",
                    "4": "Poor",
                    "5": "Very Poor"
                }
            }
    except Exception as e:
        logger.error(f"Failed to get air quality: {e}")
        return {"error": str(e)}


@tool
async def get_weather_for_specific_dates(location: str, dates: List[str]) -> Dict[str, Any]:
    """Get weather forecast for specific dates at a location. Automatically selects best data source.
    
    Args:
        location: City name or location string
        dates: List of dates in YYYY-MM-DD format
    
    Returns:
        Weather information for each requested date
    """
    # First get coordinates
    coords_result = await get_location_coordinates.ainvoke({"location": location})
    if "error" in coords_result:
        return coords_result
    
    lat = coords_result["lat"]
    lon = coords_result["lon"]
    
    today = datetime.now().date()
    max_date = max(datetime.strptime(d, "%Y-%m-%d").date() for d in dates)
    delta_days = (max_date - today).days
    
    results = []
    
    try:
        if delta_days <= 5:
            # Use OpenWeather 5-day forecast
            forecast_result = await get_5day_forecast.ainvoke({"lat": lat, "lon": lon})
            air_result = await get_air_quality.ainvoke({"lat": lat, "lon": lon})
            
            if "error" not in forecast_result:
                daily_agg = forecast_result["daily_summary"]
                daily_air = air_result.get("daily_air_quality", {})
                
                for date in dates:
                    date_obj = datetime.strptime(date, "%Y-%m-%d").date()
                    if date_obj == today:
                        current = await get_current_weather.ainvoke({"lat": lat, "lon": lon})
                        results.append({
                            "date": date,
                            "temp_max": current.get("temp_max", 22),
                            "temp_min": current.get("temp_min", 18),
                            "description": current.get("description", "N/A"),
                            "air_quality": daily_air.get(date)
                        })
                    elif date in daily_agg:
                        agg = daily_agg[date]
                        results.append({
                            "date": date,
                            "temp_max": agg["temp_max"],
                            "temp_min": agg["temp_min"],
                            "air_quality": daily_air.get(date)
                        })
                    else:
                        results.append({"date": date, "error": "Data not available"})
        
        elif 6 <= delta_days <= 16:
            # Use Open-Meteo extended forecast
            forecast_result = await get_extended_forecast.ainvoke({"lat": lat, "lon": lon})
            
            if "error" not in forecast_result:
                forecast_map = {f["date"]: f for f in forecast_result["daily_forecast"]}
                
                for date in dates:
                    if date in forecast_map:
                        f = forecast_map[date]
                        results.append({
                            "date": date,
                            "temp_max": f["temp_max"],
                            "temp_min": f["temp_min"],
                            "precipitation": f.get("precipitation"),
                            "precipitation_probability": f.get("precipitation_probability")
                        })
                    else:
                        results.append({"date": date, "error": "Data not available"})
        else:
            # Beyond 16 days - return fallback
            for date in dates:
                results.append({
                    "date": date,
                    "temp_max": 22.0,
                    "temp_min": 18.0,
                    "description": "Forecast not available beyond 16 days",
                    "note": "Fallback data"
                })
        
        return {
            "location": location,
            "coordinates": {"lat": lat, "lon": lon},
            "forecast_range": f"{delta_days} days",
            "weather_data": results
        }
        
    except Exception as e:
        logger.error(f"Failed to get weather for dates: {e}")
        return {"error": str(e)}


# ========================= TOOL LIST FOR AGENT ========================= #

WEATHER_TOOLS = [
    get_location_coordinates,
    get_current_weather,
    get_5day_forecast,
    get_extended_forecast,
    get_air_quality,
    get_weather_for_specific_dates
]