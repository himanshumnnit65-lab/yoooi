import httpx
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from langchain_core.tools import tool
from pydantic import BaseModel, Field
import logging

from app.config.settings import settings
from app.core.state import EventInfo

logger = logging.getLogger(__name__)

# ========================= INPUT SCHEMAS ========================= #

class EventSearchInput(BaseModel):
    """Input schema for basic event search."""
    location: str = Field(..., description="Location/city to search for events")
    start_date: str = Field(..., description="Start date in YYYY-MM-DD format")
    end_date: str = Field(..., description="End date in YYYY-MM-DD format")
    categories: Optional[List[str]] = Field(None, description="Event categories to filter (e.g., ['music', 'sports'])")
    size: int = Field(20, description="Maximum number of events to return")

class EventDatesInput(BaseModel):
    """Input schema for events on specific dates."""
    location: str = Field(..., description="Location/city to search for events")
    dates: List[str] = Field(..., description="List of specific dates in YYYY-MM-DD format")
    categories: Optional[List[str]] = Field(None, description="Event categories to filter")

class PopularEventsInput(BaseModel):
    """Input schema for popular events."""
    location: str = Field(..., description="Location/city to search for events")
    days_ahead: int = Field(30, description="Number of days ahead to search")
    limit: int = Field(10, description="Maximum number of events to return")

class EventCategoryInput(BaseModel):
    """Input schema for category-specific search."""
    location: str = Field(..., description="Location/city to search for events")
    category: str = Field(..., description="Event category (music, sports, arts, etc.)")
    start_date: str = Field(..., description="Start date in YYYY-MM-DD format")
    end_date: str = Field(..., description="End date in YYYY-MM-DD format")
    limit: int = Field(20, description="Maximum number of events to return")

class EventQueryInput(BaseModel):
    """Input schema for custom query search."""
    query: str = Field(..., description="Search query (e.g., 'jazz concerts', 'food festivals')")
    location: str = Field("", description="Optional location to narrow search")
    date_filter: str = Field("any", description="Date filter: any, today, tomorrow, week, weekend, next_week, month, next_month")
    is_virtual: bool = Field(False, description="Whether to search for virtual events")
    limit: int = Field(20, description="Maximum number of events to return")

class EventDetailsInput(BaseModel):
    """Input schema for event details."""
    event_id: str = Field(..., description="Unique event identifier")

# ========================= HELPER FUNCTIONS ========================= #

