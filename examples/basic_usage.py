"""Basic usage examples for the Hybrid Memory Integration API."""

import httpx
import asyncio
import json
from typing import Dict, Any


BASE_URL = "http://localhost:8000"


async def example_multi_source_query():
    """Example: Query multiple sources."""
    print("\n=== Multi-Source Query Example ===")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/v1/query",
            json={
                "query": "Find user information",
                "sources": ["supabase", "notion"],
                "require_verification": True,
                "confidence_threshold": 0.85,
                "additional_context": {
                    "user_id": "123"
                }
            }
        )
        
        print(f"Status: {response.status_code}")
        result = response.json()
        print(json.dumps(result, indent=2))
        
        # Check if we should use "I don't know" response
        if not result['meets_threshold']:
            print("\n⚠️ Confidence below threshold - should respond 'I don't know'")
        else:
            print(f"\n✓ Confidence {result['aggregated_confidence']} meets threshold")


async def example_supabase_query():
    """Example: Query Supabase directly."""
    print("\n=== Supabase Direct Query Example ===")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/v1/query/supabase",
            json={
                "table": "users",
                "filters": {"email": "test@example.com"}
            }
        )
        
        print(f"Status: {response.status_code}")
        results = response.json()
        
        for idx, result in enumerate(results, 1):
            print(f"\nResult {idx}:")
            print(f"  Source ID: {result['source_metadata']['source_id']}")
            print(f"  Confidence: {result['confidence']['score']}")
            print(f"  Reasoning: {result['confidence']['reasoning']}")
            print(f"  Data Found: {not result['information_not_found']}")


async def example_notion_query():
    """Example: Query Notion directly."""
    print("\n=== Notion Direct Query Example ===")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/v1/query/notion",
            json={
                "filters": {"Name": "Project Alpha"}
            }
        )
        
        print(f"Status: {response.status_code}")
        results = response.json()
        
        for idx, result in enumerate(results, 1):
            print(f"\nResult {idx}:")
            print(f"  Source ID: {result['source_metadata']['source_id']}")
            print(f"  Confidence: {result['confidence']['score']}")
            print(f"  Data: {result['data']}")


async def example_llm_prompt_generation():
    """Example: Generate anti-hallucination LLM prompt."""
    print("\n=== LLM Prompt Generation Example ===")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/v1/prompt/generate",
            json={
                "query": "What are the details of Project Alpha?",
                "sources": ["supabase", "notion"],
                "confidence_threshold": 0.85
            }
        )
        
        print(f"Status: {response.status_code}")
        result = response.json()
        
        print(f"\nShould use 'I don't know': {result['should_use_dont_know']}")
        print(f"Aggregated confidence: {result['aggregated_confidence']}")
        
        if result['should_use_dont_know']:
            print(f"\nDon't Know Response:\n{result['dont_know_response']}")
        else:
            print(f"\nSystem Prompt (first 200 chars):")
            print(result['prompt']['system_prompt'][:200] + "...")
            print(f"\nUser Prompt (first 200 chars):")
            print(result['prompt']['user_prompt'][:200] + "...")


async def example_webhook_supabase():
    """Example: Send webhook for Supabase event."""
    print("\n=== Supabase Webhook Example ===")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/v1/webhooks/supabase",
            json={
                "event_type": "insert",
                "source": "supabase",
                "table_name": "users",
                "record_id": "uuid-123",
                "data": {
                    "id": "uuid-123",
                    "name": "John Doe",
                    "email": "john@example.com"
                },
                "timestamp": "2026-01-01T15:09:00Z"
            }
        )
        
        print(f"Status: {response.status_code}")
        result = response.json()
        print(json.dumps(result, indent=2))


async def example_webhook_notion():
    """Example: Send webhook for Notion event."""
    print("\n=== Notion Webhook Example ===")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/v1/webhooks/notion",
            json={
                "event_type": "update",
                "source": "notion",
                "table_name": "database-id",
                "record_id": "page-id-456",
                "data": {
                    "Name": "Updated Project Name",
                    "Status": "In Progress"
                },
                "timestamp": "2026-01-01T15:09:00Z"
            }
        )
        
        print(f"Status: {response.status_code}")
        result = response.json()
        print(json.dumps(result, indent=2))


async def example_health_check():
    """Example: Check API health."""
    print("\n=== Health Check Example ===")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/health")
        
        print(f"Status: {response.status_code}")
        result = response.json()
        print(json.dumps(result, indent=2))


async def main():
    """Run all examples."""
    print("\n" + "="*60)
    print("Hybrid Memory Integration API - Usage Examples")
    print("="*60)
    
    # Check if API is running
    try:
        await example_health_check()
    except Exception as e:
        print(f"\n❌ Error: Cannot connect to API at {BASE_URL}")
        print(f"   Make sure the API is running: python main.py")
        print(f"   Error details: {str(e)}")
        return
    
    # Run examples
    try:
        await example_multi_source_query()
        await example_supabase_query()
        await example_notion_query()
        await example_llm_prompt_generation()
        await example_webhook_supabase()
        await example_webhook_notion()
    except Exception as e:
        print(f"\n❌ Error running examples: {str(e)}")
    
    print("\n" + "="*60)
    print("Examples completed!")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())