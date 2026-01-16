import argparse
import json
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict

# Reuse project models/storage
from src.openwebui.voting_system import ArenaComparison, VotingStorage


def load_questions(path: Path) -> List[str]:
    text = path.read_text(encoding="utf-8")
    lines = [l.strip() for l in text.splitlines()]
    return [l for l in lines if l]


def load_items_from_json(path: Path) -> List[Dict[str, str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("JSON must be an array of objects")
    return data


def seed_from_questions(storage: VotingStorage, questions: List[str], model_a: str, model_b: str, answer_a: str, answer_b: str) -> int:
    count = 0
    for q in questions:
        comp = ArenaComparison(
            id=str(uuid.uuid4()),
            question=q,
            timestamp=datetime.utcnow().isoformat(),
            model_a=model_a,
            answer_a=answer_a.replace("{q}", q),
            model_b=model_b,
            answer_b=answer_b.replace("{q}", q),
            vote=None,
            vote_timestamp=None,
            comment=None,
        )
        storage.save_comparison(comp)
        count += 1
    return count


def seed_from_json(storage: VotingStorage, items: List[Dict[str, str]]) -> int:
    count = 0
    for it in items:
        q = it.get("question")
        ma = it.get("model_a") or "kicampus-original"
        mb = it.get("model_b") or "kicampus-improved"
        aa = it.get("answer_a") or ""
        ab = it.get("answer_b") or ""
        comp = ArenaComparison(
            id=str(uuid.uuid4()),
            question=q,
            timestamp=datetime.utcnow().isoformat(),
            model_a=ma,
            answer_a=aa,
            model_b=mb,
            answer_b=ab,
            vote=None,
            vote_timestamp=None,
            comment=None,
        )
        storage.save_comparison(comp)
        count += 1
    return count


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description="Seed unvoted arena comparisons")
    parser.add_argument("--questions", type=str, help="Path to newline-separated questions file")
    parser.add_argument("--json", type=str, help="Path to JSON array with {question, answer_a, answer_b, model_a?, model_b?}")
    parser.add_argument("--storage-file", type=str, default=str(Path(__file__).resolve().parents[1] / "src/openwebui/data/arena_votes.jsonl"), help="Path to JSONL storage file")
    parser.add_argument("--model-a", type=str, default="kicampus-original")
    parser.add_argument("--model-b", type=str, default="kicampus-improved")
    parser.add_argument("--answer-a", type=str, default="Antwort A (auto) für: {q}")
    parser.add_argument("--answer-b", type=str, default="Antwort B (auto) für: {q}")
    parser.add_argument("--dry-run", action="store_true", help="Only print what would be added")

    args = parser.parse_args(argv)

    storage = VotingStorage(storage_file=args.storage_file)

    to_add = []
    if args.json:
        items = load_items_from_json(Path(args.json))
        if args.dry_run:
            print(f"Would add {len(items)} items from JSON")
            return 0
        added = seed_from_json(storage, items)
        print(f"Added {added} comparisons from JSON to {args.storage_file}")
        return 0

    if args.questions:
        qs = load_questions(Path(args.questions))
        if args.dry_run:
            print(f"Would add {len(qs)} questions with models A='{args.model_a}' B='{args.model_b}'")
            return 0
        added = seed_from_questions(storage, qs, args.model_a, args.model_b, args.answer_a, args.answer_b)
        print(f"Added {added} comparisons from questions to {args.storage_file}")
        return 0

    print("Nothing to do. Provide --questions or --json.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
