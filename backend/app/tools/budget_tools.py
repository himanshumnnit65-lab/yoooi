from typing import Dict, List, Optional, Any
from datetime import datetime
from langchain_core.tools import tool
from pydantic import BaseModel, Field
import logging
import re
import math

from app.core.state import BudgetBreakdown, RouteInfo

logger = logging.getLogger(__name__)

# ========================= INPUT SCHEMAS ========================= #

class TransportationCostInput(BaseModel):
    """Input schema for transportation cost calculation."""
    distance_km: float = Field(..., description="Distance in kilometers")
    transport_mode: str = Field(..., description="Transport mode: driving, train, bus, taxi, car")
    travelers_count: int = Field(..., description="Number of travelers")
    budget_category: str = Field("mid-range", description="Budget category: budget, mid-range, or luxury")

class AccommodationCostInput(BaseModel):
    """Input schema for accommodation cost calculation."""
    travel_dates: List[str] = Field(..., description="List of travel dates in YYYY-MM-DD format")
    travelers_count: int = Field(..., description="Number of travelers")
    budget_category: str = Field("mid-range", description="Budget category: budget, mid-range, or luxury")

class FoodCostInput(BaseModel):
    """Input schema for food cost calculation."""
    travel_dates: List[str] = Field(..., description="List of travel dates in YYYY-MM-DD format")
    travelers_count: int = Field(..., description="Number of travelers")
    budget_category: str = Field("mid-range", description="Budget category: budget, mid-range, or luxury")

class ActivitiesCostInput(BaseModel):
    """Input schema for activities cost calculation."""
    travel_dates: List[str] = Field(..., description="List of travel dates in YYYY-MM-DD format")
    travelers_count: int = Field(..., description="Number of travelers")
    budget_category: str = Field("mid-range", description="Budget category: budget, mid-range, or luxury")

class CompleteBudgetInput(BaseModel):
    """Input schema for complete budget calculation."""
    distance_km: Optional[float] = Field(None, description="Distance in kilometers (if known)")
    transport_mode: str = Field("driving", description="Transport mode: driving, train, bus, taxi")
    travel_dates: List[str] = Field(..., description="List of travel dates in YYYY-MM-DD format")
    travelers_count: int = Field(..., description="Number of travelers")
    budget_category: str = Field("mid-range", description="Budget category: budget, mid-range, or luxury")

class BudgetComparisonInput(BaseModel):
    """Input schema for budget comparison across categories."""
    distance_km: Optional[float] = Field(None, description="Distance in kilometers")
    transport_mode: str = Field("driving", description="Transport mode")
    travel_dates: List[str] = Field(..., description="List of travel dates")
    travelers_count: int = Field(..., description="Number of travelers")

# ========================= HELPER FUNCTIONS ========================= #

