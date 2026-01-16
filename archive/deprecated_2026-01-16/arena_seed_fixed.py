#!/usr/bin/env python3
import argparse
import json
import time
from pathlib import Path
import requests

DEFAULT_API="http://127.0.0.1:8001"

def load_questions(path: str) -> list[str]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Input not found: {path}")
    if p.suffix.lower() == ".json":
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return [q if isinstance(q, str) else q.get("question", "") for q in data]
        raise ValueError("JSON must be a list of strings or objects with 'question'")
    else:
        # treat as plain text, one question per line
        return [line.strip() for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]


def save_comparison(api_base: str, question: str) -> bool:
    payload = {
        "question": question,
        "model_a": "kicampus-original",
        "answer_a": f"Antwort A: {question}",
        "model_b": "kicampus-improved",
        "answer_b": f"Antwort B: {question}",
    }
    try:
        r = requests.post(f"{api_base}/arena/save-comparison", json=payload, timeout=15)
        if r.status_code == 200:
            return True
        print(f"WARN save-comparison {r.status_code}: {r.text[:200]}")
        return False
    except Exception as e:
        print(f"ERROR save-comparison: {e}")
        return False


def main():
    ap = argparse.ArgumentParser(description="Seed Arena with fixed questions without LLM")
    ap.add_argument("--input", required=True, help="Path to fixed questions (txt or json)")
    ap.add_argument("--api-url", default=DEFAULT_API, help="Arena API base URL")
    ap.add_argument("--limit", type=int, default=0, help="Max items to seed (0 = all)")
    args = ap.parse_args()

    # health check
    try:
        hc = requests.get(f"{args.api_url}/health", timeout=5)
        hc.raise_for_status()
    except Exception as e:
        print(f"❌ API health failed: {e}")
        return 1

    questions = load_questions(args.input)
    if args.limit and args.limit > 0:
        questions = questions[:args.limit]

    ok = 0
    for i, q in enumerate(questions, 1):
        print(f"[{i}/{len(questions)}] {q}")
        if save_comparison(args.api_url, q):
            ok += 1
        time.sleep(0.2)

    print(f"✅ Seeded {ok}/{len(questions)} comparisons")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
