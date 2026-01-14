from fastapi import FastAPI, HTTPException, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Literal, Dict, Tuple, List
from datetime import datetime
import uuid
import json
from pathlib import Path

from src.openwebui.voting_system import default_storage, ArenaComparison

app = FastAPI(
    title="KI-Campus Arena API (Light)",
    description="Leichte API nur für Arena-Endpunkte, ohne LLM-Imports",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"status": "online", "service": "KI-Campus Arena (Light)"}


@app.get("/health")
def health():
    return {"status": "healthy"}


class SaveComparisonRequest(BaseModel):
    question: str
    model_a: str
    answer_a: str
    model_b: str
    answer_b: str


class VoteRequest(BaseModel):
    comparison_id: str
    vote: Literal["A", "B", "tie", "both_bad"]
    comment: Optional[str] = None
    subset_id: Optional[int] = None


@app.post("/arena/save-comparison")
def save_comparison(request: SaveComparisonRequest):
    comparison = ArenaComparison(
        id=str(uuid.uuid4()),
        question=request.question,
        timestamp=datetime.utcnow().isoformat(),
        model_a=request.model_a,
        answer_a=request.answer_a,
        model_b=request.model_b,
        answer_b=request.answer_b,
    )
    default_storage.save_comparison(comparison)
    return {"success": True, "comparison_id": comparison.id}


@app.post("/arena/vote")
def submit_vote(request: VoteRequest, x_session_id: Optional[str] = Header(default=None)):
    # Basic validation
    if not x_session_id:
        raise HTTPException(status_code=400, detail="X-Session-ID header required")

    # 1) Append per-session vote (append-only)
    data_dir = Path(__file__).parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    user_votes_file = data_dir / "arena_user_votes.jsonl"
    vote_record = {
        "comparison_id": request.comparison_id,
        "vote": request.vote,
        "comment": request.comment,
        "subset_id": request.subset_id,
        "session_id": x_session_id,
        "timestamp": datetime.utcnow().isoformat(),
    }
    with user_votes_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(vote_record, ensure_ascii=False) + "\n")

    # 2) Keep backwards compatibility: also update the global comparison vote
    #    (This will reflect a last-writer-wins global view, but UI now filters by session.)
    success = default_storage.update_vote(
        comparison_id=request.comparison_id,
        vote=request.vote,
        comment=request.comment,
    )
    if not success:
        raise HTTPException(status_code=404, detail="Comparison ID not found")
    return {"success": True}


@app.get("/arena/comparisons")
def get_all_comparisons(subset: Optional[int] = None):
    if subset is not None:
        comparisons = default_storage.get_comparisons_by_subset(subset)
    else:
        comparisons = default_storage.load_all_comparisons()
    return {"total": len(comparisons), "comparisons": [c.model_dump() for c in comparisons]}


@app.get("/arena/statistics")
def get_statistics():
    """Aggregierte Statistiken auf Basis individueller Nutzer-Votes (session-basiert).

    Reduziert auf den jeweils letzten Vote je (session_id, comparison_id).
    """
    data_dir = Path(__file__).parent / "data"
    user_votes_file = data_dir / "arena_user_votes.jsonl"

    latest: Dict[Tuple[str, str], Dict] = {}
    if user_votes_file.exists():
        with user_votes_file.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                key = (obj.get("session_id", ""), str(obj.get("comparison_id", "")))
                ts = obj.get("timestamp") or ""
                # Last write wins by timestamp
                if key not in latest or ts >= latest[key].get("timestamp", ""):
                    latest[key] = obj

    totals = {"A": 0, "B": 0, "tie": 0, "both_bad": 0}
    for v in latest.values():
        ch = v.get("vote")
        if ch in totals:
            totals[ch] += 1

    voted_count = sum(totals.values())
    return {
        "distinct_user_votes": len(latest),
        "votes_for_a": totals["A"],
        "votes_for_b": totals["B"],
        "votes_tie": totals["tie"],
        "votes_both_bad": totals["both_bad"],
        "win_rate_a": (totals["A"] / voted_count) if voted_count else 0,
        "win_rate_b": (totals["B"] / voted_count) if voted_count else 0,
        "tie_rate": (totals["tie"] / voted_count) if voted_count else 0,
        "both_bad_rate": (totals["both_bad"] / voted_count) if voted_count else 0,
    }


@app.get("/arena/comparison/{comparison_id}")
def get_comparison(comparison_id: str):
    c = default_storage.get_comparison_by_id(comparison_id)
    if not c:
        raise HTTPException(status_code=404, detail="Comparison not found")
    return c.model_dump()


@app.get("/arena/assign-subset")
def assign_subset():
    """Weist dem User ein Subset zu (Round-Robin basierend auf Vote-Counts)."""
    subset_id = default_storage.assign_subset_round_robin()
    return {"subset_id": subset_id, "message": f"Du wurdest Subset {subset_id} zugewiesen"}


@app.get("/arena/voted")
def get_voted(session_id: str = Query(..., description="Client Session-ID")):
    """Liefert die Liste comparison_ids, die diese Session bereits gevoted hat."""
    data_dir = Path(__file__).parent / "data"
    user_votes_file = data_dir / "arena_user_votes.jsonl"
    voted: List[str] = []
    seen: set[str] = set()
    if user_votes_file.exists():
        with user_votes_file.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if obj.get("session_id") == session_id:
                    cid = str(obj.get("comparison_id", ""))
                    if cid and cid not in seen:
                        seen.add(cid)
                        voted.append(cid)
    return {"comparison_ids": voted}


@app.get("/arena/session")
def create_session():
    """Erzeugt eine neue Session-ID (optional – Clients können auch selbst UUIDs erzeugen)."""
    return {"session_id": str(uuid.uuid4())}
