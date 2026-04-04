from typing import List
import json
from app.agents.base_agent import BaseAgent
from app.core.state import TravelState, WeatherInfo
from app.services.weather_service import WeatherService


class WeatherAgent(BaseAgent):
    """Sky Gazer - Weather forecasting agent"""
    
    def __init__(self):
        super().__init__(
            name="Sky Gazer",
            role="Weather Forecaster", 
            expertise="Weather analysis, climate patterns, and travel weather recommendations"
        )
        self.weather_service = WeatherService()
    
    def get_system_prompt(self) -> str:
        """Get the system prompt for the weather agent"""
        return """
        You are the Sky Gazer, a weather expert and travel advisor. Your role is to:
        
        1. Analyze weather data for travel destinations
        2. Provide weather-based travel recommendations
        3. Suggest appropriate clothing and gear
        4. Warn about potential weather-related travel issues
        5. Recommend optimal times for outdoor activities
        
        Always provide practical, actionable weather advice that helps travelers prepare.
        Be concise but informative. Focus on how weather will impact the travel experience.
        
        When given weather data, create a brief summary that includes:
        - General weather overview for the trip
        - Any weather concerns or highlights
        - Clothing recommendations
        - Activity suggestions based on weather
        """
    
    async def process(self, state: TravelState) -> TravelState:
        """Process weather information for the travel destination"""
        self.log_action("Starting weather analysis", f"Destination: {state['destination']}")
        
        try:
            # Fetch weather data using the weather service
            weather_data = await self.weather_service.get_weather_for_dates(
                location=state['destination'],
                dates=state['travel_dates']
            )
            
            if weather_data:
                # Store weather data in state
                state['weather_data'] = weather_data
                state['weather_complete'] = True
                
                # Generate weather insights using LLM
                weather_summary = await self._generate_weather_insights(weather_data, state)
                
                self.add_message_to_state(
                    state, 
                    f"Weather analysis complete for {state['destination']}. {weather_summary}"
                )
                
                self.log_action("Weather analysis completed successfully")
            else:
                raise Exception("No weather data retrieved")
                
        except Exception as e:
            error_msg = f"Failed to get weather data: {str(e)}"
            self.add_error_to_state(state, error_msg)
            state['weather_complete'] = True  # Mark as complete to continue workflow
            
        return state
    
    async def _generate_weather_insights(self, weather_data: List[WeatherInfo], state: TravelState) -> str:
        """Generate weather insights using the LLM"""
        # Format weather data for the LLM
        weather_summary = self._format_weather_for_llm(weather_data)
        location_context = self.format_location_context(state)
        
        user_input = f"""
        {location_context}
        
        Weather Data:
        {weather_summary}
        
        Please provide a concise weather summary and travel recommendations for this trip.
        """
        
        try:
            insights = await self.invoke_llm(self.get_system_prompt(), user_input)
            return insights
        except Exception as e:
            self.log_error("Failed to generate weather insights", str(e))
            return "Weather data retrieved successfully, but detailed analysis unavailable."
    
    def _format_weather_for_llm(self, weather_data: List[WeatherInfo]) -> str:
        """Format weather data for LLM consumption"""
        formatted_data = []
        
        for weather in weather_data:
            formatted_data.append(f"""
            Date: {weather.date}
            Temperature: {weather.temperature_min}°C - {weather.temperature_max}°C
            Conditions: {weather.description}
            Humidity: {weather.humidity}%
            Wind Speed: {weather.wind_speed} m/s
            Chance of Rain: {weather.precipitation_chance}%
            """)
        
        return "\n".join(formatted_data)
    
    def should_process(self, state: TravelState) -> bool:
        """Check if weather processing is needed"""
        return not state.get('weather_complete', False)
    
    def get_weather_summary(self, weather_data: List[WeatherInfo]) -> str:
        """Get a quick weather summary"""
        if not weather_data:
            return "No weather data available"
        
        avg_temp_max = sum(w.temperature_max for w in weather_data) / len(weather_data)
        avg_temp_min = sum(w.temperature_min for w in weather_data) / len(weather_data)
        
        conditions = [w.description for w in weather_data]
        most_common_condition = max(set(conditions), key=conditions.count)
        
        return f"Average temperature: {avg_temp_min:.1f}°C - {avg_temp_max:.1f}°C, mostly {most_common_condition}"