class BudgetServiceHelpers:
    """Shared helper functions and constants for budget tools."""
    
    # Indian travel cost estimates (INR)
    COSTS = {
        "fuel_per_liter": 105,  # Approximate petrol price in INR
        "car_mileage": 15,      # km per liter
        
        "train_per_km": {
            "sleeper": 0.50,
            "ac_3tier": 1.20,
            "ac_2tier": 1.80
        },
        
        "bus_per_km": {
            "ordinary": 1.50,
            "ac": 2.50
        },
        
        "taxi_per_km": 12,      # INR per km for outstation taxi
        
        "accommodation_per_night": {
            "budget": 1500,     # Budget hotel/guesthouse
            "mid-range": 3000,  # 3-star hotel
            "luxury": 6000      # 4-star+ hotel
        },
        
        "food_per_day": {
            "budget": 500,      # Local food, street food
            "mid-range": 1200,  # Restaurant meals
            "luxury": 2500      # Fine dining
        },
        
        "activities_per_day": {
            "budget": 300,      # Entry fees, local transport
            "mid-range": 800,   # Guided tours, attractions
            "luxury": 2000      # Private tours, premium experiences
        }
    }
    
    @staticmethod
    def extract_distance_km(distance_str: str) -> float:
        """Extract distance in kilometers from string."""
        if not distance_str:
            return 0
        
        # Look for numbers followed by km
        km_match = re.search(r'(\d+(?:\.\d+)?)\s*km', distance_str.lower())
        if km_match:
            return float(km_match.group(1))
        
        # Look for numbers followed by m (meters)
        m_match = re.search(r'(\d+(?:\.\d+)?)\s*m', distance_str.lower())
        if m_match:
            return float(m_match.group(1)) / 1000
        
        return 0
    
    @staticmethod
    def calculate_nights(travel_dates: List[str]) -> int:
        """Calculate number of nights from travel dates."""
        if len(travel_dates) <= 1:
            return 1
        
        try:
            start_date = datetime.strptime(travel_dates[0], "%Y-%m-%d")
            end_date = datetime.strptime(travel_dates[-1], "%Y-%m-%d")
            nights = max(1, (end_date - start_date).days)
            return nights
        except:
            return len(travel_dates) - 1 if len(travel_dates) > 1 else 1
    
    @staticmethod
    def calculate_rooms_needed(travelers_count: int) -> int:
        """Calculate rooms needed (assuming 2 people per room)."""
        return math.ceil(travelers_count / 2)
    
    @staticmethod
    def format_currency(amount: float, currency: str = "INR") -> str:
        """Format amount with currency."""
        return f"{currency} {amount:,.2f}"

# ========================= LANGCHAIN TOOLS ========================= #

@tool
def calculate_transportation_cost(
    distance_km: float,
    transport_mode: str,
    travelers_count: int,
    budget_category: str = "mid-range"
) -> Dict[str, Any]:
    """Calculate transportation costs for a trip.
    
    Args:
        distance_km: Distance in kilometers
        transport_mode: Transport mode (driving, car, train, bus, taxi)
        travelers_count: Number of travelers
        budget_category: Budget category - budget, mid-range, or luxury
    
    Returns:
        Dictionary with total cost and detailed breakdown
    """
    if distance_km <= 0:
        distance_km = 200  # Default assumption
    
    transport_mode = transport_mode.lower()
    costs = BudgetServiceHelpers.COSTS
    
    try:
        if "driving" in transport_mode or "car" in transport_mode:
            # Calculate fuel cost
            fuel_needed = distance_km / costs["car_mileage"]
            fuel_cost = fuel_needed * costs["fuel_per_liter"]
            
            # Add tolls (approximately 10% of fuel cost for highways)
            tolls = fuel_cost * 0.10
            
            total_cost = fuel_cost + tolls
            
            return {
                "total": round(total_cost, 2),
                "total_formatted": BudgetServiceHelpers.format_currency(total_cost),
                "breakdown": {
                    "fuel": round(fuel_cost, 2),
                    "tolls": round(tolls, 2),
                    "distance_km": distance_km,
                    "fuel_per_liter": costs["fuel_per_liter"],
                    "mileage": costs["car_mileage"]
                },
                "transport_mode": transport_mode,
                "currency": "INR"
            }
        
        elif "train" in transport_mode:
            # Select rate based on budget category
            if budget_category == "budget":
                rate_per_km = costs["train_per_km"]["sleeper"]
                class_type = "Sleeper"
            elif budget_category == "luxury":
                rate_per_km = costs["train_per_km"]["ac_2tier"]
                class_type = "AC 2-Tier"
            else:
                rate_per_km = costs["train_per_km"]["ac_3tier"]
                class_type = "AC 3-Tier"
            
            total_cost = distance_km * rate_per_km * travelers_count
            
            return {
                "total": round(total_cost, 2),
                "total_formatted": BudgetServiceHelpers.format_currency(total_cost),
                "breakdown": {
                    "train_fare": round(total_cost, 2),
                    "rate_per_km": rate_per_km,
                    "distance_km": distance_km,
                    "travelers": travelers_count,
                    "class": class_type
                },
                "transport_mode": transport_mode,
                "currency": "INR"
            }
        
        elif "bus" in transport_mode:
            if budget_category == "budget":
                rate_per_km = costs["bus_per_km"]["ordinary"]
                bus_type = "Ordinary"
            else:
                rate_per_km = costs["bus_per_km"]["ac"]
                bus_type = "AC"
            
            total_cost = distance_km * rate_per_km * travelers_count
            
            return {
                "total": round(total_cost, 2),
                "total_formatted": BudgetServiceHelpers.format_currency(total_cost),
                "breakdown": {
                    "bus_fare": round(total_cost, 2),
                    "rate_per_km": rate_per_km,
                    "distance_km": distance_km,
                    "travelers": travelers_count,
                    "type": bus_type
                },
                "transport_mode": transport_mode,
                "currency": "INR"
            }
        
        else:
            # Default to taxi calculation
            total_cost = distance_km * costs["taxi_per_km"]
            
            return {
                "total": round(total_cost, 2),
                "total_formatted": BudgetServiceHelpers.format_currency(total_cost),
                "breakdown": {
                    "taxi_fare": round(total_cost, 2),
                    "rate_per_km": costs["taxi_per_km"],
                    "distance_km": distance_km
                },
                "transport_mode": "taxi",
                "currency": "INR"
            }
    
    except Exception as e:
        logger.error(f"Transportation cost calculation failed: {e}")
        return {"error": str(e)}


