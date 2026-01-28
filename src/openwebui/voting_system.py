"""
Arena Voting System für KI-Campus Chatbot Benchmarking.

Speichert Vergleiche zwischen kicampus-original und kicampus-improved.
"""

import json
import os
import hashlib
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Literal
from enum import Enum
from pydantic import BaseModel, Field, field_validator, constr

class VoteChoice(str, Enum):
    """Valid voting options for arena comparisons."""
    A = "A"
    B = "B"
    TIE = "tie"
    BOTH_BAD = "both_bad"


def get_shuffle_seed(comparison_id: str) -> bool:
    """
    Deterministic shuffle based on comparison ID hash.
    Prevents position bias in blind A/B testing by randomly assigning models to positions.
    Uses MD5 hash of ID to ensure consistent shuffling across sessions.
    
    Args:
        comparison_id: Unique identifier for the comparison
        
    Returns:
        bool: True if models should be shuffled (swapped), False otherwise
    """
    hash_value = hashlib.md5(comparison_id.encode()).hexdigest()
    return int(hash_value[:8], 16) % 2 == 1


class ArenaComparison(BaseModel):
    """Ein einzelner Arena-Vergleich zwischen zwei Modellen."""
    
    model_config = {"extra": "allow"}  # Allow extra fields for backwards compatibility
    
    id: constr(min_length=1, max_length=100) = Field(description="Unique ID für diesen Vergleich (max 100 chars)")
    question: constr(min_length=1, max_length=2000) = Field(description="Die Frage die gestellt wurde (max 2000 chars)")
    timestamp: str = Field(description="ISO timestamp wann die Frage gestellt wurde")
    
    model_a: str = Field(description="Name des ersten Modells")
    answer_a: str = Field(description="Antwort von Modell A")
    
    model_b: str = Field(description="Name des zweiten Modells")
    answer_b: str = Field(description="Antwort von Modell B")
    
    vote: Optional[VoteChoice] = Field(default=None, description="Voting-Ergebnis (A|B|tie|both_bad)")
    vote_timestamp: Optional[str] = Field(default=None, description="Wann wurde gevotet")
    comment: Optional[constr(max_length=1000)] = Field(default=None, description="Optional: Kommentar zum Vote (max 1000 chars)")
    subset_id: Optional[int] = Field(default=None, description="Subset 1-4 für User-Assignment")
    session_id: Optional[constr(max_length=100)] = Field(default=None, description="Session ID für on-demand generation tracking (max 100 chars)")
    user_id: Optional[constr(max_length=100)] = Field(default=None, description="User ID für on-demand generation tracking (max 100 chars)")
    is_generated_on_demand: bool = Field(default=False, description="True wenn die Antworten on-demand generiert wurden")
    
    def get_shuffled_view(self) -> Dict:
        """
        Get the comparison with potentially shuffled positions to prevent position bias.
        Uses deterministic shuffling based on comparison ID so results are consistent.
        
        For blind A/B testing, this ensures:
        - Users remain blind (no model names shown during voting)
        - Position bias is prevented (models appear equally in A/B positions across dataset)
        - Admin analysis is accurate (actual_model_a/b fields track which model was shown where)
        
        Returns:
            dict with actual_model_a, actual_model_b, actual_answer_a, actual_answer_b
            indicating which model/answer appears in which position for this user
        """
        should_shuffle = get_shuffle_seed(self.id)
        
        if should_shuffle:
            # Swap models and answers to show Model B in position A and Model A in position B
            return {
                **self.model_dump(),
                "actual_model_a": self.model_b,
                "actual_model_b": self.model_a,
                "actual_answer_a": self.answer_b,
                "actual_answer_b": self.answer_a,
                "is_shuffled": True,
            }
        else:
            # No shuffle, positions match original models
            return {
                **self.model_dump(),
                "actual_model_a": self.model_a,
                "actual_model_b": self.model_b,
                "actual_answer_a": self.answer_a,
                "actual_answer_b": self.answer_b,
                "is_shuffled": False,
            }


