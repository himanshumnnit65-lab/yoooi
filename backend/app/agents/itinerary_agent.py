# ItineraryAgent.py

import json
import re
from typing import Any, List, Optional,Dict
from app.agents.base_agent import BaseAgent
from app.core.state import TravelState, ItineraryDay
from app.services.itinerary_service import ItineraryService
import logging

logger = logging.getLogger(__name__)

class EnhancedItineraryAgent(BaseAgent):
    """Enhanced Itinerary Weaver with structured data extraction"""
    
    def __init__(self):
        super().__init__(
            name="Itinerary Weaver",
            role="Day Planner & Activity Coordinator",
            expertise="Itinerary creation, activity scheduling, and travel timeline optimization"
        )
        from app.services.itinerary_service import ItineraryService
        self.itinerary_service = ItineraryService()
    
    def get_system_prompt(self) -> str:
        return """
        You are the Itinerary Weaver, a day-by-day travel planning expert. Your role is to:
        1. Create detailed daily itineraries with optimal activity scheduling
        2. Balance must-see attractions with local experiences
        3. Consider weather conditions for activity planning
        4. Optimize travel time and minimize backtracking
        5. Include practical tips for each day
        6. Suggest realistic timeframes for activities
        
        IMPORTANT: At the end of your response, provide a JSON block with structured itinerary data:
        ```json
        {
            "optimized_itinerary": [
                {
                    "day": 1,
                    "date": "YYYY-MM-DD",
                    "activities": [
                        {
                            "time": "HH:MM AM/PM",
                            "activity": "Activity name",
                            "duration": "X hours",
                            "cost": number,
                            "tips": "Practical tip"
                        }
                    ],
                    "total_cost": number,
                    "weather_considerations": "Weather notes"
                }
            ],
            "transport_details": {
                "recommended_trains": ["Train name - departure time"],
                "booking_tips": ["Tip 1", "Tip 2"],
                "local_transport": "Recommendations"
            },
            "key_tips": [
                "Important tip 1",
                "Important tip 2"
            ]
        }
        ```
        """
    
    async def process(self, state: TravelState) -> TravelState:
        """Enhanced processing with structured data extraction"""
        self.log_action("Starting enhanced itinerary planning", f"Destination: {state['destination']}, Days: {len(state['travel_dates'])}")
        
        try:
            # Get initial itinerary from service
            initial_itinerary = self.itinerary_service.create_daily_itinerary(
                destination=state['destination'],
                travel_dates=state['travel_dates'],
                weather_data=state.get('weather_data'),
                budget_data=state.get('budget_data'),
                travelers_count=state.get('travelers_count', 1)
            )
            
            # Generate enhanced insights with structured data
            itinerary_analysis = await self._generate_enhanced_itinerary_insights(initial_itinerary, state)
            
            # Extract structured data from LLM response
            structured_data = self._extract_structured_itinerary_data(itinerary_analysis)
            
            # Update itinerary with LLM recommendations if available
            if structured_data and 'optimized_itinerary' in structured_data:
                # Convert structured data back to ItineraryDay objects
                from app.core.state import ItineraryDay
                enhanced_itinerary = []
                
                for day_data in structured_data['optimized_itinerary']:
                    activities = []
                    if isinstance(day_data.get('activities'), list):
                        for activity in day_data['activities']:
                            if isinstance(activity, dict):
                                activity_str = f"{activity.get('time', '')}: {activity.get('activity', '')} ({activity.get('duration', '')})"
                                if activity.get('tips'):
                                    activity_str += f" - {activity['tips']}"
                                activities.append(activity_str)
                            else:
                                activities.append(str(activity))
                    
                    day = ItineraryDay(
                        day=day_data.get('day', 1),
                        date=day_data.get('date', ''),
                        activities=activities,
                        notes=day_data.get('weather_considerations', ''),
                        estimated_cost=day_data.get('total_cost', 1500)
                    )
                    enhanced_itinerary.append(day)
                
                state['itinerary_data'] = enhanced_itinerary
                
                # Store additional structured data
                state['transport_details'] = structured_data.get('transport_details', {})
                state['itinerary_tips'] = structured_data.get('key_tips', [])
            else:
                state['itinerary_data'] = initial_itinerary
            
            self.add_message_to_state(state, itinerary_analysis)
            self.log_action("Enhanced itinerary planning completed successfully")
            
        except Exception as e:
            error_msg = f"Failed to create enhanced itinerary: {str(e)}"
            self.add_error_to_state(state, error_msg)
            logger.error(error_msg)
            
            # Fallback to basic itinerary
            state['itinerary_data'] = self._create_fallback_itinerary(state)
                
        finally:
            state['itinerary_complete'] = True
            
        return state
    
    def _extract_structured_itinerary_data(self, llm_response: str) -> Optional[Dict[str, Any]]:
        """Extract structured JSON data from LLM response"""
        try:
            # Look for JSON code blocks
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', llm_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                return json.loads(json_str)
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse structured itinerary data: {e}")
        except Exception as e:
            logger.error(f"Error extracting structured itinerary data: {e}")
        
        return None

    async def _generate_enhanced_itinerary_insights(self, itinerary_days, state: TravelState) -> str:
        """Generate enhanced insights with structured data request"""
        
        itinerary_summary = self._format_itinerary_for_llm(itinerary_days)
        location_context = self.format_location_context(state)
        
        user_input = f"""
        {location_context}
        
        Current Itinerary:
        {itinerary_summary}
        
        Please provide:
        1. Optimized daily schedule with specific times
        2. Specific transport recommendations (train names, timings)
        3. Activity duration estimates
        4. Cost breakdown per activity
        5. Weather-based activity suggestions
        6. Practical booking and timing tips
        
        Include the structured JSON data at the end of your response.
        """
        
        try:
            insights = await self.invoke_llm(self.get_system_prompt(), user_input)
            return insights
        except Exception as e:
            logger.error(f"Enhanced itinerary insights failed: {str(e)}")
            return f"Day-by-day itinerary created for {len(itinerary_days)} days."
    
    def _format_itinerary_for_llm(self, itinerary_days) -> str:
        """Format itinerary data for LLM consumption"""
        formatted_days = []
        for day in itinerary_days:
            activities = "\n  • ".join(day.activities)
            day_info = f"DAY {day.day} ({day.date}):\n  • {activities}\nNotes: {day.notes}\nEstimated Cost: ₹{day.estimated_cost:,.0f}"
            formatted_days.append(day_info)
        return "\n".join(formatted_days)
    
    def should_process(self, state: TravelState) -> bool:
        return not state.get('itinerary_complete', False)
    
    def _create_fallback_itinerary(self, state: TravelState):
        """Create fallback itinerary when processing fails"""
        from app.core.state import ItineraryDay
        fallback_days = []
        for i, date_str in enumerate(state['travel_dates']):
            day_number = i + 1
            if day_number == 1:
                activities = ["Arrive", "Check-in", "Explore nearby area"]
            elif day_number == len(state['travel_dates']):
                activities = ["Sightseeing", "Pack", "Departure"]
            else:
                activities = ["Explore attractions", "Local dining", "Cultural activities"]
            fallback_days.append(ItineraryDay(day=day_number, date=date_str, activities=activities, notes="Fallback itinerary", estimated_cost=1500))
        return fallback_days