@tool
def calculate_accommodation_cost(
    travel_dates: List[str],
    travelers_count: int,
    budget_category: str = "mid-range"
) -> Dict[str, Any]:
    """Calculate accommodation costs for a trip.
    
    Args:
        travel_dates: List of travel dates in YYYY-MM-DD format
        travelers_count: Number of travelers
        budget_category: Budget category - budget, mid-range, or luxury
    
    Returns:
        Dictionary with total cost and detailed breakdown
    """
    try:
        costs = BudgetServiceHelpers.COSTS
        
        # Calculate number of nights
        nights = BudgetServiceHelpers.calculate_nights(travel_dates)
        
        # Get cost per night based on budget
        cost_per_night = costs["accommodation_per_night"][budget_category]
        
        # Calculate rooms needed
        rooms_needed = BudgetServiceHelpers.calculate_rooms_needed(travelers_count)
        
        total_cost = cost_per_night * nights * rooms_needed
        
        return {
            "total": round(total_cost, 2),
            "total_formatted": BudgetServiceHelpers.format_currency(total_cost),
            "breakdown": {
                "cost_per_night": cost_per_night,
                "nights": nights,
                "rooms": rooms_needed,
                "travelers": travelers_count,
                "category": budget_category
            },
            "currency": "INR"
        }
    
    except Exception as e:
        logger.error(f"Accommodation cost calculation failed: {e}")
        return {"error": str(e)}


@tool
def calculate_food_cost(
    travel_dates: List[str],
    travelers_count: int,
    budget_category: str = "mid-range"
) -> Dict[str, Any]:
    """Calculate food costs for a trip.
    
    Args:
        travel_dates: List of travel dates in YYYY-MM-DD format
        travelers_count: Number of travelers
        budget_category: Budget category - budget, mid-range, or luxury
    
    Returns:
        Dictionary with total cost and detailed breakdown
    """
    try:
        costs = BudgetServiceHelpers.COSTS
        
        days = len(travel_dates) if travel_dates else 1
        cost_per_day = costs["food_per_day"][budget_category]
        
        total_cost = cost_per_day * days * travelers_count
        
        return {
            "total": round(total_cost, 2),
            "total_formatted": BudgetServiceHelpers.format_currency(total_cost),
            "breakdown": {
                "cost_per_day": cost_per_day,
                "days": days,
                "travelers": travelers_count,
                "category": budget_category
            },
            "currency": "INR"
        }
    
    except Exception as e:
        logger.error(f"Food cost calculation failed: {e}")
        return {"error": str(e)}


