#!/usr/bin/env python3
"""Test script for webhook endpoints."""

import httpx
import asyncio
import json
from datetime import datetime
from typing import Dict, Any


API_BASE_URL = "http://localhost:8000"


async def test_supabase_webhook():
    """Test Supabase webhook endpoint."""
    print("\n" + "="*60)
    print("Testing Supabase Webhook")
    print("="*60)
    
    payload = {
        "event_type": "insert",
        "source": "supabase",
        "table_name": "test_users",
        "record_id": "test-123",
        "data": {
            "id": "test-123",
            "name": "Test User",
            "email": "test@example.com",
            "created_at": datetime.utcnow().isoformat()
        },
        "timestamp": datetime.utcnow().isoformat()
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{API_BASE_URL}/api/v1/webhooks/supabase",
                json=payload,
                timeout=5.0
            )
            
            print(f"Status Code: {response.status_code}")
            print(f"Response: {json.dumps(response.json(), indent=2)}")
            
            if response.status_code == 202:
                print("✓ Supabase webhook accepted successfully")
            else:
                print("✗ Unexpected status code")
                
        except Exception as e:
            print(f"✗ Error: {e}")


async def test_notion_webhook():
    """Test Notion webhook endpoint."""
    print("\n" + "="*60)
    print("Testing Notion Webhook")
    print("="*60)
    
    payload = {
        "event_type": "update",
        "source": "notion",
        "table_name": "test-database-id",
        "record_id": "test-page-id",
        "data": {
            "properties": {
                "Name": {
                    "type": "title",
                    "title": [{"plain_text": "Test Project"}]
                },
                "Status": {
                    "type": "select",
                    "select": {"name": "Active"}
                }
            }
        },
        "timestamp": datetime.utcnow().isoformat()
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{API_BASE_URL}/api/v1/webhooks/notion",
                json=payload,
                timeout=5.0
            )
            
            print(f"Status Code: {response.status_code}")
            print(f"Response: {json.dumps(response.json(), indent=2)}")
            
            if response.status_code == 202:
                print("✓ Notion webhook accepted successfully")
            else:
                print("✗ Unexpected status code")
                
        except Exception as e:
            print(f"✗ Error: {e}")


async def test_webhook_validation():
    """Test webhook payload validation."""
    print("\n" + "="*60)
    print("Testing Webhook Validation")
    print("="*60)
    
    # Valid payload
    valid_payload = {
        "event_type": "insert",
        "source": "supabase",
        "table_name": "test",
        "record_id": "123",
        "data": {"test": "data"}
    }
    
    # Invalid payload (missing fields)
    invalid_payload = {
        "event_type": "insert",
        "source": "supabase"
    }
    
    async with httpx.AsyncClient() as client:
        # Test valid payload
        print("\n1. Testing valid payload...")
        try:
            response = await client.post(
                f"{API_BASE_URL}/api/v1/webhooks/test",
                json=valid_payload,
                timeout=5.0
            )
            result = response.json()
            print(f"Status: {result.get('status')}")
            print(f"Would be processed: {result.get('would_be_processed')}")
            
            if result.get('status') == 'valid':
                print("✓ Valid payload recognized correctly")
            else:
                print("✗ Validation failed unexpectedly")
        except Exception as e:
            print(f"✗ Error: {e}")
        
        # Test invalid payload
        print("\n2. Testing invalid payload...")
        try:
            response = await client.post(
                f"{API_BASE_URL}/api/v1/webhooks/test",
                json=invalid_payload,
                timeout=5.0
            )
            result = response.json()
            print(f"Status: {result.get('status')}")
            print(f"Missing fields: {result.get('missing_fields')}")
            
            if result.get('status') == 'validation_failed':
                print("✓ Invalid payload detected correctly")
            else:
                print("✗ Should have failed validation")
        except Exception as e:
            print(f"✗ Error: {e}")


async def test_webhook_stats():
    """Test webhook statistics endpoint."""
    print("\n" + "="*60)
    print("Testing Webhook Statistics")
    print("="*60)
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{API_BASE_URL}/api/v1/webhooks/stats",
                timeout=5.0
            )
            
            print(f"Status Code: {response.status_code}")
            print(f"Statistics:\n{json.dumps(response.json(), indent=2)}")
            
            if response.status_code == 200:
                print("✓ Statistics retrieved successfully")
            else:
                print("✗ Unexpected status code")
                
        except Exception as e:
            print(f"✗ Error: {e}")


async def test_invalid_source():
    """Test webhook with wrong source type."""
    print("\n" + "="*60)
    print("Testing Invalid Source Validation")
    print("="*60)
    
    # Send Notion payload to Supabase endpoint
    payload = {
        "event_type": "insert",
        "source": "notion",  # Wrong source!
        "table_name": "test",
        "record_id": "123",
        "data": {},
        "timestamp": datetime.utcnow().isoformat()
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{API_BASE_URL}/api/v1/webhooks/supabase",
                json=payload,
                timeout=5.0
            )
            
            print(f"Status Code: {response.status_code}")
            print(f"Response: {json.dumps(response.json(), indent=2)}")
            
            if response.status_code == 400:
                print("✓ Invalid source correctly rejected")
            else:
                print("✗ Should have been rejected with 400")
                
        except Exception as e:
            print(f"✗ Error: {e}")


async def main():
    """Run all tests."""
    print("\n" + "#"*60)
    print("#" + " "*58 + "#")
    print("#" + "  Webhook Integration Tests".center(58) + "#")
    print("#" + " "*58 + "#")
    print("#"*60)
    print(f"\nAPI Base URL: {API_BASE_URL}")
    print("\nMake sure the API is running before executing tests.")
    
    await asyncio.sleep(1)
    
    # Run tests
    await test_supabase_webhook()
    await asyncio.sleep(0.5)
    
    await test_notion_webhook()
    await asyncio.sleep(0.5)
    
    await test_webhook_validation()
    await asyncio.sleep(0.5)
    
    await test_invalid_source()
    await asyncio.sleep(0.5)
    
    await test_webhook_stats()
    
    print("\n" + "#"*60)
    print("#" + "  All tests completed!".center(58) + "#")
    print("#"*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())