from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from langchain_core.tools import tool
from pydantic import BaseModel, Field
import logging

from app.core.state import ItineraryDay, WeatherInfo, BudgetBreakdown

logger = logging.getLogger(__name__)

# ========================= INPUT SCHEMAS ========================= #

class DestinationInfoInput(BaseModel):
    """Input schema for destination information."""
    destination: str = Field(..., description="Destination city or location name")

class DailyItineraryInput(BaseModel):
    """Input schema for daily itinerary creation."""
    destination: str = Field(..., description="Destination city or location")
    travel_dates: List[str] = Field(..., description="List of travel dates in YYYY-MM-DD format")
    weather_data: Optional[List[Dict[str, Any]]] = Field(None, description="Optional weather data for each day")
    budget_total: Optional[float] = Field(None, description="Optional total budget for the trip")
    travelers_count: int = Field(1, description="Number of travelers")

class DayActivitiesInput(BaseModel):
    """Input schema for planning day activities."""
    destination: str = Field(..., description="Destination city or location")
    day_number: int = Field(..., description="Day number in the trip (1-based)")
    total_days: int = Field(..., description="Total number of days in the trip")
    weather_temp_max: Optional[float] = Field(None, description="Maximum temperature for the day")
    precipitation_chance: Optional[float] = Field(None, description="Chance of precipitation (0-100)")

# ========================= HELPER FUNCTIONS ========================= #

