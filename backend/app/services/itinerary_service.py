from typing import Dict, List, Optional
from datetime import datetime, timedelta
from app.core.state import ItineraryDay, WeatherInfo, BudgetBreakdown
import logging

logger = logging.getLogger(__name__)


class ItineraryService:
    """Simple itinerary planning service"""
    
    def __init__(self):
        # Popular destinations and their main attractions
        self.destination_attractions = {
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
            }
        }
    
    def get_destination_info(self, destination: str) -> Dict:
        """Get attractions and tips for a destination"""
        destination_lower = destination.lower()
        
        # Find matching destination
        for city, info in self.destination_attractions.items():
            if city in destination_lower:
                return info
        
        # Generic fallback for unknown destinations
        return {
            "must_visit": [f"Explore main attractions in {destination}"],
            "optional": ["Visit local markets", "Try local cuisine", "Walk around city center"],
            "food": ["Try local specialties", "Visit popular restaurants"],
            "tips": ["Research local customs", "Carry water and comfortable shoes", "Keep emergency contacts handy"]
        }
    
    def create_daily_itinerary(
        self,
        destination: str,
        travel_dates: List[str],
        weather_data: Optional[List[WeatherInfo]] = None,
        budget_data: Optional[BudgetBreakdown] = None,
        travelers_count: int = 1
    ) -> List[ItineraryDay]:
        """Create day-by-day itinerary"""
        
        itinerary_days = []
        destination_info = self.get_destination_info(destination)
        
        # Distribute attractions across days
        all_attractions = destination_info["must_visit"] + destination_info["optional"]
        
        for i, date_str in enumerate(travel_dates):
            day_number = i + 1
            
            # Get weather for the day if available
            day_weather = None
            if weather_data and i < len(weather_data):
                day_weather = weather_data[i]
            
            # Plan activities based on day and weather
            activities = self._plan_day_activities(
                day_number, 
                all_attractions, 
                destination_info,
                day_weather,
                len(travel_dates)
            )
            
            # Estimate daily cost
            estimated_cost = self._estimate_daily_cost(budget_data, len(travel_dates), travelers_count)
            
            # Create notes based on weather and attractions
            notes = self._create_day_notes(day_weather, destination_info, day_number)
            
            itinerary_day = ItineraryDay(
                day=day_number,
                date=date_str,
                activities=activities,
                notes=notes,
                estimated_cost=estimated_cost
            )
            
            itinerary_days.append(itinerary_day)
        
        return itinerary_days
    
    def _plan_day_activities(
        self, 
        day_number: int, 
        all_attractions: List[str], 
        destination_info: Dict,
        weather: Optional[WeatherInfo],
        total_days: int
    ) -> List[str]:
        """Plan activities for a specific day"""
        
        activities = []
        
        if day_number == 1:
            # First day - arrival and major attraction
            activities.append("Arrival and check-in to accommodation")
            if destination_info["must_visit"]:
                activities.append(destination_info["must_visit"][0])
            activities.append("Explore nearby area and local food")
            
        elif day_number == total_days and total_days > 1:
            # Last day - departure
            activities.append("Visit remaining attractions or shopping")
            activities.append("Pack and prepare for departure")
            activities.append("Departure")
            
        else:
            # Middle days - main sightseeing
            attractions_per_day = max(2, len(destination_info["must_visit"]) // max(1, total_days - 1))
            
            start_idx = (day_number - 2) * attractions_per_day
            end_idx = min(start_idx + attractions_per_day, len(all_attractions))
            
            for attraction in all_attractions[start_idx:end_idx]:
                activities.append(attraction)
            
            # Add food recommendation
            if destination_info["food"]:
                food_idx = (day_number - 1) % len(destination_info["food"])
                activities.append(destination_info["food"][food_idx])
        
        # Weather-based activity adjustments
        if weather:
            if weather.precipitation_chance > 70:
                activities.append("⚠️ High chance of rain - carry umbrella")
            if weather.temperature_max > 35:
                activities.append("🌡️ Hot weather - plan indoor activities during midday")
            if weather.temperature_max < 15:
                activities.append("🧥 Cold weather - dress warmly")
        
        return activities
    
    def _estimate_daily_cost(
        self, 
        budget_data: Optional[BudgetBreakdown], 
        total_days: int,
        travelers_count: int
    ) -> float:
        """Estimate cost for a single day"""
        
        if not budget_data or total_days == 0:
            return 1500.0  # Default daily estimate
        
        # Calculate daily averages (excluding transportation which is usually one-time)
        daily_accommodation = budget_data.accommodation / max(1, total_days - 1)  # Nights
        daily_food = budget_data.food / total_days
        daily_activities = budget_data.activities / total_days
        
        daily_transport = 200  # Local transport estimate
        
        return daily_accommodation + daily_food + daily_activities + daily_transport
    
    def _create_day_notes(
        self, 
        weather: Optional[WeatherInfo], 
        destination_info: Dict,
        day_number: int
    ) -> str:
        """Create helpful notes for the day"""
        
        notes = []
        
        # Weather notes
        if weather:
            notes.append(f"Weather: {weather.description}, {weather.temperature_min}-{weather.temperature_max}°C")
            
            if weather.precipitation_chance > 50:
                notes.append("Chance of rain - plan indoor activities")
            
            if weather.wind_speed > 15:
                notes.append("Windy conditions - secure loose items")
        
        # General tips for the day
        if destination_info["tips"] and day_number <= len(destination_info["tips"]):
            tip_idx = (day_number - 1) % len(destination_info["tips"])
            notes.append(f"Tip: {destination_info['tips'][tip_idx]}")
        
        return " | ".join(notes) if notes else "Enjoy your day of exploration!"