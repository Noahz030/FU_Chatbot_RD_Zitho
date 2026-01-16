#!/usr/bin/env python3
"""Diagnostic: Qdrant Connection & Collections"""
import sys
import os

print("=" * 70)
print("DIAGNOSTIC: Qdrant Connection & Collections")
print("=" * 70)

try:
    from qdrant_client import QdrantClient
    
    # Get from environment
    qdrant_url = os.getenv('PROD_QDRANT_URL')
    qdrant_key = os.getenv('PROD_QDRANT_API_KEY')
    
    print(f"\n✓ Environment vars loaded")
    print(f"  PROD_QDRANT_URL: {qdrant_url}")
    print(f"  PROD_QDRANT_API_KEY: {'***' if qdrant_key else 'MISSING'}")
    
    if not qdrant_url or not qdrant_key:
        print(f"\n✗ Missing Qdrant credentials!")
        sys.exit(1)
    
    # Connect to Qdrant
    print(f"\nConnecting to Qdrant...")
    client = QdrantClient(url=qdrant_url, api_key=qdrant_key, timeout=5.0)
    print(f"✓ Connected to Qdrant")
    
    # List all collections
    collections = client.get_collections()
    print(f"\n✓ Found {len(collections.collections)} collections:")
    for col in collections.collections:
        print(f"  - {col.name} ({col.points_count} vectors)")
    
    # Check specifically for web_assistant collection
    print(f"\n--- Checking 'web_assistant' collection ---")
    try:
        collection_info = client.get_collection("web_assistant")
        print(f"✓ Collection exists: web_assistant")
        print(f"  - Vector count: {collection_info.points_count}")
        print(f"  - Vector size: {collection_info.config.params.vectors.size}")
        print(f"  - Distance metric: {collection_info.config.params.vectors.distance}")
    except Exception as e:
        print(f"✗ Collection 'web_assistant' error: {e}")
    
except Exception as e:
    print(f"\n✗ Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
