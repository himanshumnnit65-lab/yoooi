from typing import Dict, Optional
import asyncio
from app.agents.base_agent import BaseAgent
from app.core.state import TravelState, RouteInfo
from app.services.maps_service import MapsService


class MapsAgent(BaseAgent):
    """Trailblazer - Route planning and navigation agent"""
    
    def __init__(self):
        super().__init__(
            name="Trailblazer",
            role="Route Planner & Navigator", 
            expertise="Route optimization, transportation analysis, and travel logistics"
        )
        self.maps_service = MapsService()
    
    def get_system_prompt(self) -> str:
        """Get the system prompt for the maps agent"""
        return """
        You are the Trailblazer, a route planning and navigation expert. Your role is to:
        
        1. Analyze route options between origin and destination
        2. Compare different transportation modes (driving, walking, cycling)
        3. Provide practical travel recommendations based on distance and duration
        4. Suggest optimal transportation methods considering factors like time, cost, and convenience
        5. Identify potential travel challenges or considerations
        
        Always provide practical, actionable route advice that helps travelers make informed decisions.
        Be concise but informative. Focus on how route choices will impact the overall travel experience.
        
        When given route data, create a brief analysis that includes:
        - Recommended transportation mode and reasoning
        - Journey overview with key details
        - Any notable considerations or tips
        - Alternative options if relevant
        """
    
    async def process(self, state: TravelState) -> TravelState:
        """Process route information for the travel itinerary"""
        self.log_action("Starting route analysis", f"From {state['origin']} to {state['destination']}")
        
        try:
            # Get primary route (driving by default) 
            transport_mode = state.get('preferred_transport', 'driving')
            
            primary_route = await self.maps_service.get_route_between_locations(
                origin=state['origin'],
                destination=state['destination'],
                transport_mode=transport_mode
            )
            
            if primary_route:
                # Store primary route data in state
                state['route_data'] = primary_route
                
                # Get alternative transportation options (but don't fail if they don't work)
                alternative_routes = await self._get_alternative_routes(state)
                
                # Generate route insights using LLM
                route_analysis = await self._generate_route_insights(
                    primary_route, alternative_routes, state
                )
                
                self.add_message_to_state(
                    state, 
                    f"Route analysis complete. {route_analysis}"
                )
                
                self.log_action("Route analysis completed successfully")
            else:
                # Create fallback route information
                fallback_route = self._create_fallback_route_info(state)
                state['route_data'] = fallback_route
                
                self.add_message_to_state(
                    state,
                    f"Basic route information available for {state['origin']} to {state['destination']}"
                )
                
                self.log_action("Used fallback route information")
                
        except Exception as e:
            error_msg = f"Failed to get route information: {str(e)}"
            self.add_error_to_state(state, error_msg)
            
            # Even with errors, try to provide basic route info
            try:
                fallback_route = self._create_fallback_route_info(state)
                state['route_data'] = fallback_route
            except:
                pass  # If even fallback fails, continue without route data
                
        finally:
            state['maps_complete'] = True
            
        return state
    
    def _create_fallback_route_info(self, state: TravelState) -> RouteInfo:
        """Create basic route information when API calls fail"""
        return RouteInfo(
            distance="Distance calculation unavailable",
            duration="Duration estimation unavailable",
            steps=[f"Travel from {state['origin']} to {state['destination']}"],
            traffic_info=None,
            transport_mode=state.get('preferred_transport', 'driving')
        )
    
    async def _get_alternative_routes(self, state: TravelState) -> Dict[str, Optional[RouteInfo]]:
        """Get alternative transportation routes"""
        self.log_action("Fetching alternative transportation options")
        
        try:
            # Get routes for walking and cycling as alternatives
            tasks = [
                self.maps_service.get_route_between_locations(
                    state['origin'], state['destination'], "walking"
                ),
                self.maps_service.get_route_between_locations(
                    state['origin'], state['destination'], "cycling"
                )
            ]
            
            walking_route, cycling_route = await asyncio.gather(*tasks, return_exceptions=True)
            
            alternatives = {}
            
            if not isinstance(walking_route, Exception) and walking_route:
                alternatives["walking"] = walking_route
            
            if not isinstance(cycling_route, Exception) and cycling_route:
                alternatives["cycling"] = cycling_route
            
            return alternatives
            
        except Exception as e:
            self.log_error("Failed to get alternative routes", str(e))
            return {}
    
    async def _generate_route_insights(
        self, 
        primary_route: RouteInfo,
        alternative_routes: Dict[str, Optional[RouteInfo]], 
        state: TravelState
    ) -> str:
        """Generate route insights using the LLM"""
        
        # Format route data for the LLM
        route_summary = self._format_routes_for_llm(primary_route, alternative_routes)
        location_context = self.format_location_context(state)
        
        user_input = f"""
        {location_context}
        
        Route Analysis:
        {route_summary}
        
        Please provide a concise route recommendation and travel analysis for this journey.
        Consider factors like convenience, time efficiency, and practical considerations.
        """
        
        try:
            insights = await self.invoke_llm(self.get_system_prompt(), user_input)
            return insights
        except Exception as e:
            self.log_error("Failed to generate route insights", str(e))
            return f"Primary route: {primary_route.distance} in {primary_route.duration} by {primary_route.transport_mode}"
    
    def _format_routes_for_llm(
        self, 
        primary_route: RouteInfo, 
        alternative_routes: Dict[str, Optional[RouteInfo]]
    ) -> str:
        """Format route data for LLM consumption"""
        
        formatted_data = [f"""
        PRIMARY ROUTE (Driving):
        Distance: {primary_route.distance}
        Duration: {primary_route.duration}
        Transport: {primary_route.transport_mode}
        Key Steps: {'; '.join(primary_route.steps[:3])}
        """]
        
        for mode, route in alternative_routes.items():
            if route:
                formatted_data.append(f"""
        ALTERNATIVE ({mode.upper()}):
        Distance: {route.distance}
        Duration: {route.duration}
        Transport: {route.transport_mode}
                """)
        
        return "\n".join(formatted_data)
    
    def should_process(self, state: TravelState) -> bool:
        """Check if maps processing is needed"""
        return not state.get('maps_complete', False)
    
    async def get_quick_route_info(self, origin: str, destination: str) -> Optional[str]:
        """Get quick route information for API responses"""
        try:
            route = await self.maps_service.get_route_between_locations(
                origin, destination, "driving"
            )
            
            if route:
                return f"{route.distance} journey taking approximately {route.duration} by car"
            else:
                return "Route information unavailable"
                
        except Exception as e:
            self.log_error("Failed to get quick route info", str(e))
            return "Route calculation failed"
    
    def format_route_summary(self, route: RouteInfo) -> str:
        """Format route information for display"""
        if not route:
            return "No route information available"
        
        summary_parts = [
            f"Distance: {route.distance}",
            f"Duration: {route.duration}",
            f"Mode: {route.transport_mode.title()}"
        ]
        
        if route.traffic_info:
            summary_parts.append(f"Traffic: {route.traffic_info}")
        
        return " | ".join(summary_parts)
    
    async def compare_transport_modes(
        self, 
        origin: str, 
        destination: str
    ) -> Dict[str, Dict[str, str]]:
        """Compare different transportation modes for a journey"""
        try:
            routes = await self.maps_service.get_multiple_route_options(origin, destination)
            
            comparison = {}
            for mode, route in routes.items():
                if route:
                    comparison[mode] = {
                        "distance": route.distance,
                        "duration": route.duration,
                        "summary": self.format_route_summary(route)
                    }
                else:
                    comparison[mode] = {
                        "distance": "N/A",
                        "duration": "N/A", 
                        "summary": "Route unavailable"
                    }
            
            return comparison
            
        except Exception as e:
            self.log_error("Failed to compare transport modes", str(e))
            return {}