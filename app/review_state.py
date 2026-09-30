"""
Human Review & Audit State Management for ReconFlow.

Provides in-memory session persistence for exception review workflows,
decision audit notes, and escalation logs.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional


class ReviewStatus:
    UNREVIEWED = "UNREVIEWED"
    REVIEWED = "REVIEWED"
    ESCALATED = "ESCALATED"


class ReviewStateStore:
    """
    In-memory review state store keyed by unique exception composite ID.
    """

    def __init__(self):
        self._reviews: Dict[str, Dict[str, Any]] = {}

    @staticmethod
    def make_key(source_a_id: Optional[str], source_b_id: Optional[str], reference: Optional[str]) -> str:
        return f"A:{source_a_id or 'NONE'}|B:{source_b_id or 'NONE'}|R:{reference or 'NONE'}"

    def update_review(
        self,
        key: str,
        status: str,
        note: str = "",
        reviewer: str = "Ops Analyst"
    ) -> Dict[str, Any]:
        """
        Updates review status and appends audit trail entry.
        """
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if key not in self._reviews:
            self._reviews[key] = {
                "key": key,
                "status": ReviewStatus.UNREVIEWED,
                "note": "",
                "reviewer": reviewer,
                "updated_at": now_str,
                "history": []
            }

        prev_status = self._reviews[key]["status"]
        self._reviews[key]["status"] = status
        if note.strip():
            self._reviews[key]["note"] = note.strip()
        self._reviews[key]["reviewer"] = reviewer
        self._reviews[key]["updated_at"] = now_str

        self._reviews[key]["history"].append({
            "timestamp": now_str,
            "reviewer": reviewer,
            "from_status": prev_status,
            "to_status": status,
            "note": note.strip()
        })

        return self._reviews[key]

    def get_review(self, key: str) -> Dict[str, Any]:
        """
        Retrieves current review state for a record key.
        """
        return self._reviews.get(key, {
            "key": key,
            "status": ReviewStatus.UNREVIEWED,
            "note": "",
            "reviewer": "",
            "updated_at": "",
            "history": []
        })

    def get_all_reviews(self) -> List[Dict[str, Any]]:
        """
        Returns list of all active review records for exports and reporting.
        """
        return list(self._reviews.values())


# Module-level singleton instance for session usage
_global_review_store = ReviewStateStore()

def get_review_store() -> ReviewStateStore:
    return _global_review_store
