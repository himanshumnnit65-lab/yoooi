from typing import List
from fastapi import APIRouter, HTTPException
from datetime import datetime
import time
from app.models.requests import TravelPlanRequest, WeatherRequest
from app.models.response import (
    TravelPlanResponse, 
    WeatherResponse, 
    HealthResponse, 
    ErrorResponse
)
from app.agents.weather_agent import WeatherAgent
from app.agents.maps_agent import MapsAgent
from app.agents.budget_agent import BudgetAgent
from app.agents.itinerary_agent import ItineraryAgent
from app.agents.event_agent import EventsAgent
from app.core.state import EventInfo, create_initial_state
import logging

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Initialize all agents
weather_agent = WeatherAgent()
maps_agent = MapsAgent()
budget_agent = BudgetAgent()
itinerary_agent = ItineraryAgent()
event_agent = EventsAgent()



@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version="1.0.0"
    )


@router.post("/weather", response_model=WeatherResponse)
async def get_weather(request: WeatherRequest):
    """Get weather information for a location and dates"""
    try:
        logger.info(f"Weather request for {request.location}")
        
        weather_data = await weather_agent.weather_service.get_weather_for_dates(
            location=request.location,
            dates=request.dates
        )
        
        return WeatherResponse(
            success=True,
            data=weather_data
        )
        
    except Exception as e:
        logger.error(f"Weather request failed: {str(e)}")
        return WeatherResponse(
            success=False,
            error=f"Failed to get weather data: {str(e)}"
        )

@router.post("/route")
async def get_route(origin: str, destination: str, transport_mode: str = "driving"):
    """Get route information between two locations"""
    try:
        logger.info(f"Route request: {origin} to {destination} by {transport_mode}")
        
        route_data = await maps_agent.maps_service.get_route_between_locations(
            origin=origin,
            destination=destination,
            transport_mode=transport_mode
        )
        
        if route_data:
            return {
                "success": True,
                "data": {
                    "distance": route_data.distance,
                    "duration": route_data.duration,
                    "transport_mode": route_data.transport_mode,
                    "steps": route_data.steps[:5],  # First 5 steps only
                    "traffic_info": route_data.traffic_info
                }
            }
        else:
            return {
                "success": False,
                "error": "Failed to calculate route"
            }
        
    except Exception as e:
        logger.error(f"Route request failed: {str(e)}")
        return {
            "success": False,
            "error": f"Failed to get route data: {str(e)}"
        }


@router.get("/route/compare/{origin}/{destination}")
async def compare_routes(origin: str, destination: str):
    """Compare different transportation modes for a journey"""
    try:
        logger.info(f"Route comparison request: {origin} to {destination}")
        
        comparison = await maps_agent.compare_transport_modes(origin, destination)
        
        return {
            "success": True,
            "origin": origin,
            "destination": destination,
            "routes": comparison
        }
        
    except Exception as e:
     
        logger.error(f"Route comparison failed: {str(e)}")
        return {
            "success": False,
            "error": f"Failed to compare routes: {str(e)}"
        }

@router.post("/budget")
async def get_budget_estimate(
    origin: str, 
    destination: str, 
    travel_dates: str,  # comma-separated dates
    travelers: int = 1,
    budget_category: str = "mid-range"
):
    """Get budget estimate for a trip"""
    try:
        logger.info(f"Budget request: {origin} to {destination}, {travelers} travelers")
        
        dates_list = travel_dates.split(",")
        
        # Create minimal state for budget calculation
        state = create_initial_state(
            destination=destination,
            origin=origin,
            travel_dates=dates_list,
            travelers_count=travelers,
            budget_range=budget_category
        )
        
        # Get route info for accurate transport costs
        route_info = await maps_agent.maps_service.get_route_between_locations(origin, destination)
        state['route_data'] = route_info
        
        # Calculate budget
        state = await budget_agent.process(state)
        
        budget_data = state.get('budget_data')
        if budget_data:
            return {
                "success": True,
                "budget": {
                    "total": budget_data.total,
                    "transportation": budget_data.transportation,
                    "accommodation": budget_data.accommodation,
                    "food": budget_data.food,
                    "activities": budget_data.activities,
                    "currency": budget_data.currency,
                    "breakdown": budget_agent.format_budget_summary(budget_data)
                }
            }
        else:
            return {"success": False, "error": "Budget calculation failed"}
        
    except Exception as e:
        logger.error(f"Budget request failed: {str(e)}")
        return {"success": False, "error": f"Failed to calculate budget: {str(e)}"}


