from supabase import create_client, Client
from notion_client import Client as NotionClient
from typing import List, Dict, Any, Optional
import hashlib
import json
from datetime import datetime

from config import settings
from models import (
    SourceMetadata, 
    SourceType, 
    ConfidenceScore, 
    DataResponse
)


class SupabaseClient:
    """Wrapper for Supabase client with source tracking."""
    
    def __init__(self):
        self.client: Client = create_client(
            settings.supabase_url,
            settings.supabase_key
        )
    
    def _calculate_data_hash(self, data: Any) -> str:
        """Calculate hash of data for verification."""
        data_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(data_str.encode()).hexdigest()
    
    async def query(self, table: str, filters: Optional[Dict[str, Any]] = None) -> List[DataResponse]:
        """Query Supabase table with source tracking."""
        try:
            query = self.client.table(table).select("*")
            
            if filters:
                for key, value in filters.items():
                    query = query.eq(key, value)
            
            response = query.execute()
            
            if not response.data:
                return [self._create_empty_response(table, filters)]
            
            results = []
            for item in response.data:
                # Extract ID (trying common field names)
                source_id = str(item.get('id') or item.get('uuid') or item.get('_id') or 'unknown')
                
                confidence = self._calculate_confidence(item, filters)
                
                metadata = SourceMetadata(
                    source_type=SourceType.SUPABASE,
                    source_id=source_id,
                    table_name=table,
                    query_params=filters,
                    raw_data_hash=self._calculate_data_hash(item)
                )
                
                results.append(DataResponse(
                    data=item,
                    source_metadata=metadata,
                    confidence=confidence,
                    verified=True,
                    information_not_found=False
                ))
            
            return results
            
        except Exception as e:
            print(f"Supabase query error: {str(e)}")
            return [self._create_error_response(table, filters, str(e))]
    
    def _calculate_confidence(self, data: Dict[str, Any], filters: Optional[Dict[str, Any]]) -> ConfidenceScore:
        """Calculate confidence score based on data completeness and match quality."""
        factors = {}
        
        # Data completeness factor
        non_null_fields = sum(1 for v in data.values() if v is not None)
        total_fields = len(data)
        factors['completeness'] = non_null_fields / total_fields if total_fields > 0 else 0.0
        
        # Filter match factor
        if filters:
            matches = sum(1 for k, v in filters.items() if data.get(k) == v)
            factors['filter_match'] = matches / len(filters)
        else:
            factors['filter_match'] = 1.0
        
        # Source reliability (Supabase is highly reliable)
        factors['source_reliability'] = 0.95
        
        # Calculate weighted average
        score = (
            factors['completeness'] * 0.3 +
            factors['filter_match'] * 0.4 +
            factors['source_reliability'] * 0.3
        )
        
        return ConfidenceScore(
            score=score,
            reasoning=f"Data from verified Supabase source with {factors['completeness']:.1%} completeness",
            factors=factors
        )
    
    def _create_empty_response(self, table: str, filters: Optional[Dict[str, Any]]) -> DataResponse:
        """Create response for no data found."""
        metadata = SourceMetadata(
            source_type=SourceType.SUPABASE,
            source_id="none",
            table_name=table,
            query_params=filters
        )
        
        confidence = ConfidenceScore(
            score=0.0,
            reasoning="No data found in Supabase",
            factors={'data_found': 0.0}
        )
        
        return DataResponse(
            data=None,
            source_metadata=metadata,
            confidence=confidence,
            information_not_found=True,
            verified=True
        )
    
    def _create_error_response(self, table: str, filters: Optional[Dict[str, Any]], error: str) -> DataResponse:
        """Create response for query errors."""
        metadata = SourceMetadata(
            source_type=SourceType.SUPABASE,
            source_id="error",
            table_name=table,
            query_params=filters
        )
        
        confidence = ConfidenceScore(
            score=0.0,
            reasoning=f"Query error: {error}",
            factors={'error': 1.0}
        )
        
        return DataResponse(
            data=None,
            source_metadata=metadata,
            confidence=confidence,
            information_not_found=True,
            verified=False,
            additional_context=error
        )


