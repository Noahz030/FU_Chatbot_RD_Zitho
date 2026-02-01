#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, '/home/appuser')

print("=" * 70)
print("DIAGNOSTIC: Retriever Initialization")
print("=" * 70)

try:
    print("\n1. Importing retriever module...")
    from src.llm.objects.retriever import VectorDBQdrant
    print("   ✓ VectorDBQdrant imported")
    
    print("\n2. Creating VectorDBQdrant instance...")
    retriever = VectorDBQdrant()
    print("   ✓ VectorDBQdrant instance created")
    
    print("\n3. Checking collection...")
    print(f"   Collection name: {retriever.collection_name}")
    
    print("\n✓ SUCCESS: Retriever initialized without errors")
    
except Exception as e:
    print(f"\n✗ ERROR: {type(e).__name__}: {e}")
    import traceback
    print("\nFull traceback:")
    traceback.print_exc()
