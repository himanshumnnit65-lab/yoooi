from typing import Dict, List, Optional, Any
from app.agents.base_agent import BaseAgent
from app.core.state import TravelState, BudgetBreakdown
from app.services.budget_service import BudgetService
import json
import re
import logging

logger = logging.getLogger(__name__)

class EnhancedBudgetAgent(BaseAgent):
    """Enhanced Quartermaster with structured data extraction"""
    
    def __init__(self):
        super().__init__(
            name="Quartermaster",
            role="Budget Planner & Financial Advisor", 
            expertise="Cost estimation, budget optimization, and financial planning for travel"
        )
        self.budget_service = BudgetService()
    
    def get_system_prompt(self) -> str:
        return """
        You are the Quartermaster, a budget planning and financial expert for travel. Your role is to:
        
        1. Analyze travel costs across all categories (transport, accommodation, food, activities)
        2. Provide practical budget recommendations based on traveler preferences
        3. Suggest cost-saving opportunities and alternatives
        4. Warn about potential hidden costs or budget overruns
        5. Recommend budget allocation strategies
        
        IMPORTANT: At the end of your response, provide a JSON block with structured budget data:
        ```json
        {
            "revised_budget": {
                "total": number,
                "transportation": number,
                "accommodation": number,
                "food": number,
                "activities": number,
                "contingency": number
            },
            "recommended_transport": {
                "mode": "string",
                "details": "string",
                "estimated_cost": number
            },
            "key_recommendations": [
                "recommendation 1",
                "recommendation 2"
            ],
            "cost_per_person": number,
            "recommended_duration": number
        }
        ```
        
        Always provide practical, money-conscious advice in Indian Rupees (INR).
        """
    
    async def process(self, state: TravelState) -> TravelState:
        """Enhanced processing with structured data extraction"""
        self.log_action("Starting enhanced budget analysis", f"Budget category: {state.get('budget_range', 'mid-range')}")
        
        try:
            # Get initial budget from service
            budget_category = state.get('budget_range', 'mid-range').lower()
            if budget_category not in ['budget', 'mid-range', 'luxury']:
                budget_category = 'mid-range'
            
            initial_budget = self.budget_service.create_budget_breakdown(
                route_info=state.get('route_data'),
                travel_dates=state['travel_dates'],
                travelers_count=state['travelers_count'],
                budget_category=budget_category
            )
            
            # Generate enhanced insights with structured data
            budget_analysis = await self._generate_enhanced_budget_insights(initial_budget, state)
            
            # Extract structured data from LLM response
            structured_data = self._extract_structured_budget_data(budget_analysis)
            
            # Update budget with LLM recommendations if available
            if structured_data and 'revised_budget' in structured_data:
                revised = structured_data['revised_budget']
                enhanced_budget = BudgetBreakdown(
                    transportation=revised.get('transportation', initial_budget.transportation),
                    accommodation=revised.get('accommodation', initial_budget.accommodation),
                    food=revised.get('food', initial_budget.food),
                    activities=revised.get('activities', initial_budget.activities),
                    total=revised.get('total', initial_budget.total),
                    currency="INR"
                )
                state['budget_data'] = enhanced_budget
                
                # Store additional structured data
                state['transport_recommendations'] = structured_data.get('recommended_transport', {})
                state['budget_recommendations'] = structured_data.get('key_recommendations', [])
            else:
                state['budget_data'] = initial_budget
            
            self.add_message_to_state(state, budget_analysis)
            self.log_action("Enhanced budget analysis completed successfully")
            
        except Exception as e:
            error_msg = f"Failed to calculate enhanced budget: {str(e)}"
            self.add_error_to_state(state, error_msg)
            logger.error(error_msg)
            
            # Fallback to basic budget
            fallback_budget = self._create_fallback_budget(state)
            state['budget_data'] = fallback_budget
                
        finally:
            state['budget_complete'] = True
            
        return state
    
    async def _generate_enhanced_budget_insights(self, budget_breakdown: BudgetBreakdown, state: TravelState) -> str:
        """Generate enhanced insights with structured data request"""
        
        budget_summary = self._format_budget_for_llm(budget_breakdown)
        location_context = self.format_location_context(state)
        
        user_input = f"""
        {location_context}
        
        Current Budget Analysis:
        {budget_summary}
        
        User's stated budget range: {state.get('budget_range', 'Not specified')}
        
        Please provide:
        1. Analysis of whether this budget is realistic
        2. Specific transport recommendations (train names, booking tips)
        3. Optimized budget breakdown if current one doesn't fit user needs
        4. Practical money-saving tips
        5. Recommended trip duration for budget optimization
        
        Include the structured JSON data at the end of your response.
        """
        
        try:
            insights = await self.invoke_llm(self.get_system_prompt(), user_input)
            return insights
        except Exception as e:
            logger.error(f"Enhanced LLM insights failed: {str(e)}")
            return f"Total estimated cost: ₹{budget_breakdown.total:,.0f} for {state['travelers_count']} travelers"
    
    def _extract_structured_budget_data(self, llm_response: str) -> Optional[Dict[str, Any]]:
        """Extract structured JSON data from LLM response"""
        try:
            # Look for JSON code blocks
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', llm_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                return json.loads(json_str)
            
            # Alternative: look for JSON-like structures
            json_match = re.search(r'\{[^{}]*"revised_budget"[^{}]*\{.*?\}[^{}]*\}', llm_response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
                
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse structured data from LLM response: {e}")
        except Exception as e:
            logger.error(f"Error extracting structured data: {e}")
        
        return None

    def _format_budget_for_llm(self, budget: BudgetBreakdown) -> str:
        """Format budget data for LLM consumption"""
        return f"""
        TOTAL BUDGET: ₹{budget.total:,.0f} {budget.currency}
        
        BREAKDOWN:
        • Transportation: ₹{budget.transportation:,.0f} ({budget.transportation/budget.total*100:.1f}%)
        • Accommodation: ₹{budget.accommodation:,.0f} ({budget.accommodation/budget.total*100:.1f}%)
        • Food & Dining: ₹{budget.food:,.0f} ({budget.food/budget.total*100:.1f}%)
        • Activities & Sightseeing: ₹{budget.activities:,.0f} ({budget.activities/budget.total*100:.1f}%)
        """
    
    def should_process(self, state: TravelState) -> bool:
        """Check if budget processing is needed"""
        return not state.get('budget_complete', False)
    
    def _create_fallback_budget(self, state: TravelState) -> BudgetBreakdown:
        """Create fallback budget when calculation fails"""
        travelers = state['travelers_count']
        days = len(state['travel_dates']) if state['travel_dates'] else 1
        
        # Simple fallback estimates
        transport = 2000 * travelers
        accommodation = 2500 * days
        food = 1000 * days * travelers
        activities = 500 * days * travelers
        
        return BudgetBreakdown(
            transportation=transport,
            accommodation=accommodation,
            food=food,
            activities=activities,
            total=transport + accommodation + food + activities,
            currency="INR"
        )