class VotingStorage:
    """Verwaltet das Speichern und Laden von Arena Comparisons."""
    
    def __init__(self, storage_file: str = "arena_votes.jsonl"):
        """
        Args:
            storage_file: Pfad zur JSONL Datei (jede Zeile = ein JSON Objekt)
        """
        self.storage_file = Path(storage_file)
        # Erstelle Datei wenn nicht existiert
        if not self.storage_file.exists():
            self.storage_file.parent.mkdir(parents=True, exist_ok=True)
            self.storage_file.touch()
    
    def save_comparison(self, comparison: ArenaComparison) -> None:
        """Speichert einen neuen Vergleich (append-only)."""
        with open(self.storage_file, "a", encoding="utf-8") as f:
            f.write(comparison.model_dump_json() + "\n")
    
    def load_all_comparisons(self) -> List[ArenaComparison]:
        """Lädt alle gespeicherten Vergleiche."""
        comparisons = []
        if not self.storage_file.exists():
            return comparisons
        
        with open(self.storage_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    comparisons.append(ArenaComparison.model_validate_json(line))
        
        return comparisons
    
    def get_comparison_by_id(self, comparison_id: str) -> Optional[ArenaComparison]:
        """Findet einen spezifischen Vergleich anhand der ID."""
        comparisons = self.load_all_comparisons()
        for comp in comparisons:
            if comp.id == comparison_id:
                return comp
        return None
    
    def update_vote(self, comparison_id: str, vote: VoteChoice, comment: Optional[str] = None) -> bool:
        """
        Updated einen existierenden Vergleich mit Vote-Informationen.
        
        Returns:
            True wenn erfolgreich, False wenn ID nicht gefunden
        """
        if not comparison_id or len(comparison_id) > 100:
            return False
        if comment is not None and len(comment) > 1000:
            comment = comment[:1000]

        comparisons = self.load_all_comparisons()
        found = False
        
        for comp in comparisons:
            if comp.id == comparison_id:
                comp.vote = vote
                # Use timezone-aware timestamp (Europe/Berlin = UTC+1)
                comp.vote_timestamp = datetime.now(timezone.utc).astimezone().isoformat()
                if comment:
                    comp.comment = comment
                found = True
                break
        
        if not found:
            return False
        
        # Überschreibe Datei mit updated comparisons
        with open(self.storage_file, "w", encoding="utf-8") as f:
            for comp in comparisons:
                f.write(comp.model_dump_json() + "\n")
        
        return True
    
    def get_comparisons_by_subset(self, subset_id: int) -> List[ArenaComparison]:
        """Filtert Vergleiche nach Subset-ID."""
        all_comparisons = self.load_all_comparisons()
        return [c for c in all_comparisons if c.subset_id == subset_id]
    
    def get_comparisons_by_session(self, session_id: str) -> List[ArenaComparison]:
        """Filtert Vergleiche nach Session-ID (für on-demand-generierte Comparisons)."""
        all_comparisons = self.load_all_comparisons()
        return [c for c in all_comparisons if c.session_id == session_id]
    
    def add_comparison(self, comparison: ArenaComparison) -> None:
        """Alias für save_comparison (für Konsistenz)."""
        self.save_comparison(comparison)
    
    def assign_subset_round_robin(self) -> int:
        """Weist ein Subset zu basierend auf Vote-Counts (Round-Robin für faire Verteilung).
        Wenn mehrere Subsets gleich viele Votes haben, wird zufällig eines gewählt."""
        comparisons = self.load_all_comparisons()
        
        # Zähle Votes pro Subset
        subset_votes = {1: 0, 2: 0, 3: 0, 4: 0}
        for c in comparisons:
            if c.subset_id and c.vote:
                subset_votes[c.subset_id] = subset_votes.get(c.subset_id, 0) + 1
        
        # Finde Subsets mit wenigsten Votes
        min_votes = min(subset_votes.values())
        candidates = [s for s, v in subset_votes.items() if v == min_votes]
        
        # Bei Ties: zufällig wählen statt immer min()
        return random.choice(candidates)
    
    def assign_subsets_to_unassigned(self) -> int:
        """Weist unzugewiesenen Vergleichen Round-Robin Subsets zu. Returns Anzahl zugewiesener."""
        comparisons = self.load_all_comparisons()
        subset_counts = {1: 0, 2: 0, 3: 0, 4: 0}
        
        # Zähle bestehende Subsets
        for c in comparisons:
            if c.subset_id:
                subset_counts[c.subset_id] = subset_counts.get(c.subset_id, 0) + 1
        
        # Weise unzugewiesenen Vergleichen Subsets zu
        assigned = 0
        for c in comparisons:
            if c.subset_id is None:
                # Finde Subset mit wenigsten Vergleichen
                c.subset_id = min(subset_counts, key=subset_counts.get)
                subset_counts[c.subset_id] += 1
                assigned += 1
        
        # Speichere aktualisierte Comparisons
        if assigned > 0:
            with open(self.storage_file, "w", encoding="utf-8") as f:
                for comp in comparisons:
                    f.write(comp.model_dump_json() + "\n")
        
        return assigned
    
    def get_statistics(self) -> Dict[str, any]:
        """Berechnet Statistiken über alle Votes."""
        comparisons = self.load_all_comparisons()
        
        total = len(comparisons)
        voted = sum(1 for c in comparisons if c.vote is not None)
        unvoted = total - voted
        
        votes_a = sum(1 for c in comparisons if c.vote == "A")
        votes_b = sum(1 for c in comparisons if c.vote == "B")
        votes_tie = sum(1 for c in comparisons if c.vote == "tie")
        votes_both_bad = sum(1 for c in comparisons if c.vote == "both_bad")
        
        # Finde häufigste Modell-Namen
        model_names = set()
        for c in comparisons:
            model_names.add(c.model_a)
            model_names.add(c.model_b)
        
        return {
            "total_comparisons": total,
            "voted": voted,
            "unvoted": unvoted,
            "votes_for_a": votes_a,
            "votes_for_b": votes_b,
            "votes_tie": votes_tie,
            "votes_both_bad": votes_both_bad,
            "win_rate_a": votes_a / voted if voted > 0 else 0,
            "win_rate_b": votes_b / voted if voted > 0 else 0,
            "tie_rate": votes_tie / voted if voted > 0 else 0,
            "both_bad_rate": votes_both_bad / voted if voted > 0 else 0,
            "models_seen": list(model_names),
        }
    
    def export_to_json(self, output_file: str) -> None:
        """Exportiert alle Comparisons als schönes JSON Array."""
        comparisons = self.load_all_comparisons()
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(
                [c.model_dump() for c in comparisons],
                f,
                indent=2,
                ensure_ascii=False
            )


# Global Storage Instance
default_storage = VotingStorage(
    storage_file=os.getenv(
        "STORAGE_PATH",
        os.path.join(os.path.dirname(__file__), "data", "arena_votes.jsonl")
    )
)