@router.post("/itinerary")
async def create_itinerary(
    destination: str,
    travel_dates: str,  # comma-separated dates
    travelers: int = 1
):
    """Create a detailed itinerary"""
    try:
        logger.info(f"Itinerary request: {destination}, {travelers} travelers")
        
        dates_list = travel_dates.split(",")
        
        # Create state for itinerary planning
        state = create_initial_state(
            destination=destination,
            origin="",  # Not needed for itinerary
            travel_dates=dates_list,
            travelers_count=travelers
        )
        
        # Get weather data to optimize itinerary
        state = await weather_agent.process(state)
        
        # Create itinerary
        state = await itinerary_agent.process(state)
        
        itinerary_data = state.get('itinerary_data')
        if itinerary_data:
            return {
                "success": True,
                "itinerary": [
                    {
                        "day": day.day,
                        "date": day.date,
                        "activities": day.activities,
                        "notes": day.notes,
                        "estimated_cost": day.estimated_cost
                    } for day in itinerary_data
                ],
                "summary": itinerary_agent.format_itinerary_summary(itinerary_data)
            }
        else:
            return {"success": False, "error": "Itinerary creation failed"}
        
    except Exception as e:
        logger.error(f"Itinerary request failed: {str(e)}")
        return {"success": False, "error": f"Failed to create itinerary: {str(e)}"}


@router.post("/plan", response_model=TravelPlanResponse)
async def create_travel_plan(request: TravelPlanRequest):
    """Create a comprehensive travel plan with all agents"""
    start_time = time.time()
    
    try:
        logger.info(f"Complete travel plan request: {request.origin} to {request.destination}")
        
        # Create initial state
        state = create_initial_state(
            destination=request.destination,
            origin=request.origin,
            travel_dates=request.travel_dates,
            travelers_count=request.travelers_count,
            budget_range=request.budget_range
        )
        
        # Process with all agents sequentially
        state = await weather_agent.process(state)
        state = await maps_agent.process(state)
        state = await budget_agent.process(state)
        state = await itinerary_agent.process(state)
        state = await event_agent.process(state)

        event_recommendations = None
        event_categories_found = None

        if state.get('events_data'):
            event_recommendations = await _generate_event_recommendations(state['events_data'])
            event_categories_found = list(set(event.category for event in state['events_data']))
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Generate comprehensive trip summary
        trip_summary = await _generate_complete_trip_summary(state)
        
        return TravelPlanResponse(
            success=True,
            message="Complete travel plan created successfully",
            trip_summary=trip_summary,
            weather=state.get('weather_data'),
            route=state.get('route_data'),
            budget=state.get('budget_data'),
            itinerary=state.get('itinerary_data'),
            errors=state.get('errors', []),
            processing_time=processing_time,
             event_recommendations=event_recommendations,
            event_categories_found=event_categories_found
        )
        
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Complete travel plan failed: {str(e)}")
        
        return TravelPlanResponse(
            success=False,
            message=f"Travel planning failed: {str(e)}",
            errors=[str(e)],
            processing_time=processing_time
        )