@tool
def calculate_activities_cost(
    travel_dates: List[str],
    travelers_count: int,
    budget_category: str = "mid-range"
) -> Dict[str, Any]:
    """Calculate activities and sightseeing costs for a trip.
    
    Args:
        travel_dates: List of travel dates in YYYY-MM-DD format
        travelers_count: Number of travelers
        budget_category: Budget category - budget, mid-range, or luxury
    
    Returns:
        Dictionary with total cost and detailed breakdown
    """
    try:
        costs = BudgetServiceHelpers.COSTS
        
        days = len(travel_dates) if travel_dates else 1
        cost_per_day = costs["activities_per_day"][budget_category]
        
        total_cost = cost_per_day * days * travelers_count
        
        return {
            "total": round(total_cost, 2),
            "total_formatted": BudgetServiceHelpers.format_currency(total_cost),
            "breakdown": {
                "cost_per_day": cost_per_day,
                "days": days,
                "travelers": travelers_count,
                "category": budget_category
            },
            "currency": "INR"
        }
    
    except Exception as e:
        logger.error(f"Activities cost calculation failed: {e}")
        return {"error": str(e)}


@tool
def calculate_complete_budget(
    distance_km: Optional[float],
    transport_mode: str,
    travel_dates: List[str],
    travelers_count: int,
    budget_category: str = "mid-range"
) -> Dict[str, Any]:
    """Calculate complete trip budget including all categories.
    
    Args:
        distance_km: Distance in kilometers (optional, will use default if not provided)
        transport_mode: Transport mode (driving, train, bus, taxi)
        travel_dates: List of travel dates in YYYY-MM-DD format
        travelers_count: Number of travelers
        budget_category: Budget category - budget, mid-range, or luxury
    
    Returns:
        Dictionary with complete budget breakdown
    """
    try:
        # Use default distance if not provided
        if not distance_km or distance_km <= 0:
            distance_km = 200
        
        # Calculate each category
        transport_result = calculate_transportation_cost.invoke({
            "distance_km": distance_km,
            "transport_mode": transport_mode,
            "travelers_count": travelers_count,
            "budget_category": budget_category
        })
        
        accommodation_result = calculate_accommodation_cost.invoke({
            "travel_dates": travel_dates,
            "travelers_count": travelers_count,
            "budget_category": budget_category
        })
        
        food_result = calculate_food_cost.invoke({
            "travel_dates": travel_dates,
            "travelers_count": travelers_count,
            "budget_category": budget_category
        })
        
        activities_result = calculate_activities_cost.invoke({
            "travel_dates": travel_dates,
            "travelers_count": travelers_count,
            "budget_category": budget_category
        })
        
        # Calculate total
        total_cost = (
            transport_result.get("total", 0) +
            accommodation_result.get("total", 0) +
            food_result.get("total", 0) +
            activities_result.get("total", 0)
        )
        
        return {
            "total": round(total_cost, 2),
            "total_formatted": BudgetServiceHelpers.format_currency(total_cost),
            "budget_category": budget_category,
            "travelers_count": travelers_count,
            "days": len(travel_dates),
            "breakdown": {
                "transportation": transport_result,
                "accommodation": accommodation_result,
                "food": food_result,
                "activities": activities_result
            },
            "currency": "INR",
            "per_person": round(total_cost / travelers_count, 2) if travelers_count > 0 else 0
        }
    
    except Exception as e:
        logger.error(f"Complete budget calculation failed: {e}")
        return {"error": str(e)}


