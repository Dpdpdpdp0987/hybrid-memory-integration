from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
from enum import Enum


class SourceType(str, Enum):
    """Enumeration of supported data sources."""
    SUPABASE = "supabase"
    NOTION = "notion"
    UNKNOWN = "unknown"


class SourceMetadata(BaseModel):
    """Metadata about the data source."""
    source_type: SourceType
    source_id: str = Field(..., description="Unique identifier from the source database")
    table_name: Optional[str] = Field(None, description="Table/Database name")
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)
    query_params: Optional[Dict[str, Any]] = Field(default=None)
    raw_data_hash: Optional[str] = Field(None, description="Hash of raw data for verification")


class ConfidenceScore(BaseModel):
    """Confidence score with reasoning."""
    score: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    reasoning: str = Field(..., description="Explanation for the confidence score")
    factors: Dict[str, float] = Field(default_factory=dict, description="Individual confidence factors")
    
    @validator('score')
    def validate_score(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError('Confidence score must be between 0.0 and 1.0')
        return round(v, 3)


class DataResponse(BaseModel):
    """Standardized response format with source tracking and confidence."""
    data: Any = Field(..., description="The actual data retrieved")
    source_metadata: SourceMetadata
    confidence: ConfidenceScore
    information_not_found: bool = Field(default=False)
    verified: bool = Field(default=False, description="Whether data has been verified against source")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    additional_context: Optional[str] = Field(None)


class MultiSourceResponse(BaseModel):
    """Response containing data from multiple sources."""
    query: str
    sources: List[DataResponse]
    aggregated_confidence: float = Field(..., ge=0.0, le=1.0)
    meets_threshold: bool
    information_not_found: bool = Field(default=False)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('aggregated_confidence')
    def validate_confidence(cls, v):
        return round(v, 3)


class QueryRequest(BaseModel):
    """Request model for querying data."""
    query: str = Field(..., min_length=1)
    sources: List[SourceType] = Field(default=[SourceType.SUPABASE, SourceType.NOTION])
    require_verification: bool = Field(default=True)
    confidence_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    additional_context: Optional[Dict[str, Any]] = None


class WebhookPayload(BaseModel):
    """Webhook payload for real-time data updates."""
    event_type: Literal["insert", "update", "delete"]
    source: SourceType
    table_name: str
    record_id: str
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = None


class LLMPromptTemplate(BaseModel):
    """Template for LLM prompts with anti-hallucination mechanisms."""
    system_prompt: str
    user_prompt: str
    retrieved_data: List[DataResponse]
    strict_mode: bool = Field(default=True, description="Enforce strict 'I don't know' policy")
    confidence_threshold: float = Field(default=0.85)