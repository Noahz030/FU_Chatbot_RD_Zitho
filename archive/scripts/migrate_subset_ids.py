#!/usr/bin/env python3
"""
Migration Script: Assign subset_id to existing comparisons
Distributes 109 comparisons evenly across 4 subsets using round-robin
"""
import json
from pathlib import Path

JSONL_PATH = Path(__file__).parent.parent / "src/openwebui/data/arena_votes.jsonl"

def migrate_subset_ids():
    """Assign subset_id (1-4) to all comparisons in round-robin fashion"""
    
    if not JSONL_PATH.exists():
        print(f"❌ File not found: {JSONL_PATH}")
        return
    
    # Load all comparisons
    comparisons = []
    with open(JSONL_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                comparisons.append(json.loads(line))
    
    print(f"📊 Loaded {len(comparisons)} comparisons")
    
    # Count existing subset assignments
    with_subset = sum(1 for c in comparisons if c.get("subset_id") is not None)
    print(f"   - {with_subset} already have subset_id")
    print(f"   - {len(comparisons) - with_subset} need assignment")
    
    # Assign subset_id in round-robin (1, 2, 3, 4, 1, 2, ...)
    subset_counts = {1: 0, 2: 0, 3: 0, 4: 0}
    
    for i, comp in enumerate(comparisons):
        if comp.get("subset_id") is None:
            subset_id = (i % 4) + 1  # Round-robin: 1, 2, 3, 4, 1, 2, ...
            comp["subset_id"] = subset_id
        
        subset_counts[comp["subset_id"]] += 1
    
    # Write back to file
    with open(JSONL_PATH, "w", encoding="utf-8") as f:
        for comp in comparisons:
            f.write(json.dumps(comp, ensure_ascii=False) + "\n")
    
    print(f"\n✅ Migration complete!")
    print(f"   Subset distribution:")
    for subset_id in sorted(subset_counts.keys()):
        print(f"   - Subset {subset_id}: {subset_counts[subset_id]} comparisons")
    
    total = sum(subset_counts.values())
    print(f"\n   Total: {total} comparisons across {len(subset_counts)} subsets")

if __name__ == "__main__":
    migrate_subset_ids()
