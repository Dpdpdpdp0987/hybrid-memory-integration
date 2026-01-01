from typing import List, Dict, Any, Optional
from models import DataResponse, MultiSourceResponse, ConfidenceScore
from config import settings
import hashlib
import json


class DataValidator:
    """Validates data integrity and confidence thresholds."""
    
    def __init__(self, confidence_threshold: Optional[float] = None):
        self.confidence_threshold = confidence_threshold or settings.confidence_threshold
    
    def validate_response(self, response: DataResponse) -> tuple[bool, List[str]]:
        """Validate a single data response.
        
        Returns:
            tuple: (is_valid, list_of_issues)
        """
        issues = []
        
        # Check if verified
        if not response.verified:
            issues.append("Data has not been verified against source")
        
        # Check confidence threshold
        if response.confidence.score < self.confidence_threshold:
            issues.append(
                f"Confidence score {response.confidence.score:.3f} below threshold {self.confidence_threshold}"
            )
        
        # Check if information was found
        if response.information_not_found:
            issues.append("Information not found in source")
        
        # Validate source metadata
        if response.source_metadata.source_id in ["none", "error", "unknown"]:
            issues.append(f"Invalid source ID: {response.source_metadata.source_id}")
        
        # Verify data is not None when info should be found
        if not response.information_not_found and response.data is None:
            issues.append("Data is None but information_not_found is False")
        
        return len(issues) == 0, issues
    
    def validate_multi_source(self, response: MultiSourceResponse) -> tuple[bool, List[str]]:
        """Validate a multi-source response.
        
        Returns:
            tuple: (is_valid, list_of_issues)
        """
        issues = []
        
        # Validate each source
        for idx, source_response in enumerate(response.sources):
            is_valid, source_issues = self.validate_response(source_response)
            if not is_valid:
                issues.append(f"Source {idx} ({source_response.source_metadata.source_type}): " + "; ".join(source_issues))
        
        # Check aggregated confidence
        if response.aggregated_confidence < self.confidence_threshold:
            issues.append(
                f"Aggregated confidence {response.aggregated_confidence:.3f} below threshold {self.confidence_threshold}"
            )
        
        # Verify meets_threshold flag is correct
        if response.meets_threshold and response.aggregated_confidence < self.confidence_threshold:
            issues.append("meets_threshold is True but aggregated confidence is below threshold")
        
        return len(issues) == 0, issues
    
    def verify_data_hash(self, data: Any, expected_hash: str) -> bool:
        """Verify data integrity using hash."""
        data_str = json.dumps(data, sort_keys=True, default=str)
        actual_hash = hashlib.sha256(data_str.encode()).hexdigest()
        return actual_hash == expected_hash
    
    def calculate_aggregated_confidence(self, responses: List[DataResponse]) -> float:
        """Calculate aggregated confidence from multiple sources."""
        if not responses:
            return 0.0
        
        # Filter out responses with no data found
        valid_responses = [r for r in responses if not r.information_not_found]
        
        if not valid_responses:
            return 0.0
        
        # Weighted average based on source reliability
        weights = {
            'supabase': 0.55,
            'notion': 0.45
        }
        
        total_score = 0.0
        total_weight = 0.0
        
        for response in valid_responses:
            source_type = response.source_metadata.source_type.value
            weight = weights.get(source_type, 0.5)
            total_score += response.confidence.score * weight
            total_weight += weight
        
        return round(total_score / total_weight if total_weight > 0 else 0.0, 3)
    
    def should_return_dont_know(self, response: MultiSourceResponse) -> bool:
        """Determine if response should be 'I don't know' based on validation."""
        # If information not found in all sources
        if all(r.information_not_found for r in response.sources):
            return True
        
        # If confidence is below threshold
        if response.aggregated_confidence < self.confidence_threshold:
            return True
        
        # If no sources are verified
        if not any(r.verified for r in response.sources):
            return True
        
        return False
    
    def enforce_confidence_threshold(self, responses: List[DataResponse]) -> List[DataResponse]:
        """Filter responses to only include those meeting confidence threshold."""
        return [
            r for r in responses 
            if r.confidence.score >= self.confidence_threshold and not r.information_not_found
        ]