import httpx
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from app.config.settings import settings
from app.core.state import WeatherInfo
import logging

logger = logging.getLogger(__name__)


class WeatherService:
    """Service for fetching weather data from OpenWeatherMap API"""
    
    def __init__(self):
        self.api_key = settings.openweather_api_key
        self.base_url = "https://api.openweathermap.org/data/2.5"
        self.geocoding_url = "https://api.openweathermap.org/geo/1.0"
    
    async def get_coordinates(self, location: str) -> Optional[Dict[str, float]]:
        """Get latitude and longitude for a location"""
        try:
            async with httpx.AsyncClient() as client:
                params = {
                    "q": location,
                    "limit": 1,
                    "appid": self.api_key
                }
                
                response = await client.get(f"{self.geocoding_url}/direct", params=params)
                response.raise_for_status()
                
                data = response.json()
                if not data:
                    logger.error(f"Location not found: {location}")
                    return None
                
                return {
                    "lat": data[0]["lat"],
                    "lon": data[0]["lon"]
                }
        
        except Exception as e:
            logger.error(f"Failed to get coordinates for {location}: {str(e)}")
            return None
    
    async def get_current_weather(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        """Get current weather for coordinates"""
        try:
            async with httpx.AsyncClient() as client:
                params = {
                    "lat": lat,
                    "lon": lon,
                    "appid": self.api_key,
                    "units": "metric"
                }
                
                response = await client.get(f"{self.base_url}/weather", params=params)
                response.raise_for_status()
                
                return response.json()
        
        except Exception as e:
            logger.error(f"Failed to get current weather: {str(e)}")
            return None
    
    async def get_forecast(self, lat: float, lon: float, days: int = 5) -> Optional[Dict[str, Any]]:
        """Get weather forecast for coordinates"""
        try:
            async with httpx.AsyncClient() as client:
                params = {
                    "lat": lat,
                    "lon": lon,
                    "appid": self.api_key,
                    "units": "metric",
                    "cnt": days * 8  # 8 forecasts per day (3-hour intervals)
                }
                
                response = await client.get(f"{self.base_url}/forecast", params=params)
                response.raise_for_status()
                
                return response.json()
        
        except Exception as e:
            logger.error(f"Failed to get weather forecast: {str(e)}")
            return None
    
    def parse_weather_data(self, weather_data: Dict[str, Any], date: str) -> WeatherInfo:
        """Parse weather API response into WeatherInfo object"""
        main = weather_data.get("main", {})
        weather = weather_data.get("weather", [{}])[0]
        wind = weather_data.get("wind", {})
        
        return WeatherInfo(
            date=date,
            temperature_max=main.get("temp_max", main.get("temp", 0)),
            temperature_min=main.get("temp_min", main.get("temp", 0)),
            description=weather.get("description", "Unknown"),
            humidity=main.get("humidity", 0),
            wind_speed=wind.get("speed", 0),
            precipitation_chance=weather_data.get("pop", 0) * 100 if "pop" in weather_data else 0
        )
    
    async def get_weather_for_dates(self, location: str, dates: List[str]) -> List[WeatherInfo]:
        """Get weather information for specific dates"""
        coordinates = await self.get_coordinates(location)
        if not coordinates:
            raise ValueError(f"Could not find coordinates for location: {location}")
        
        weather_info = []
        
        # Check if dates are within forecast range (next 5 days)
        today = datetime.now().date()
        forecast_limit = today + timedelta(days=5)
        
        # Get current weather and forecast
        current_weather = await self.get_current_weather(coordinates["lat"], coordinates["lon"])
        forecast_data = await self.get_forecast(coordinates["lat"], coordinates["lon"])
        
        for date_str in dates:
            try:
                target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                
                if target_date == today and current_weather:
                    # Use current weather for today
                    weather_info.append(self.parse_weather_data(current_weather, date_str))
                elif target_date <= forecast_limit and forecast_data:
                    # Use forecast data
                    forecast_item = self._find_forecast_for_date(forecast_data, target_date)
                    if forecast_item:
                        weather_info.append(self.parse_weather_data(forecast_item, date_str))
                    else:
                        # Fallback to estimated data
                        weather_info.append(self._create_fallback_weather(date_str))
                else:
                    # For dates beyond forecast range, create estimated data
                    weather_info.append(self._create_fallback_weather(date_str))
            
            except ValueError as e:
                logger.error(f"Invalid date format {date_str}: {str(e)}")
                continue
        
        return weather_info
    
    def _find_forecast_for_date(self, forecast_data: Dict[str, Any], target_date) -> Optional[Dict[str, Any]]:
        """Find forecast data for a specific date"""
        forecasts = forecast_data.get("list", [])
        
        for forecast in forecasts:
            forecast_date = datetime.fromtimestamp(forecast["dt"]).date()
            if forecast_date == target_date:
                return forecast
        
        return None
    
    def _create_fallback_weather(self, date_str: str) -> WeatherInfo:
        """Create fallback weather data for dates beyond API range"""
        return WeatherInfo(
            date=date_str,
            temperature_max=22.0,  # Default pleasant temperature
            temperature_min=18.0,
            description="Partly cloudy",
            humidity=60,
            wind_speed=5.0,
            precipitation_chance=20
        )