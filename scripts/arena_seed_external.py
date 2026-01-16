#!/usr/bin/env python3
"""
Seed Arena with comparisons between Original and Improved Chatbot
Uses simple KI-Campus questions for initial testing

IMPORTANT: This script writes to src/openwebui/data/arena_votes.jsonl
(NOT to data/arena_votes.jsonl in the workspace root).
The Arena UI loads from src/openwebui/data/, so seeded comparisons must be written there.
"""

import json
import requests
import sys
import uuid
from pathlib import Path
from datetime import datetime, timezone

# Configuration
ARENA_API = "http://localhost:8001"
MODELS = ["kicampus-v1", "kicampus-v1-improved"]

# Load fixed question set (one question per line, UTF-8)
_fixed_questions_file = Path(__file__).parent.parent / "data" / "fixed_questions.txt"
if not _fixed_questions_file.exists():
    print(f"❌ Fixed question file not found: {_fixed_questions_file}")
    sys.exit(1)

TEST_QUESTIONS = [q.strip() for q in _fixed_questions_file.read_text(encoding="utf-8").splitlines() if q.strip()]

# CRITICAL: Write to src/openwebui/data/ directory (where Arena loads from)
# NOT to data/ in workspace root
_votes_file = Path(__file__).parent.parent / "src" / "openwebui" / "data" / "arena_votes.jsonl"
_votes_file.parent.mkdir(parents=True, exist_ok=True)

def chat_with_model(model: str, question: str) -> dict:
    """Call Arena API and get response from specified model"""
    try:
        response = requests.post(
            f"{ARENA_API}/v1/chat/completions",
            json={
                "model": model,
                "messages": [{"role": "user", "content": question}]
            },
            timeout=60
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Error calling {model}: {e}")
        return None

def seed_comparisons():
    """Create comparisons between both models for all test questions"""
    print("🌱 Starting Arena Seeding...")
    print(f"   Models: {', '.join(MODELS)}")
    print(f"   Questions: {len(TEST_QUESTIONS)}")
    print()
    
    successful = 0
    failed = 0
    
    for i, question in enumerate(TEST_QUESTIONS, 1):
        print(f"[{i}/{len(TEST_QUESTIONS)}] 📝 Question: {question[:50]}...")
        
        # Get responses from both models
        responses = {}
        for model in MODELS:
            print(f"     🔄 Calling {model}...", end=" ", flush=True)
            result = chat_with_model(model, question)
            
            if result and "choices" in result:
                responses[model] = result["choices"][0]["message"]["content"]
                print(f"✅ Got {len(responses[model])} chars")
            else:
                print(f"❌ Failed")
                failed += 1
                break
        
        # If we got both responses, save them
        if len(responses) == 2:
            # Create comparison with required Arena fields (id, timestamp, answer_a, answer_b)
            comparison = {
                "id": str(uuid.uuid4()),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "question": question,
                "model_a": MODELS[0],
                "model_b": MODELS[1],
                "answer_a": responses[MODELS[0]],
                "answer_b": responses[MODELS[1]],
            }
            
            # Save to Arena votes file (in src/openwebui/data/ - where Arena loads from)
            try:
                with open(_votes_file, "a") as f:
                    f.write(json.dumps(comparison) + "\n")
                print(f"     💾 Saved comparison")
                successful += 1
            except Exception as e:
                print(f"     ❌ Error saving: {e}")
                failed += 1
        
        print()
    
    print("=" * 60)
    print(f"✅ Seeding Complete!")
    print(f"   ✓ Successful: {successful}")
    print(f"   ✗ Failed: {failed}")
    print(f"   📊 Saved to: {_votes_file}")
    print(f"   📊 Comparisons ready for voting at http://localhost:8002")
    print("=" * 60)

if __name__ == "__main__":
    seed_comparisons()