class ItineraryServiceHelpers:
    """Shared helper functions and data for itinerary tools."""
    
    # Popular destinations and their main attractions
    DESTINATION_ATTRACTIONS = {
        "agra": {
            "must_visit": [
                "Taj Mahal - Best visited at sunrise or sunset",
                "Agra Fort - Explore the Mughal architecture",
                "Itimad-ud-Daulah (Baby Taj) - Beautiful marble work"
            ],
            "optional": [
                "Mehtab Bagh - Sunset view of Taj Mahal",
                "Local markets - Handicrafts and leather goods",
                "Fatehpur Sikri - Day trip to abandoned Mughal city"
            ],
            "food": [
                "Try Agra's famous petha (sweet)",
                "Mughlai cuisine at local restaurants",
                "Street food near Sadar Bazaar"
            ],
            "tips": [
                "Book Taj Mahal tickets online in advance",
                "Carry water and wear comfortable shoes",
                "Best light for photography: early morning or late afternoon"
            ]
        },
        "delhi": {
            "must_visit": [
                "Red Fort - Historic Mughal fortress",
                "India Gate - War memorial and iconic landmark",
                "Qutub Minar - UNESCO World Heritage site",
                "Lotus Temple - Modern architectural marvel"
            ],
            "optional": [
                "Chandni Chowk - Old Delhi markets and street food",
                "Humayun's Tomb - Beautiful garden tomb",
                "Connaught Place - Shopping and dining",
                "Akshardham Temple - Modern Hindu temple complex"
            ],
            "food": [
                "Street food at Chandni Chowk",
                "Paranthas at Paranthe Wali Gali",
                "South Indian food at Saravana Bhavan"
            ],
            "tips": [
                "Use Delhi Metro for efficient transport",
                "Carry cash for street vendors",
                "Avoid peak traffic hours (8-10 AM, 6-8 PM)"
            ]
        },
        "jaipur": {
            "must_visit": [
                "Amber Fort - Majestic hilltop fort",
                "City Palace - Royal residence and museum",
                "Hawa Mahal - Palace of Winds",
                "Jantar Mantar - Ancient astronomical observatory"
            ],
            "optional": [
                "Nahargarh Fort - Sunset views over Jaipur",
                "Jal Mahal - Palace in the middle of a lake",
                "Local bazaars - Textiles, jewelry, handicrafts"
            ],
            "food": [
                "Dal Baati Churma - Traditional Rajasthani dish",
                "Lassi at famous local shops",
                "Rajasthani thali at heritage restaurants"
            ],
            "tips": [
                "Negotiate prices at local markets",
                "Carry sunscreen and hat",
                "Evening sound and light show at Amber Fort"
            ]
        },
        "mumbai": {
            "must_visit": [
                "Gateway of India - Iconic monument",
                "Marine Drive - Scenic waterfront promenade",
                "Chhatrapati Shivaji Terminus - UNESCO World Heritage railway station",
                "Elephanta Caves - Ancient rock-cut temples"
            ],
            "optional": [
                "Colaba Causeway - Shopping and dining",
                "Juhu Beach - Popular beach area",
                "Sanjay Gandhi National Park - Nature and wildlife",
                "Film City - Bollywood studio tour"
            ],
            "food": [
                "Vada Pav - Mumbai's famous street food",
                "Pav Bhaji at local stalls",
                "Seafood at coastal restaurants"
            ],
            "tips": [
                "Use local trains during non-peak hours",
                "Try Mumbai's famous dabbawalas lunch delivery",
                "Best time to visit Marine Drive: evening sunset"
            ]
        },
        "goa": {
            "must_visit": [
                "Calangute and Baga Beaches - Popular beaches",
                "Basilica of Bom Jesus - UNESCO World Heritage church",
                "Aguada Fort - Historic Portuguese fort",
                "Dudhsagar Falls - Spectacular waterfall"
            ],
            "optional": [
                "Anjuna Flea Market - Shopping and local culture",
                "Palolem Beach - Quieter southern beach",
                "Old Goa Churches - Portuguese colonial architecture",
                "Spice plantations - Guided tours"
            ],
            "food": [
                "Goan fish curry and rice",
                "Bebinca - Traditional Goan dessert",
                "Fresh seafood at beach shacks"
            ],
            "tips": [
                "Rent a scooter for easy transportation",
                "Try water sports at major beaches",
                "Visit churches in the morning when they're open"
            ]
        }
    }
    
    @staticmethod
    def get_destination_info(destination: str) -> Dict[str, List[str]]:
        """Get attractions and tips for a destination."""
        destination_lower = destination.lower()
        
        for city, info in ItineraryServiceHelpers.DESTINATION_ATTRACTIONS.items():
            if city in destination_lower:
                return info
        
        # Generic fallback
        return {
            "must_visit": [f"Explore main attractions in {destination}"],
            "optional": ["Visit local markets", "Try local cuisine", "Walk around city center"],
            "food": ["Try local specialties", "Visit popular restaurants"],
            "tips": ["Research local customs", "Carry water and comfortable shoes", "Keep emergency contacts handy"]
        }
    
    @staticmethod
    def plan_day_activities(
        destination: str,
        day_number: int,
        total_days: int,
        weather_temp_max: Optional[float] = None,
        precipitation_chance: Optional[float] = None
    ) -> List[str]:
        """Plan activities for a specific day."""
        destination_info = ItineraryServiceHelpers.get_destination_info(destination)
        all_attractions = destination_info["must_visit"] + destination_info["optional"]
        activities = []
        
        if day_number == 1:
            activities.append("Arrival and check-in to accommodation")
            if destination_info["must_visit"]:
                activities.append(destination_info["must_visit"][0])
            activities.append("Explore nearby area and local food")
        
        elif day_number == total_days and total_days > 1:
            activities.append("Visit remaining attractions or shopping")
            activities.append("Pack and prepare for departure")
            activities.append("Departure")
        
        else:
            attractions_per_day = max(2, len(destination_info["must_visit"]) // max(1, total_days - 1))
            start_idx = (day_number - 2) * attractions_per_day
            end_idx = min(start_idx + attractions_per_day, len(all_attractions))
            activities.extend(all_attractions[start_idx:end_idx])
            
            if destination_info["food"]:
                food_idx = (day_number - 1) % len(destination_info["food"])
                activities.append(destination_info["food"][food_idx])
        
        # Weather-based adjustments
        if precipitation_chance and precipitation_chance > 70:
            activities.append("⚠️ High chance of rain - carry umbrella")
        if weather_temp_max and weather_temp_max > 35:
            activities.append("🌡️ Hot weather - plan indoor activities during midday")
        if weather_temp_max and weather_temp_max < 15:
            activities.append("🧥 Cold weather - dress warmly")
        
        return activities
    
    @staticmethod
    def estimate_daily_cost(
        budget_total: Optional[float],
        total_days: int,
        travelers_count: int
    ) -> float:
        """Estimate cost for a single day."""
        if not budget_total or total_days == 0:
            return 1500.0  # Default daily estimate in INR
        
        return budget_total / total_days
    
    @staticmethod
    def create_day_notes(
        weather_data: Optional[Dict[str, Any]],
        destination_info: Dict[str, List[str]],
        day_number: int
    ) -> str:
        """Create helpful notes for the day."""
        notes = []
        
        if weather_data:
            temp_min = weather_data.get("temp_min", "?")
            temp_max = weather_data.get("temp_max", "?")
            description = weather_data.get("description", "N/A")
            notes.append(f"Weather: {description}, {temp_min}-{temp_max}°C")
            
            precipitation_chance = weather_data.get("precipitation_chance", 0)
            if precipitation_chance > 50:
                notes.append("Chance of rain - plan indoor activities")
            
            wind_speed = weather_data.get("wind_speed", 0)
            if wind_speed > 15:
                notes.append("Windy conditions - secure loose items")
        
        if destination_info["tips"]:
            tip_idx = (day_number - 1) % len(destination_info["tips"])
            notes.append(f"Tip: {destination_info['tips'][tip_idx]}")
        
        return " | ".join(notes) if notes else "Enjoy your day of exploration!"

# ========================= LANGCHAIN TOOLS ========================= #

@tool
def get_destination_info(destination: str) -> Dict[str, Any]:
    """Get comprehensive information about a destination including attractions, food, and tips.
    
    Args:
        destination: Destination city or location name
    
    Returns:
        Dictionary with must-visit attractions, optional attractions, food recommendations, and travel tips
    """
    info = ItineraryServiceHelpers.get_destination_info(destination)
    
    return {
        "destination": destination,
        "must_visit": info["must_visit"],
        "optional_attractions": info["optional"],
        "food_recommendations": info["food"],
        "travel_tips": info["tips"],
        "total_attractions": len(info["must_visit"]) + len(info["optional"])
    }


@tool
def create_daily_itinerary(
    destination: str,
    travel_dates: List[str],
    weather_data: Optional[List[Dict[str, Any]]] = None,
    budget_total: Optional[float] = None,
    travelers_count: int = 1
) -> Dict[str, Any]:
    """Create a complete day-by-day itinerary for a trip.
    
    Args:
        destination: Destination city or location
        travel_dates: List of travel dates in YYYY-MM-DD format
        weather_data: Optional list of weather data dictionaries for each day
        budget_total: Optional total budget for the trip in INR
        travelers_count: Number of travelers (default: 1)
    
    Returns:
        Dictionary with day-by-day itinerary including activities, costs, and notes
    """
    try:
        destination_info = ItineraryServiceHelpers.get_destination_info(destination)
        itinerary_days = []
        total_days = len(travel_dates)
        
        for i, date_str in enumerate(travel_dates):
            day_number = i + 1
            
            # Get weather for the day
            day_weather = weather_data[i] if weather_data and i < len(weather_data) else None
            
            # Plan activities
            weather_temp_max = day_weather.get("temp_max") if day_weather else None
            precipitation_chance = day_weather.get("precipitation_chance") if day_weather else None
            
            activities = ItineraryServiceHelpers.plan_day_activities(
                destination,
                day_number,
                total_days,
                weather_temp_max,
                precipitation_chance
            )
            
            # Estimate daily cost
            estimated_cost = ItineraryServiceHelpers.estimate_daily_cost(
                budget_total,
                total_days,
                travelers_count
            )
            
            # Create notes
            notes = ItineraryServiceHelpers.create_day_notes(
                day_weather,
                destination_info,
                day_number
            )
            
            itinerary_days.append({
                "day": day_number,
                "date": date_str,
                "activities": activities,
                "notes": notes,
                "estimated_cost": round(estimated_cost, 2),
                "estimated_cost_formatted": f"INR {estimated_cost:,.2f}"
            })
        
        return {
            "destination": destination,
            "travelers_count": travelers_count,
            "total_days": total_days,
            "start_date": travel_dates[0],
            "end_date": travel_dates[-1],
            "itinerary": itinerary_days,
            "total_estimated_cost": round(budget_total, 2) if budget_total else round(estimated_cost * total_days, 2),
            "currency": "INR"
        }
    
    except Exception as e:
        logger.error(f"Daily itinerary creation failed: {e}")
        return {"error": str(e)}


@tool
def plan_single_day_activities(
    destination: str,
    day_number: int,
    total_days: int,
    weather_temp_max: Optional[float] = None,
    precipitation_chance: Optional[float] = None
) -> Dict[str, Any]:
    """Plan activities for a single day of a trip.
    
    Args:
        destination: Destination city or location
        day_number: Day number in the trip (1-based)
        total_days: Total number of days in the trip
        weather_temp_max: Optional maximum temperature for the day in Celsius
        precipitation_chance: Optional chance of precipitation (0-100)
    
    Returns:
        Dictionary with activities and recommendations for the day
    """
    try:
        activities = ItineraryServiceHelpers.plan_day_activities(
            destination,
            day_number,
            total_days,
            weather_temp_max,
            precipitation_chance
        )
        
        destination_info = ItineraryServiceHelpers.get_destination_info(destination)
        
        return {
            "destination": destination,
            "day_number": day_number,
            "total_days": total_days,
            "activities": activities,
            "weather_considerations": {
                "temp_max": weather_temp_max,
                "precipitation_chance": precipitation_chance
            },
            "destination_tips": destination_info["tips"]
        }
    
    except Exception as e:
        logger.error(f"Single day activity planning failed: {e}")
        return {"error": str(e)}


@tool
def get_food_recommendations(destination: str) -> Dict[str, Any]:
    """Get food and dining recommendations for a destination.
    
    Args:
        destination: Destination city or location
    
    Returns:
        Dictionary with food recommendations and local specialties
    """
    destination_info = ItineraryServiceHelpers.get_destination_info(destination)
    
    return {
        "destination": destination,
        "recommendations": destination_info["food"],
        "count": len(destination_info["food"])
    }


@tool
def get_travel_tips(destination: str) -> Dict[str, Any]:
    """Get travel tips and advice for a destination.
    
    Args:
        destination: Destination city or location
    
    Returns:
        Dictionary with helpful travel tips and advice
    """
    destination_info = ItineraryServiceHelpers.get_destination_info(destination)
    
    return {
        "destination": destination,
        "tips": destination_info["tips"],
        "count": len(destination_info["tips"])
    }


@tool
def get_available_destinations() -> Dict[str, Any]:
    """Get list of destinations with pre-loaded attraction information.
    
    Returns:
        Dictionary with available destinations and their attraction counts
    """
    destinations = {}
    
    for city, info in ItineraryServiceHelpers.DESTINATION_ATTRACTIONS.items():
        destinations[city.title()] = {
            "must_visit_count": len(info["must_visit"]),
            "optional_count": len(info["optional"]),
            "food_recommendations": len(info["food"]),
            "tips_count": len(info["tips"])
        }
    
    return {
        "destinations": destinations,
        "total_count": len(destinations),
        "supported_cities": list(destinations.keys())
    }


@tool
def optimize_itinerary_by_weather(
    destination: str,
    travel_dates: List[str],
    weather_data: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Optimize itinerary based on weather forecasts to plan indoor/outdoor activities.
    
    Args:
        destination: Destination city or location
        travel_dates: List of travel dates in YYYY-MM-DD format
        weather_data: List of weather data dictionaries for each day
    
    Returns:
        Dictionary with weather-optimized daily recommendations
    """
    try:
        destination_info = ItineraryServiceHelpers.get_destination_info(destination)
        optimized_days = []
        
        for i, date_str in enumerate(travel_dates):
            day_weather = weather_data[i] if i < len(weather_data) else {}
            
            temp_max = day_weather.get("temp_max", 25)
            precipitation = day_weather.get("precipitation_chance", 0)
            
            recommendations = []
            
            # Weather-based recommendations
            if precipitation > 70:
                recommendations.append("High chance of rain - ideal for indoor attractions")
                recommendations.append("Visit museums, temples, or covered markets")
            elif precipitation > 40:
                recommendations.append("Moderate rain chance - plan flexible activities")
                recommendations.append("Keep indoor backup options ready")
            else:
                recommendations.append("Good weather for outdoor sightseeing")
            
            if temp_max > 35:
                recommendations.append("Very hot - visit outdoor attractions early morning or late evening")
                recommendations.append("Stay hydrated and take breaks in air-conditioned places")
            elif temp_max < 15:
                recommendations.append("Cold weather - dress in layers")
                recommendations.append("Enjoy hot local beverages")
            
            optimized_days.append({
                "date": date_str,
                "day": i + 1,
                "weather": {
                    "temp_max": temp_max,
                    "precipitation_chance": precipitation,
                    "description": day_weather.get("description", "N/A")
                },
                "recommendations": recommendations
            })
        
        return {
            "destination": destination,
            "optimized_itinerary": optimized_days,
            "total_days": len(travel_dates)
        }
    
    except Exception as e:
        logger.error(f"Itinerary optimization failed: {e}")
        return {"error": str(e)}


@tool
def estimate_time_per_attraction(
    destination: str,
    attraction_count: int = None
) -> Dict[str, Any]:
    """Estimate time needed for attractions at a destination.
    
    Args:
        destination: Destination city or location
        attraction_count: Optional specific number of attractions to estimate for
    
    Returns:
        Dictionary with time estimates for visiting attractions
    """
    destination_info = ItineraryServiceHelpers.get_destination_info(destination)
    
    if attraction_count is None:
        attraction_count = len(destination_info["must_visit"])
    
    # Average time estimates
    time_per_major_attraction = 2.5  # hours
    time_per_optional_attraction = 1.5  # hours
    travel_time_between = 0.5  # hours
    
    major_attractions_time = len(destination_info["must_visit"]) * time_per_major_attraction
    optional_attractions_time = len(destination_info["optional"]) * time_per_optional_attraction
    total_travel_time = attraction_count * travel_time_between
    
    return {
        "destination": destination,
        "major_attractions": {
            "count": len(destination_info["must_visit"]),
            "estimated_hours": major_attractions_time,
            "avg_per_attraction": time_per_major_attraction
        },
        "optional_attractions": {
            "count": len(destination_info["optional"]),
            "estimated_hours": optional_attractions_time,
            "avg_per_attraction": time_per_optional_attraction
        },
        "travel_time_estimate": total_travel_time,
        "recommended_days": max(1, round((major_attractions_time + total_travel_time) / 8)),
        "notes": "Estimates assume 8 hours of sightseeing per day"
    }


# ========================= TOOL LIST FOR AGENT ========================= #

ITINERARY_TOOLS = [
    get_destination_info,
    create_daily_itinerary,
    plan_single_day_activities,
    get_food_recommendations,
    get_travel_tips,
    get_available_destinations,
    optimize_itinerary_by_weather,
    estimate_time_per_attraction
]