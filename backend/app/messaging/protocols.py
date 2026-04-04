from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List, Literal
from datetime import datetime
from enum import Enum
import uuid


class MessageAction(str, Enum):
    """MCP message action types"""
    REQUEST = "request"
    RESPONSE = "response"
    ERROR = "error"
    CANCEL = "cancel"
    HEALTH_CHECK = "health_check"
    STREAMING_UPDATE = "streaming_update"


class MessagePriority(str, Enum):
    """Message priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class AgentType(str, Enum):
    """Agent type identifiers"""
    WEATHER = "weather"
    EVENTS = "events"
    MAPS = "maps"
    BUDGET = "budget"
    ITINERARY = "itinerary"
    ORCHESTRATOR = "orchestrator"


# ==================== BASE MESSAGE PROTOCOL ====================

class MCPMessage(BaseModel):
    """Base MCP (Model-Context-Protocol) Message"""
    
    session_id: str = Field(..., description="Unique session identifier")
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique request identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Message timestamp")
    agent: AgentType = Field(..., description="Source/target agent")
    action: MessageAction = Field(..., description="Message action type")
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class MessageMetadata(BaseModel):
    """Metadata for message handling"""
    retry_count: int = Field(default=0, ge=0, le=5)
    timeout_ms: int = Field(default=30000, gt=0)
    priority: MessagePriority = MessagePriority.NORMAL
    correlation_id: Optional[str] = None  # For linking related messages
    parent_request_id: Optional[str] = None  # For tracking message chains


# ==================== REQUEST MESSAGES ====================

class WeatherRequest(MCPMessage):
    """Weather agent request message"""
    action: Literal[MessageAction.REQUEST] = MessageAction.REQUEST
    agent: Literal[AgentType.WEATHER] = AgentType.WEATHER
    
    payload: Dict[str, Any] = Field(..., description="Request payload")
    metadata: MessageMetadata = Field(default_factory=MessageMetadata)
    
    @field_validator('payload')
    def validate_weather_payload(cls, v):
        required = ['destination', 'travel_dates']
        for field in required:
            if field not in v:
                raise ValueError(f"Missing required field: {field}")
        return v


class EventsRequest(MCPMessage):
    """Events agent request message"""
    action: Literal[MessageAction.REQUEST] = MessageAction.REQUEST
    agent: Literal[AgentType.EVENTS] = AgentType.EVENTS
    
    payload: Dict[str, Any] = Field(..., description="Request payload")
    metadata: MessageMetadata = Field(default_factory=MessageMetadata)
    
    @field_validator('payload')
    def validate_events_payload(cls, v):
        required = ['destination', 'travel_dates']
        for field in required:
            if field not in v:
                raise ValueError(f"Missing required field: {field}")
        return v


class MapsRequest(MCPMessage):
    """Maps agent request message"""
    action: Literal[MessageAction.REQUEST] = MessageAction.REQUEST
    agent: Literal[AgentType.MAPS] = AgentType.MAPS
    
    payload: Dict[str, Any] = Field(..., description="Request payload")
    metadata: MessageMetadata = Field(default_factory=MessageMetadata)
    
    @field_validator('payload')
    def validate_maps_payload(cls, v):
        required = ['origin', 'destination']
        for field in required:
            if field not in v:
                raise ValueError(f"Missing required field: {field}")
        return v


class BudgetRequest(MCPMessage):
    """Budget agent request message"""
    action: Literal[MessageAction.REQUEST] = MessageAction.REQUEST
    agent: Literal[AgentType.BUDGET] = AgentType.BUDGET
    
    payload: Dict[str, Any] = Field(..., description="Request payload")
    metadata: MessageMetadata = Field(default_factory=MessageMetadata)
    
    @field_validator('payload')
    def validate_budget_payload(cls, v):
        required = ['destination', 'travel_dates', 'travelers_count']
        for field in required:
            if field not in v:
                raise ValueError(f"Missing required field: {field}")
        return v


class ItineraryRequest(MCPMessage):
    """Itinerary agent request message"""
    action: Literal[MessageAction.REQUEST] = MessageAction.REQUEST
    agent: Literal[AgentType.ITINERARY] = AgentType.ITINERARY
    
    payload: Dict[str, Any] = Field(..., description="Complete travel state")
    metadata: MessageMetadata = Field(default_factory=MessageMetadata)


# ==================== RESPONSE MESSAGES ====================

class AgentResponse(MCPMessage):
    """Base agent response message"""
    action: Literal[MessageAction.RESPONSE] = MessageAction.RESPONSE
    
    success: bool = Field(..., description="Whether request was successful")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")
    error: Optional[str] = Field(None, description="Error message if failed")
    processing_time_ms: Optional[int] = Field(None, description="Processing duration")
    metadata: MessageMetadata = Field(default_factory=MessageMetadata)


class WeatherResponse(AgentResponse):
    """Weather agent response"""
    agent: Literal[AgentType.WEATHER] = AgentType.WEATHER


class EventsResponse(AgentResponse):
    """Events agent response"""
    agent: Literal[AgentType.EVENTS] = AgentType.EVENTS


class MapsResponse(AgentResponse):
    """Maps agent response"""
    agent: Literal[AgentType.MAPS] = AgentType.MAPS


class BudgetResponse(AgentResponse):
    """Budget agent response"""
    agent: Literal[AgentType.BUDGET] = AgentType.BUDGET


class ItineraryResponse(AgentResponse):
    """Itinerary agent response"""
    agent: Literal[AgentType.ITINERARY] = AgentType.ITINERARY


# ==================== ERROR MESSAGES ====================

class ErrorMessage(MCPMessage):
    """Error message format"""
    action: Literal[MessageAction.ERROR] = MessageAction.ERROR
    
    error_code: str = Field(..., description="Error code")
    error_message: str = Field(..., description="Human-readable error message")
    error_details: Optional[Dict[str, Any]] = Field(None, description="Additional error context")
    recoverable: bool = Field(default=True, description="Whether error is recoverable")
    retry_after_ms: Optional[int] = Field(None, description="Suggested retry delay")


# ==================== CONTROL MESSAGES ====================

class CancelMessage(MCPMessage):
    """Cancel operation message"""
    action: Literal[MessageAction.CANCEL] = MessageAction.CANCEL
    
    reason: Optional[str] = Field(None, description="Cancellation reason")


class HealthCheckMessage(MCPMessage):
    """Health check message"""
    action: Literal[MessageAction.HEALTH_CHECK] = MessageAction.HEALTH_CHECK
    
    status: str = Field(..., description="Agent status: healthy, degraded, unhealthy")
    uptime_seconds: Optional[int] = Field(None, description="Agent uptime")
    version: Optional[str] = Field(None, description="Agent version")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional health info")


class StreamingUpdate(MCPMessage):
    """Real-time streaming update message"""
    action: Literal[MessageAction.STREAMING_UPDATE] = MessageAction.STREAMING_UPDATE
    
    update_type: str = Field(..., description="Type of update: progress, status, data")
    message: str = Field(..., description="Human-readable update message")
    progress_percent: Optional[int] = Field(None, ge=0, le=100, description="Progress percentage")
    data: Optional[Dict[str, Any]] = Field(None, description="Update data payload")


# ==================== MESSAGE FACTORIES ====================

class MessageFactory:
    """Factory for creating MCP messages"""
    
    @staticmethod
    def create_weather_request(
        session_id: str,
        destination: str,
        travel_dates: List[str],
        timeout_ms: int = 10000
    ) -> WeatherRequest:
        """Create weather request message"""
        return WeatherRequest(
            session_id=session_id,
            agent=AgentType.WEATHER,
            action=MessageAction.REQUEST,
            payload={
                "destination": destination,
                "travel_dates": travel_dates
            },
            metadata=MessageMetadata(timeout_ms=timeout_ms)
        )
    
    @staticmethod
    def create_events_request(
        session_id: str,
        destination: str,
        travel_dates: List[str],
        interests: Optional[List[str]] = None,
        timeout_ms: int = 15000
    ) -> EventsRequest:
        """Create events request message"""
        payload = {
            "destination": destination,
            "travel_dates": travel_dates
        }
        if interests:
            payload["interests"] = interests
            
        return EventsRequest(
            session_id=session_id,
            agent=AgentType.EVENTS,
            action=MessageAction.REQUEST,
            payload=payload,
            metadata=MessageMetadata(timeout_ms=timeout_ms)
        )
    
    @staticmethod
    def create_maps_request(
        session_id: str,
        origin: str,
        destination: str,
        transport_mode: str = "driving",
        timeout_ms: int = 12000
    ) -> MapsRequest:
        """Create maps request message"""
        return MapsRequest(
            session_id=session_id,
            agent=AgentType.MAPS,
            action=MessageAction.REQUEST,
            payload={
                "origin": origin,
                "destination": destination,
                "transport_mode": transport_mode
            },
            metadata=MessageMetadata(timeout_ms=timeout_ms)
        )
    
    @staticmethod
    def create_budget_request(
        session_id: str,
        destination: str,
        travel_dates: List[str],
        travelers_count: int,
        budget_range: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None,
        timeout_ms: int = 8000
    ) -> BudgetRequest:
        """Create budget request message"""
        payload = {
            "destination": destination,
            "travel_dates": travel_dates,
            "travelers_count": travelers_count
        }
        if budget_range:
            payload["budget_range"] = budget_range
        if additional_data:
            payload.update(additional_data)
            
        return BudgetRequest(
            session_id=session_id,
            agent=AgentType.BUDGET,
            action=MessageAction.REQUEST,
            payload=payload,
            metadata=MessageMetadata(timeout_ms=timeout_ms)
        )
    
    @staticmethod
    def create_itinerary_request(
        session_id: str,
        travel_state: Dict[str, Any],
        timeout_ms: int = 20000
    ) -> ItineraryRequest:
        """Create itinerary request message"""
        return ItineraryRequest(
            session_id=session_id,
            agent=AgentType.ITINERARY,
            action=MessageAction.REQUEST,
            payload=travel_state,
            metadata=MessageMetadata(timeout_ms=timeout_ms)
        )
    
    @staticmethod
    def create_response(
        request: MCPMessage,
        agent: AgentType,
        success: bool,
        data: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        processing_time_ms: Optional[int] = None
    ) -> AgentResponse:
        """Create generic response message"""
        response_classes = {
            AgentType.WEATHER: WeatherResponse,
            AgentType.EVENTS: EventsResponse,
            AgentType.MAPS: MapsResponse,
            AgentType.BUDGET: BudgetResponse,
            AgentType.ITINERARY: ItineraryResponse
        }
        
        response_class = response_classes.get(agent, AgentResponse)
        
        return response_class(
            session_id=request.session_id,
            request_id=request.request_id,
            timestamp=datetime.utcnow().isoformat(),
            agent=agent,
            action=MessageAction.RESPONSE,
            success=success,
            data=data,
            error=error,
            processing_time_ms=processing_time_ms,
            metadata=request.metadata if hasattr(request, 'metadata') else MessageMetadata()
        )
    
    @staticmethod
    def create_error(
        request: MCPMessage,
        error_code: str,
        error_message: str,
        error_details: Optional[Dict[str, Any]] = None,
        recoverable: bool = True,
        retry_after_ms: Optional[int] = None
    ) -> ErrorMessage:
        """Create error message"""
        return ErrorMessage(
            session_id=request.session_id,
            request_id=request.request_id,
            timestamp=datetime.utcnow().isoformat(),
            agent=request.agent,
            action=MessageAction.ERROR,
            error_code=error_code,
            error_message=error_message,
            error_details=error_details,
            recoverable=recoverable,
            retry_after_ms=retry_after_ms
        )
    
    @staticmethod
    def create_streaming_update(
        session_id: str,
        agent: AgentType,
        update_type: str,
        message: str,
        progress_percent: Optional[int] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> StreamingUpdate:
        """Create streaming update message"""
        return StreamingUpdate(
            session_id=session_id,
            request_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow().isoformat(),
            agent=agent,
            action=MessageAction.STREAMING_UPDATE,
            update_type=update_type,
            message=message,
            progress_percent=progress_percent,
            data=data
        )
    
    @staticmethod
    def create_cancel(
        session_id: str,
        agent: AgentType,
        reason: Optional[str] = None
    ) -> CancelMessage:
        """Create cancel message"""
        return CancelMessage(
            session_id=session_id,
            request_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            agent=agent,
            action=MessageAction.CANCEL,
            reason=reason
        )
    
    @staticmethod
    def create_health_check(
        agent: AgentType,
        status: str = "healthy",
        uptime_seconds: Optional[int] = None,
        version: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> HealthCheckMessage:
        """Create health check message"""
        return HealthCheckMessage(
            session_id="health",
            request_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow().isoformat(),
            agent=agent,
            action=MessageAction.HEALTH_CHECK,
            status=status,
            uptime_seconds=uptime_seconds,
            version=version,
            metadata=metadata
        )


# ==================== MESSAGE VALIDATION ====================

class MessageValidator:
    """Validate MCP messages"""
    
    @staticmethod
    def validate_request(message: MCPMessage) -> tuple[bool, Optional[str]]:
        """
        Validate request message
        
        Returns:
            (is_valid, error_message)
        """
        try:
            # Check required fields
            if not message.session_id:
                return False, "Missing session_id"
            
            if not message.request_id:
                return False, "Missing request_id"
            
            # Check timestamp not too old (> 5 minutes)
            age_seconds = (datetime.utcnow().isoformat() - message.timestamp).total_seconds()
            if age_seconds > 300:
                return False, f"Message too old: {age_seconds}s"
            
            # Validate metadata
            if hasattr(message, 'metadata'):
                if message.metadata.retry_count > 5:
                    return False, "Too many retries"
                
                if message.metadata.timeout_ms < 1000:
                    return False, "Timeout too short"
            
            return True, None
            
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    @staticmethod
    def validate_response(response: AgentResponse, request: MCPMessage) -> tuple[bool, Optional[str]]:
        """
        Validate response message matches request
        
        Returns:
            (is_valid, error_message)
        """
        if response.session_id != request.session_id:
            return False, "Session ID mismatch"
        
        if response.request_id != request.request_id:
            return False, "Request ID mismatch"
        
        if not response.success and not response.error:
            return False, "Failed response must include error message"
        
        return True, None


# ==================== SERIALIZATION HELPERS ====================

def serialize_message(message: MCPMessage) -> str:
    """Serialize MCP message to JSON string"""
    return message.json()


def deserialize_message(json_str: str, expected_type: type[MCPMessage]) -> MCPMessage:
    """Deserialize JSON string to MCP message"""
    return expected_type.parse_raw(json_str)


def message_to_dict(message: MCPMessage) -> Dict[str, Any]:
    """Convert MCP message to dictionary"""
    return message.dict()


def dict_to_message(data: Dict[str, Any], message_type: type[MCPMessage]) -> MCPMessage:
    """Convert dictionary to MCP message"""
    return message_type(**data)