class EventServiceHelpers:
    """Shared helper functions for event tools."""
    
    @staticmethod
    def get_date_filter(start_date: str, end_date: str) -> str:
        """Convert date range to OpenWeb Ninja date filter."""
        try:
            start_dt = datetime.fromisoformat(start_date).date()
            end_dt = datetime.fromisoformat(end_date).date()
            today = datetime.now().date()
            
            days_to_start = (start_dt - today).days
            days_to_end = (end_dt - today).days
            
            if days_to_start <= 0 and days_to_end >= 0:
                return "today"
            elif days_to_start == 1:
                return "tomorrow"
            elif days_to_start <= 7:
                return "week"
            elif days_to_start <= 14:
                return "next_week"
            elif days_to_start <= 30:
                return "month"
            elif days_to_start <= 60:
                return "next_month"
            else:
                return "any"
        except:
            return "any"
    
    @staticmethod
    def determine_category(event_data: Dict, venue_info: Dict) -> str:
        """Determine event category based on venue type and event name."""
        name = event_data.get("name", "").lower()
        venue_subtypes = venue_info.get("subtypes", [])
        
        # Check venue types first
        if "movie_theater" in venue_subtypes:
            return "film"
        elif "sports_club" in venue_subtypes or "stadium" in venue_subtypes:
            return "sports"
        elif "night_club" in venue_subtypes or "bar" in venue_subtypes:
            return "music"
        elif "museum" in venue_subtypes or "art_gallery" in venue_subtypes:
            return "arts"
        elif "theater" in venue_subtypes:
            return "theatre"
        elif "restaurant" in venue_subtypes:
            return "food"
        
        # Check event name for keywords
        if any(word in name for word in ["concert", "music", "band", "singer", "dj"]):
            return "music"
        elif any(word in name for word in ["sport", "match", "game", "championship", "tournament"]):
            return "sports"
        elif any(word in name for word in ["art", "gallery", "exhibition", "museum"]):
            return "arts"
        elif any(word in name for word in ["theater", "theatre", "play", "drama"]):
            return "theatre"
        elif any(word in name for word in ["comedy", "comedian", "stand-up"]):
            return "comedy"
        elif any(word in name for word in ["festival", "fair", "celebration"]):
            return "miscellaneous"
        elif any(word in name for word in ["food", "wine", "dining", "restaurant"]):
            return "food"
        elif any(word in name for word in ["family", "kids", "children"]):
            return "family"
        elif any(word in name for word in ["business", "conference", "seminar", "workshop"]):
            return "business"
        elif any(word in name for word in ["film", "movie", "cinema", "screening"]):
            return "film"
        
        return "miscellaneous"
    
    @staticmethod
    def parse_openweb_events(data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse OpenWeb Ninja API response into event dictionaries."""
        events = []
        
        if data.get("status") != "OK":
            logger.warning(f"OpenWeb Ninja API returned status: {data.get('status')}")
            return events
        
        events_data = data.get("data", [])
        
        for event_data in events_data:
            try:
                name = event_data.get("name", "Unknown Event")
                description = event_data.get("description") or ""
                
                # Parse date and time
                start_time = event_data.get("start_time", "")
                end_time = event_data.get("end_time", "")
                
                if start_time:
                    start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    date_str = start_dt.date().isoformat()
                    time_str = start_dt.time().strftime('%H:%M')
                else:
                    date_str = ""
                    time_str = ""
                
                # Extract venue information
                venue_info = event_data.get("venue", {})
                venue_name = venue_info.get("name", "TBA")
                venue_address = venue_info.get("full_address", "")
                
                # Determine category
                category = EventServiceHelpers.determine_category(event_data, venue_info)
                
                # Extract pricing information
                price_min = None
                price_max = None
                currency = "USD"
                
                # Get event URL and image
                event_url = event_data.get("link") or ""
                image_url = event_data.get("thumbnail", "")
                
                events.append({
                    "name": name,
                    "date": date_str,
                    "time": time_str,
                    "venue": venue_name,
                    "address": venue_address,
                    "category": category,
                    "price_min": price_min,
                    "price_max": price_max,
                    "currency": currency,
                    "description": description,
                    "url": event_url,
                    "image_url": image_url
                })
                
            except Exception as e:
                logger.error(f"Error parsing event data: {str(e)}")
                continue
        
        return events
    
    @staticmethod
    def filter_events(
        events: List[Dict[str, Any]], 
        start_date: str, 
        end_date: str, 
        categories: List[str] = None
    ) -> List[Dict[str, Any]]:
        """Filter events by date range and categories."""
        filtered = []
        
        try:
            start_dt = datetime.fromisoformat(start_date).date()
            end_dt = datetime.fromisoformat(end_date).date()
        except:
            return events
        
        for event in events:
            # Filter by date
            if event.get("date"):
                try:
                    event_date = datetime.fromisoformat(event["date"]).date()
                    if not (start_dt <= event_date <= end_dt):
                        continue
                except:
                    continue
            
            # Filter by categories
            if categories and event.get("category", "").lower() not in [cat.lower() for cat in categories]:
                continue
            
            filtered.append(event)
        
        return filtered
    
    @staticmethod
    def create_fallback_events(location: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Create fallback event data when API is unavailable."""
        fallback_events = [
            {
                "name": f"Local Music Festival - {location}",
                "date": start_date,
                "time": "19:00",
                "venue": f"Central Park, {location}",
                "address": f"Main Street, {location}",
                "category": "music",
                "price_min": 25.0,
                "price_max": 75.0,
                "currency": "USD",
                "description": "Annual local music festival featuring various artists",
                "url": "",
                "image_url": ""
            },
            {
                "name": "Art Gallery Opening",
                "date": start_date,
                "time": "18:00",
                "venue": f"Modern Art Gallery, {location}",
                "address": f"Art District, {location}",
                "category": "arts",
                "price_min": 0.0,
                "price_max": 15.0,
                "currency": "USD",
                "description": "Contemporary art exhibition opening",
                "url": "",
                "image_url": ""
            },
            {
                "name": "Food & Wine Festival",
                "date": end_date if start_date != end_date else start_date,
                "time": "12:00",
                "venue": f"Convention Center, {location}",
                "address": f"Downtown, {location}",
                "category": "food",
                "price_min": 30.0,
                "price_max": 85.0,
                "currency": "USD",
                "description": "Local food and wine tasting festival",
                "url": "",
                "image_url": ""
            }
        ]
        
        logger.info(f"Using fallback events for {location}")
        return fallback_events

# ========================= LANGCHAIN TOOLS ========================= #

@tool
async def search_events(
    location: str,
    start_date: str,
    end_date: str,
    categories: Optional[List[str]] = None,
    size: int = 20
) -> Dict[str, Any]:
    """Search for events in a location within a date range.
    
    Args:
        location: City or location to search for events
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        categories: Optional list of event categories to filter (music, sports, arts, etc.)
        size: Maximum number of events to return (default: 20)
    
    Returns:
        Dictionary with events list and search metadata
    """
    api_key = getattr(settings, 'openweb_ninja_api_key', None)
    base_url = getattr(settings, 'openweb_ninja_base_url', None)
    
    if not api_key or not base_url:
        logger.warning("OpenWeb Ninja API key not configured, using fallback data")
        fallback = EventServiceHelpers.create_fallback_events(location, start_date, end_date)
        return {
            "location": location,
            "start_date": start_date,
            "end_date": end_date,
            "events": fallback,
            "count": len(fallback),
            "fallback": True
        }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            date_filter = EventServiceHelpers.get_date_filter(start_date, end_date)
            
            params = {
                "query": f"Events in {location}",
                "date": date_filter,
                "is_virtual": False,
                "start": 0
            }
            
            headers = {
                "x-api-key": api_key,
                "Content-Type": "application/json"
            }
            
            resp = await client.get(base_url, params=params, headers=headers)
            resp.raise_for_status()
            
            data = resp.json()
            events = EventServiceHelpers.parse_openweb_events(data)
            
            # Filter events by date range and categories
            filtered_events = EventServiceHelpers.filter_events(events, start_date, end_date, categories)
            
            return {
                "location": location,
                "start_date": start_date,
                "end_date": end_date,
                "categories": categories,
                "events": filtered_events[:size],
                "count": len(filtered_events[:size]),
                "total_found": len(filtered_events)
            }
            
    except httpx.TimeoutException:
        logger.error("OpenWeb Ninja API timeout")
        fallback = EventServiceHelpers.create_fallback_events(location, start_date, end_date)
        return {
            "location": location,
            "events": fallback,
            "count": len(fallback),
            "error": "API timeout",
            "fallback": True
        }
    except Exception as e:
        logger.error(f"Failed to search events: {str(e)}")
        fallback = EventServiceHelpers.create_fallback_events(location, start_date, end_date)
        return {
            "location": location,
            "events": fallback,
            "count": len(fallback),
            "error": str(e),
            "fallback": True
        }


@tool
async def get_events_for_dates(
    location: str,
    dates: List[str],
    categories: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Get events for specific dates at a location.
    
    Args:
        location: City or location to search for events
        dates: List of specific dates in YYYY-MM-DD format
        categories: Optional list of event categories to filter
    
    Returns:
        Dictionary with events matching the specific dates
    """
    if not dates:
        return {
            "location": location,
            "events": [],
            "count": 0,
            "error": "No dates provided"
        }
    
    # Sort dates to get range
    sorted_dates = sorted(dates)
    start_date = sorted_dates[0]
    end_date = sorted_dates[-1]
    
    # Get all events in the date range
    result = await search_events.ainvoke({
        "location": location,
        "start_date": start_date,
        "end_date": end_date,
        "categories": categories,
        "size": 50
    })
    
    # Filter events that fall on the specific dates
    all_events = result.get("events", [])
    target_dates = set(dates)
    filtered_events = [e for e in all_events if e.get("date") in target_dates]
    
    return {
        "location": location,
        "dates": dates,
        "categories": categories,
        "events": filtered_events,
        "count": len(filtered_events)
    }


@tool
async def get_popular_events(
    location: str,
    days_ahead: int = 30,
    limit: int = 10
) -> Dict[str, Any]:
    """Get popular upcoming events in a location.
    
    Args:
        location: City or location to search for events
        days_ahead: Number of days ahead to search (default: 30)
        limit: Maximum number of events to return (default: 10)
    
    Returns:
        Dictionary with popular upcoming events
    """
    start_date = datetime.now().date().isoformat()
    end_date = (datetime.now().date() + timedelta(days=days_ahead)).isoformat()
    
    result = await search_events.ainvoke({
        "location": location,
        "start_date": start_date,
        "end_date": end_date,
        "size": limit
    })
    
    return {
        "location": location,
        "days_ahead": days_ahead,
        "events": result.get("events", []),
        "count": result.get("count", 0)
    }


@tool
async def search_events_by_category(
    location: str,
    category: str,
    start_date: str,
    end_date: str,
    limit: int = 20
) -> Dict[str, Any]:
    """Search for events in a specific category.
    
    Args:
        location: City or location to search for events
        category: Event category (music, sports, arts, theatre, comedy, family, business, food, film, miscellaneous)
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        limit: Maximum number of events to return (default: 20)
    
    Returns:
        Dictionary with events in the specified category
    """
    result = await search_events.ainvoke({
        "location": location,
        "start_date": start_date,
        "end_date": end_date,
        "categories": [category],
        "size": limit
    })
    
    return {
        "location": location,
        "category": category,
        "start_date": start_date,
        "end_date": end_date,
        "events": result.get("events", []),
        "count": result.get("count", 0)
    }


@tool
async def search_events_with_query(
    query: str,
    location: str = "",
    date_filter: str = "any",
    is_virtual: bool = False,
    limit: int = 20
) -> Dict[str, Any]:
    """Search events using a custom query string.
    
    Args:
        query: Search query (e.g., 'jazz concerts', 'food festivals', 'comedy shows')
        location: Optional location to narrow search
        date_filter: Date filter - any, today, tomorrow, week, weekend, next_week, month, next_month
        is_virtual: Whether to search for virtual events (default: False)
        limit: Maximum number of events to return (default: 20)
    
    Returns:
        Dictionary with events matching the query
    """
    api_key = getattr(settings, 'openweb_ninja_api_key', None)
    base_url = getattr(settings, 'openweb_ninja_base_url', None)
    
    if not api_key or not base_url:
        logger.warning("OpenWeb Ninja API key not configured")
        return {
            "query": query,
            "events": [],
            "count": 0,
            "error": "API not configured"
        }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Build search query
            search_query = query
            if location:
                search_query = f"{query} in {location}"
            
            params = {
                "query": search_query,
                "date": date_filter,
                "is_virtual": is_virtual,
                "start": 0
            }
            
            headers = {
                "x-api-key": api_key,
                "Content-Type": "application/json"
            }
            
            resp = await client.get(base_url, params=params, headers=headers)
            resp.raise_for_status()
            
            data = resp.json()
            events = EventServiceHelpers.parse_openweb_events(data)
            
            return {
                "query": query,
                "location": location,
                "date_filter": date_filter,
                "is_virtual": is_virtual,
                "events": events[:limit],
                "count": len(events[:limit]),
                "total_found": len(events)
            }
            
    except Exception as e:
        logger.error(f"Failed to search events with query: {str(e)}")
        return {
            "query": query,
            "events": [],
            "count": 0,
            "error": str(e)
        }


@tool
async def get_event_details(event_id: str) -> Dict[str, Any]:
    """Get detailed information about a specific event.
    
    Args:
        event_id: Unique event identifier
    
    Returns:
        Dictionary with detailed event information
    """
    api_key = getattr(settings, 'openweb_ninja_api_key', None)
    base_url = getattr(settings, 'openweb_ninja_base_url', None)
    
    if not api_key or not base_url:
        logger.warning("OpenWeb Ninja API key not configured")
        return {"error": "API not configured"}
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            params = {"event_id": event_id}
            headers = {
                "x-api-key": api_key,
                "Content-Type": "application/json"
            }
            
            resp = await client.get(
                f"{base_url}/event-details",
                params=params,
                headers=headers
            )
            resp.raise_for_status()
            
            data = resp.json()
            if data.get("status") == "OK" and data.get("data"):
                event_data = data["data"]
                events = EventServiceHelpers.parse_openweb_events({"status": "OK", "data": [event_data]})
                
                if events:
                    return {
                        "event_id": event_id,
                        "event": events[0]
                    }
            
            return {"error": "Event not found"}
            
    except Exception as e:
        logger.error(f"Failed to get event details: {str(e)}")
        return {"error": str(e)}


@tool
def get_event_categories() -> Dict[str, Any]:
    """Get list of available event categories.
    
    Returns:
        Dictionary with list of event categories
    """
    categories = [
        "music",
        "sports",
        "arts",
        "theatre",
        "comedy",
        "family",
        "business",
        "food",
        "film",
        "miscellaneous"
    ]
    
    return {
        "categories": categories,
        "count": len(categories),
        "descriptions": {
            "music": "Concerts, festivals, live performances",
            "sports": "Games, matches, tournaments",
            "arts": "Gallery openings, exhibitions, art shows",
            "theatre": "Plays, musicals, theatrical performances",
            "comedy": "Stand-up comedy, comedy shows",
            "family": "Family-friendly events and activities",
            "business": "Conferences, seminars, networking events",
            "food": "Food festivals, wine tastings, culinary events",
            "film": "Movie screenings, film festivals",
            "miscellaneous": "Other events and activities"
        }
    }


@tool
def get_date_filters() -> Dict[str, Any]:
    """Get list of available date filters for event searches.
    
    Returns:
        Dictionary with available date filter options
    """
    filters = [
        "any",
        "today",
        "tomorrow",
        "week",
        "weekend",
        "next_week",
        "month",
        "next_month"
    ]
    
    return {
        "filters": filters,
        "count": len(filters),
        "descriptions": {
            "any": "Events at any time",
            "today": "Events happening today",
            "tomorrow": "Events happening tomorrow",
            "week": "Events within the next 7 days",
            "weekend": "Events this weekend",
            "next_week": "Events next week",
            "month": "Events within the next 30 days",
            "next_month": "Events next month"
        }
    }


# ========================= TOOL LIST FOR AGENT ========================= #

EVENT_TOOLS = [
    search_events,
    get_events_for_dates,
    get_popular_events,
    search_events_by_category,
    search_events_with_query,
    get_event_details,
    get_event_categories,
    get_date_filters
]