async def _generate_complete_trip_summary(state):
    """Generate a comprehensive trip summary with all agent data"""
    messages = state.get('messages', [])
    weather_data = state.get('weather_data', [])
    route_data = state.get('route_data')
    budget_data = state.get('budget_data')
    events_data = state.get('events_data', [])
    itinerary_data = state.get('itinerary_data', [])
    
    summary_parts = [
        f"Trip from {state['origin']} to {state['destination']}",
        f"Travel dates: {', '.join(state['travel_dates'])}",
        f"Travelers: {state['travelers_count']}"
    ]
    
    # Add weather summary
    if weather_data:
        avg_temp_max = sum(w.temperature_max for w in weather_data) / len(weather_data)
        avg_temp_min = sum(w.temperature_min for w in weather_data) / len(weather_data)
        summary_parts.append(
            f"Weather: {avg_temp_min:.1f}°C - {avg_temp_max:.1f}°C"
        )
     # Add route summary
    if route_data:
        summary_parts.append(
            f"Route: {route_data.distance} in {route_data.duration} by {route_data.transport_mode}"
        )
      # Add budget summary
    if budget_data:
        summary_parts.append(f"Total Budget: ₹{budget_data.total:,.0f}")
    
    if itinerary_data:
        total_activities = sum(len(day.activities) for day in itinerary_data)
        summary_parts.append(f"Itinerary: {len(itinerary_data)} days, {total_activities} activities")

    if events_data:
        categories = set(event.category for event in events_data)
        venues = set(event.venue for event in events_data)
        free_events = sum(1 for event in events_data if hasattr(event, 'is_free') and event.is_free())
        
        event_summary = f"Events: {len(events_data)} events across {len(categories)} categories at {len(venues)} venues"
        if free_events > 0:
            event_summary += f" ({free_events} free)"
        summary_parts.append(event_summary)
        
        # Highlight top categories
        category_counts = {}
        for event in events_data:
            category_counts[event.category] = category_counts.get(event.category, 0) + 1
        
        top_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:2]
        if top_categories:
            top_cat_summary = ", ".join([f"{count} {cat}" for cat, count in top_categories])
            summary_parts.append(f"Top events: {top_cat_summary}")
    
    
    # Add agent messages
    if messages:
        summary_parts.extend(messages)
    
    return " | ".join(summary_parts)


@router.get("/test-weather/{location}")
async def test_weather_service(location: str, dates: str = None):
    """Test endpoint for weather service"""
    try:
        if not dates:
            # Default to next 3 days
            from datetime import date, timedelta
            test_dates = []
            for i in range(3):
                test_date = date.today() + timedelta(days=i)
                test_dates.append(test_date.strftime("%Y-%m-%d"))
        else:
            test_dates = dates.split(",")
        
        weather_data = await weather_agent.weather_service.get_weather_for_dates(
            location=location,
            dates=test_dates
        )
        
        return {
            "success": True,
            "location": location,
            "dates": test_dates,
            "weather_data": [w.dict() for w in weather_data]
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "location": location
        }


@router.get("/test-route/{origin}/{destination}")
async def test_route_service(origin: str, destination: str, mode: str = "driving"):
    """Test endpoint for route service"""
    try:
        route_data = await maps_agent.maps_service.get_route_between_locations(
            origin=origin,
            destination=destination,
            transport_mode=mode
        )
        
        if route_data:
            return {
                "success": True,
                "origin": origin,
                "destination": destination,
                "transport_mode": mode,
                "route_data": route_data.dict()
            }
        else:
            return {
                "success": False,
                "error": "Route calculation failed",
                "origin": origin,
                "destination": destination
            }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "origin": origin,
            "destination": destination
        }
    

async def _generate_event_recommendations(events_data: List[EventInfo]) -> str:
    """Generate specific event recommendations based on OpenWeb Ninja data"""
    if not events_data:
        return "No events available for your travel dates"
    
    recommendations = []
    
    # Find must-see events (prioritize unique venues and categories)
    unique_venues = {}
    for event in events_data:
        if event.venue not in unique_venues:
            unique_venues[event.venue] = event
    
    # Categorize recommendations
    free_events = [e for e in events_data if hasattr(e, 'is_free') and e.is_free()]
    cultural_events = [e for e in events_data if e.category in ['arts', 'theatre', 'film']]
    entertainment_events = [e for e in events_data if e.category in ['music', 'comedy']]
    
    if free_events:
        recommendations.append(f"Free events: {len(free_events)} available including {free_events[0].name}")
    
    if cultural_events:
        recommendations.append(f"Cultural highlights: {cultural_events[0].name} at {cultural_events[0].venue}")
    
    if entertainment_events:
        recommendations.append(f"Entertainment: {entertainment_events[0].name}")
    
    # Venue recommendations
    popular_venues = {}
    for event in events_data:
        popular_venues[event.venue] = popular_venues.get(event.venue, 0) + 1
    
    top_venue = max(popular_venues.items(), key=lambda x: x[1]) if popular_venues else None
    if top_venue and top_venue[1] > 1:
        recommendations.append(f"Popular venue: {top_venue[0]} ({top_venue[1]} events)")
    
    return " | ".join(recommendations) if recommendations else "Various events available across different categories"

