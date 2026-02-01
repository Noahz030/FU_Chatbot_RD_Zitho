#!/usr/bin/env python3
"""
Arena Seeding Script with LLM Integration

Reads questions from CSV/JSON, generates answers from both KI Campus models,
and seeds the Arena with unvoted comparisons.

Usage:
    python scripts/arena_seed_with_llm.py --input questions.csv --api-url http://127.0.0.1:8001
    python scripts/arena_seed_with_llm.py --input questions.json --output data/arena_votes.jsonl
"""

import argparse
import csv
import json
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests


class ArenaLLMSeeder:
    """Seed Arena comparisons by calling LLM models."""

    def __init__(
        self,
        api_base_url: str = "http://127.0.0.1:8001",
        output_file: Optional[str] = None,
        timeout: int = 60,
    ):
        """
        Args:
            api_base_url: Base URL of the OpenWebUI API
            output_file: Path to JSONL output (default: src/openwebui/data/arena_votes.jsonl)
            timeout: HTTP request timeout in seconds
        """
        self.api_base_url = api_base_url
        self.timeout = timeout

        if output_file:
            self.output_file = Path(output_file)
        else:
            self.output_file = (
                Path(__file__).parent.parent
                / "src/openwebui/data/arena_votes.jsonl"
            )

        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.models = ["kicampus-v1", "kicampus-v1-improved"]

    def check_api_health(self) -> bool:
        """Verify API is accessible."""
        try:
            resp = self.session.get(
                f"{self.api_base_url}/health", timeout=5
            )
            return resp.status_code == 200
        except Exception as e:
            print(f"❌ API not reachable: {e}")
            return False

    def get_llm_response(self, question: str, model: str) -> Optional[str]:
        """
        Call the LLM via OpenWebUI API and return the answer.

        Args:
            question: The question to ask
            model: Model name (kicampus-original or kicampus-improved)

        Returns:
            The LLM's answer text, or None if error occurs
        """
        try:
            payload = {
                "model": model,
                "messages": [
                    {"role": "user", "content": question}
                ],
                "stream": False,
                "temperature": 0.1,
                "max_tokens": 500,
            }

            resp = self.session.post(
                f"{self.api_base_url}/v1/chat/completions",
                json=payload,
                timeout=self.timeout,
            )

            if resp.status_code == 200:
                data = resp.json()
                if data.get("choices") and len(data["choices"]) > 0:
                    answer = data["choices"][0].get("message", {}).get("content", "")
                    return answer if answer else None
            else:
                print(
                    f"⚠️ Model {model}: HTTP {resp.status_code}: {resp.text[:200]}"
                )
                return None

        except requests.Timeout:
            print(f"⏱️ Model {model}: Timeout (>{self.timeout}s)")
            return None
        except Exception as e:
            print(f"❌ Model {model}: {type(e).__name__}: {e}")
            return None

    def seed_comparison(self, question: str) -> bool:
        """
        Seed a single comparison by calling both models and saving.

        Args:
            question: The question to seed

        Returns:
            True if successful, False otherwise
        """
        print(f"\n📝 Question: {question}")

        # Get answers from both models
        answers = {}
        for model in self.models:
            print(f"  → Calling {model}...", end=" ", flush=True)
            answer = self.get_llm_response(question, model)

            if answer:
                print(f"✓ ({len(answer)} chars)")
                answers[model] = answer
            else:
                print("✗ Failed")
                return False

        # Build comparison record
        comparison = {
            "id": str(uuid.uuid4()),
            "question": question,
            "timestamp": datetime.utcnow().isoformat(),
            "model_a": "kicampus-v1",
            "answer_a": answers.get("kicampus-v1", ""),
            "model_b": "kicampus-v1-improved",
            "answer_b": answers.get("kicampus-v1-improved", ""),
            "vote": None,
            "vote_timestamp": None,
            "comment": None,
        }

        # Save to JSONL
        try:
            with open(self.output_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(comparison, ensure_ascii=False) + "\n")
            print(f"  ✅ Saved: {comparison['id']}")
            return True
        except Exception as e:
            print(f"  ❌ Save error: {e}")
            return False

    def load_questions_from_csv(self, csv_file: str) -> list[str]:
        """Load questions from CSV (expects 'question' column)."""
        questions = []
        try:
            with open(csv_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if "question" in row and row["question"].strip():
                        questions.append(row["question"].strip())
            print(f"📥 Loaded {len(questions)} questions from {csv_file}")
            return questions
        except Exception as e:
            print(f"❌ Error reading CSV: {e}")
            return []

    def load_questions_from_json(self, json_file: str) -> list[str]:
        """Load questions from JSON (expects list or list of objects with 'question' key)."""
        questions = []
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, list):
                for item in data:
                    if isinstance(item, str):
                        questions.append(item)
                    elif isinstance(item, dict) and "question" in item:
                        questions.append(item["question"])

            print(f"📥 Loaded {len(questions)} questions from {json_file}")
            return questions
        except Exception as e:
            print(f"❌ Error reading JSON: {e}")
            return []

    def run(self, input_file: str, skip_health_check: bool = False) -> None:
        """
        Main seeding run.

        Args:
            input_file: CSV or JSON file with questions
            skip_health_check: Skip API health check
        """
        print(f"🚀 Arena LLM Seeding")
        print(f"   API: {self.api_base_url}")
        print(f"   Output: {self.output_file}")
        print()

        # Health check
        if not skip_health_check:
            print("🔍 Checking API health...")
            if not self.check_api_health():
                print("   ⚠️ API not healthy. Continuing anyway...")
                print()

        # Load questions
        if input_file.endswith(".csv"):
            questions = self.load_questions_from_csv(input_file)
        elif input_file.endswith(".json"):
            questions = self.load_questions_from_json(input_file)
        else:
            print(f"❌ Unknown file format: {input_file}")
            sys.exit(1)

        if not questions:
            print("❌ No questions loaded.")
            sys.exit(1)

        # Seed comparisons
        print(f"\n🎯 Seeding {len(questions)} comparisons...\n")
        successful = 0
        failed = 0

        for i, question in enumerate(questions, 1):
            print(f"[{i}/{len(questions)}]", end=" ")
            if self.seed_comparison(question):
                successful += 1
            else:
                failed += 1

            # Small delay between requests to avoid overwhelming API
            if i < len(questions):
                time.sleep(1)

        # Summary
        print(f"\n{'='*60}")
        print(f"✅ Summary:")
        print(f"   Successful: {successful}/{len(questions)}")
        print(f"   Failed: {failed}/{len(questions)}")
        print(f"   Output file: {self.output_file}")
        print(f"{'='*60}\n")

        if failed > 0:
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Seed Arena comparisons with LLM-generated answers"
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Input file (CSV or JSON) with questions",
    )
    parser.add_argument(
        "--output",
        help="Output JSONL file (default: src/openwebui/data/arena_votes.jsonl)",
    )
    parser.add_argument(
        "--api-url",
        default="http://127.0.0.1:8001",
        help="OpenWebUI API base URL",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="HTTP request timeout in seconds",
    )
    parser.add_argument(
        "--skip-health-check",
        action="store_true",
        help="Skip API health check",
    )

    args = parser.parse_args()

    seeder = ArenaLLMSeeder(
        api_base_url=args.api_url,
        output_file=args.output,
        timeout=args.timeout,
    )
    seeder.run(args.input, skip_health_check=args.skip_health_check)


if __name__ == "__main__":
    main()