class NotionDatabaseClient:
    """Wrapper for Notion client with source tracking."""
    
    def __init__(self):
        self.client = NotionClient(auth=settings.notion_api_key)
        self.database_id = settings.notion_database_id
    
    def _calculate_data_hash(self, data: Any) -> str:
        """Calculate hash of data for verification."""
        data_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(data_str.encode()).hexdigest()
    
    async def query(self, filters: Optional[Dict[str, Any]] = None) -> List[DataResponse]:
        """Query Notion database with source tracking."""
        try:
            # Build Notion filter
            notion_filter = self._build_notion_filter(filters) if filters else None
            
            response = self.client.databases.query(
                database_id=self.database_id,
                filter=notion_filter
            )
            
            if not response.get('results'):
                return [self._create_empty_response(filters)]
            
            results = []
            for page in response['results']:
                page_id = page['id']
                properties = self._extract_properties(page['properties'])
                
                confidence = self._calculate_confidence(properties, filters)
                
                metadata = SourceMetadata(
                    source_type=SourceType.NOTION,
                    source_id=page_id,
                    table_name=self.database_id,
                    query_params=filters,
                    raw_data_hash=self._calculate_data_hash(properties)
                )
                
                results.append(DataResponse(
                    data=properties,
                    source_metadata=metadata,
                    confidence=confidence,
                    verified=True,
                    information_not_found=False
                ))
            
            return results
            
        except Exception as e:
            print(f"Notion query error: {str(e)}")
            return [self._create_error_response(filters, str(e))]
    
    def _build_notion_filter(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Convert simple filters to Notion API filter format."""
        if len(filters) == 1:
            key, value = list(filters.items())[0]
            return {
                "property": key,
                "rich_text": {
                    "contains": str(value)
                }
            }
        else:
            return {
                "and": [
                    {
                        "property": key,
                        "rich_text": {"contains": str(value)}
                    }
                    for key, value in filters.items()
                ]
            }
    
    def _extract_properties(self, properties: Dict[str, Any]) -> Dict[str, Any]:
        """Extract property values from Notion property objects."""
        extracted = {}
        
        for key, prop in properties.items():
            prop_type = prop.get('type')
            
            if prop_type == 'title':
                title_list = prop.get('title', [])
                extracted[key] = title_list[0]['plain_text'] if title_list else None
            elif prop_type == 'rich_text':
                text_list = prop.get('rich_text', [])
                extracted[key] = text_list[0]['plain_text'] if text_list else None
            elif prop_type == 'number':
                extracted[key] = prop.get('number')
            elif prop_type == 'select':
                select = prop.get('select')
                extracted[key] = select['name'] if select else None
            elif prop_type == 'multi_select':
                multi = prop.get('multi_select', [])
                extracted[key] = [item['name'] for item in multi]
            elif prop_type == 'date':
                date = prop.get('date')
                extracted[key] = date['start'] if date else None
            else:
                extracted[key] = prop.get(prop_type)
        
        return extracted
    
    def _calculate_confidence(self, data: Dict[str, Any], filters: Optional[Dict[str, Any]]) -> ConfidenceScore:
        """Calculate confidence score for Notion data."""
        factors = {}
        
        # Data completeness
        non_null_fields = sum(1 for v in data.values() if v is not None and v != '')
        total_fields = len(data)
        factors['completeness'] = non_null_fields / total_fields if total_fields > 0 else 0.0
        
        # Filter match factor
        if filters:
            # Notion filters are more flexible, so we check containment
            matches = 0
            for k, v in filters.items():
                if k in data and data[k] is not None:
                    if str(v).lower() in str(data[k]).lower():
                        matches += 1
            factors['filter_match'] = matches / len(filters)
        else:
            factors['filter_match'] = 1.0
        
        # Source reliability
        factors['source_reliability'] = 0.90  # Notion is reliable but slightly less structured
        
        score = (
            factors['completeness'] * 0.3 +
            factors['filter_match'] * 0.4 +
            factors['source_reliability'] * 0.3
        )
        
        return ConfidenceScore(
            score=score,
            reasoning=f"Data from verified Notion source with {factors['completeness']:.1%} completeness",
            factors=factors
        )
    
    def _create_empty_response(self, filters: Optional[Dict[str, Any]]) -> DataResponse:
        """Create response for no data found."""
        metadata = SourceMetadata(
            source_type=SourceType.NOTION,
            source_id="none",
            table_name=self.database_id,
            query_params=filters
        )
        
        confidence = ConfidenceScore(
            score=0.0,
            reasoning="No data found in Notion database",
            factors={'data_found': 0.0}
        )
        
        return DataResponse(
            data=None,
            source_metadata=metadata,
            confidence=confidence,
            information_not_found=True,
            verified=True
        )
    
    def _create_error_response(self, filters: Optional[Dict[str, Any]], error: str) -> DataResponse:
        """Create response for query errors."""
        metadata = SourceMetadata(
            source_type=SourceType.NOTION,
            source_id="error",
            table_name=self.database_id,
            query_params=filters
        )
        
        confidence = ConfidenceScore(
            score=0.0,
            reasoning=f"Query error: {error}",
            factors={'error': 1.0}
        )
        
        return DataResponse(
            data=None,
            source_metadata=metadata,
            confidence=confidence,
            information_not_found=True,
            verified=False,
            additional_context=error
        )