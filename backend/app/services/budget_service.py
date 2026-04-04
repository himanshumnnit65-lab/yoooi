from typing import Dict, List, Optional
from datetime import datetime
from app.core.state import BudgetBreakdown, RouteInfo
import logging
import re

logger = logging.getLogger(__name__)


class BudgetService:
    """Simple budget estimation service for Indian travel"""
    
    def __init__(self):
        # Simple Indian travel cost estimates (INR)
        self.costs = {
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
    
    def extract_distance_km(self, distance_str: str) -> float:
        """Extract distance in kilometers from string"""
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
    
    def calculate_transportation_cost(
        self, 
        route_info: Optional[RouteInfo], 
        travelers_count: int,
        budget_category: str = "mid-range"
    ) -> Dict[str, float]:
        """Calculate transportation costs"""
        
        if not route_info:
            return {
                "total": 1000 * travelers_count,
                "breakdown": {"estimated": 1000}
            }
        
        distance_km = self.extract_distance_km(route_info.distance)
        if distance_km == 0:
            distance_km = 200  # Default assumption for missing data
        
        transport_mode = route_info.transport_mode.lower()
        
        if "driving" in transport_mode or "car" in transport_mode:
            # Calculate fuel cost
            fuel_needed = distance_km / self.costs["car_mileage"]
            fuel_cost = fuel_needed * self.costs["fuel_per_liter"]
            
            # Add tolls (approximately 10% of fuel cost for highways)
            tolls = fuel_cost * 0.10
            
            total_cost = fuel_cost + tolls
            
            return {
                "total": total_cost,
                "breakdown": {
                    "fuel": fuel_cost,
                    "tolls": tolls,
                    "distance_km": distance_km
                }
            }
        
        elif "train" in transport_mode:
            # Use AC 3-tier as default for mid-range
            rate_per_km = self.costs["train_per_km"]["ac_3tier"]
            if budget_category == "budget":
                rate_per_km = self.costs["train_per_km"]["sleeper"]
            elif budget_category == "luxury":
                rate_per_km = self.costs["train_per_km"]["ac_2tier"]
            
            total_cost = distance_km * rate_per_km * travelers_count
            
            return {
                "total": total_cost,
                "breakdown": {
                    "train_fare": total_cost,
                    "rate_per_km": rate_per_km,
                    "distance_km": distance_km
                }
            }
        
        elif "bus" in transport_mode:
            rate_per_km = self.costs["bus_per_km"]["ac"] if budget_category != "budget" else self.costs["bus_per_km"]["ordinary"]
            total_cost = distance_km * rate_per_km * travelers_count
            
            return {
                "total": total_cost,
                "breakdown": {
                    "bus_fare": total_cost,
                    "rate_per_km": rate_per_km,
                    "distance_km": distance_km
                }
            }
        
        else:
            # Default to taxi calculation
            total_cost = distance_km * self.costs["taxi_per_km"]
            
            return {
                "total": total_cost,
                "breakdown": {
                    "taxi_fare": total_cost,
                    "rate_per_km": self.costs["taxi_per_km"],
                    "distance_km": distance_km
                }
            }
    
    def calculate_accommodation_cost(
        self,
        travel_dates: List[str],
        travelers_count: int,
        budget_category: str = "mid-range"
    ) -> Dict[str, float]:
        """Calculate accommodation costs"""
        
        # Calculate number of nights
        if len(travel_dates) <= 1:
            nights = 1
        else:
            try:
                start_date = datetime.strptime(travel_dates[0], "%Y-%m-%d")
                end_date = datetime.strptime(travel_dates[-1], "%Y-%m-%d")
                nights = max(1, (end_date - start_date).days)
            except:
                nights = len(travel_dates) - 1 if len(travel_dates) > 1 else 1
        
        # Get cost per night based on budget
        cost_per_night = self.costs["accommodation_per_night"][budget_category]
        
        # Calculate rooms needed (assuming 2 people per room)
        import math
        rooms_needed = math.ceil(travelers_count / 2)
        
        total_cost = cost_per_night * nights * rooms_needed
        
        return {
            "total": total_cost,
            "breakdown": {
                "cost_per_night": cost_per_night,
                "nights": nights,
                "rooms": rooms_needed,
                "category": budget_category
            }
        }
    
    def calculate_food_cost(
        self,
        travel_dates: List[str],
        travelers_count: int,
        budget_category: str = "mid-range"
    ) -> Dict[str, float]:
        """Calculate food costs"""
        
        days = len(travel_dates) if travel_dates else 1
        cost_per_day = self.costs["food_per_day"][budget_category]
        
        total_cost = cost_per_day * days * travelers_count
        
        return {
            "total": total_cost,
            "breakdown": {
                "cost_per_day": cost_per_day,
                "days": days,
                "travelers": travelers_count,
                "category": budget_category
            }
        }
    
    def calculate_activities_cost(
        self,
        travel_dates: List[str],
        travelers_count: int,
        budget_category: str = "mid-range"
    ) -> Dict[str, float]:
        """Calculate activities and sightseeing costs"""
        
        days = len(travel_dates) if travel_dates else 1
        cost_per_day = self.costs["activities_per_day"][budget_category]
        
        total_cost = cost_per_day * days * travelers_count
        
        return {
            "total": total_cost,
            "breakdown": {
                "cost_per_day": cost_per_day,
                "days": days,
                "travelers": travelers_count,
                "category": budget_category
            }
        }
    
    def create_budget_breakdown(
        self,
        route_info: Optional[RouteInfo],
        travel_dates: List[str],
        travelers_count: int,
        budget_category: str = "mid-range"
    ) -> BudgetBreakdown:
        """Create complete budget breakdown"""
        
        # Calculate each category
        transport_cost = self.calculate_transportation_cost(route_info, travelers_count, budget_category)
        accommodation_cost = self.calculate_accommodation_cost(travel_dates, travelers_count, budget_category)
        food_cost = self.calculate_food_cost(travel_dates, travelers_count, budget_category)
        activities_cost = self.calculate_activities_cost(travel_dates, travelers_count, budget_category)
        
        # Calculate totals
        total_cost = (
            transport_cost["total"] + 
            accommodation_cost["total"] + 
            food_cost["total"] + 
            activities_cost["total"]
        )
        
        return BudgetBreakdown(
            transportation=transport_cost["total"],
            accommodation=accommodation_cost["total"],
            food=food_cost["total"],
            activities=activities_cost["total"],
            total=total_cost,
            currency="INR"
        )