@tool
def compare_budget_categories(
    distance_km: Optional[float],
    transport_mode: str,
    travel_dates: List[str],
    travelers_count: int
) -> Dict[str, Any]:
    """Compare trip costs across budget categories (budget, mid-range, luxury).
    
    Args:
        distance_km: Distance in kilometers
        transport_mode: Transport mode
        travel_dates: List of travel dates
        travelers_count: Number of travelers
    
    Returns:
        Dictionary with cost comparison across all budget categories
    """
    try:
        categories = ["budget", "mid-range", "luxury"]
        comparison = {}
        
        for category in categories:
            budget_result = calculate_complete_budget.invoke({
                "distance_km": distance_km,
                "transport_mode": transport_mode,
                "travel_dates": travel_dates,
                "travelers_count": travelers_count,
                "budget_category": category
            })
            
            comparison[category] = {
                "total": budget_result.get("total", 0),
                "total_formatted": budget_result.get("total_formatted", ""),
                "per_person": budget_result.get("per_person", 0),
                "transportation": budget_result.get("breakdown", {}).get("transportation", {}).get("total", 0),
                "accommodation": budget_result.get("breakdown", {}).get("accommodation", {}).get("total", 0),
                "food": budget_result.get("breakdown", {}).get("food", {}).get("total", 0),
                "activities": budget_result.get("breakdown", {}).get("activities", {}).get("total", 0)
            }
        
        return {
            "comparison": comparison,
            "travelers_count": travelers_count,
            "days": len(travel_dates),
            "transport_mode": transport_mode,
            "distance_km": distance_km,
            "currency": "INR",
            "recommendation": "mid-range" if travelers_count <= 2 else "budget"
        }
    
    except Exception as e:
        logger.error(f"Budget comparison failed: {e}")
        return {"error": str(e)}


@tool
def get_budget_categories() -> Dict[str, Any]:
    """Get information about available budget categories and their characteristics.
    
    Returns:
        Dictionary with budget category details
    """
    costs = BudgetServiceHelpers.COSTS
    
    return {
        "categories": ["budget", "mid-range", "luxury"],
        "details": {
            "budget": {
                "description": "Budget-friendly travel with basic amenities",
                "accommodation_per_night": costs["accommodation_per_night"]["budget"],
                "food_per_day": costs["food_per_day"]["budget"],
                "activities_per_day": costs["activities_per_day"]["budget"],
                "train_class": "Sleeper",
                "bus_type": "Ordinary"
            },
            "mid-range": {
                "description": "Comfortable travel with good amenities",
                "accommodation_per_night": costs["accommodation_per_night"]["mid-range"],
                "food_per_day": costs["food_per_day"]["mid-range"],
                "activities_per_day": costs["activities_per_day"]["mid-range"],
                "train_class": "AC 3-Tier",
                "bus_type": "AC"
            },
            "luxury": {
                "description": "Premium travel with top-tier amenities",
                "accommodation_per_night": costs["accommodation_per_night"]["luxury"],
                "food_per_day": costs["food_per_day"]["luxury"],
                "activities_per_day": costs["activities_per_day"]["luxury"],
                "train_class": "AC 2-Tier",
                "bus_type": "AC Sleeper"
            }
        },
        "currency": "INR"
    }


@tool
def get_cost_breakdown_info() -> Dict[str, Any]:
    """Get detailed information about cost calculation parameters.
    
    Returns:
        Dictionary with all cost parameters used in calculations
    """
    costs = BudgetServiceHelpers.COSTS
    
    return {
        "transportation": {
            "fuel_per_liter": costs["fuel_per_liter"],
            "car_mileage": costs["car_mileage"],
            "train_rates": costs["train_per_km"],
            "bus_rates": costs["bus_per_km"],
            "taxi_per_km": costs["taxi_per_km"]
        },
        "accommodation": costs["accommodation_per_night"],
        "food": costs["food_per_day"],
        "activities": costs["activities_per_day"],
        "currency": "INR",
        "notes": {
            "rooms": "Calculated as 2 people per room",
            "tolls": "Estimated at 10% of fuel cost for driving",
            "days": "Based on number of dates in travel_dates list",
            "nights": "Calculated from first to last date in travel_dates"
        }
    }


# ========================= TOOL LIST FOR AGENT ========================= #

BUDGET_TOOLS = [
    calculate_transportation_cost,
    calculate_accommodation_cost,
    calculate_food_cost,
    calculate_activities_cost,
    calculate_complete_budget,
    compare_budget_categories,
    get_budget_categories,
    get_cost_breakdown_info
]