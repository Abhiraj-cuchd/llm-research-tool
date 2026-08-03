import json
import os
from datetime import datetime
from pathlib import Path

from utils.validators import (
    InterviewJSON,
    CodingResult,
    FailedCoding,
    ParticipantScore,
    DimensionScore,
    Codebook,
)


def _serialise(obj):
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    return str(obj)


def save_session(session_state: dict, study_name: str = "study") -> str:
    data_dir = Path("data")
    data_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{study_name}.json"
    filepath = data_dir / filename

    payload = {
        "study_name": study_name,
        "saved_at": datetime.now().isoformat(),
        "codebook": session_state.get("codebook"),
        "transcripts": session_state.get("transcripts", {}),
        "coding_results": session_state.get("coding_results", {}),
        "scores": session_state.get("scores", {}),
        "run_metadata": session_state.get("run_metadata", {}),
    }

    serialised = json.loads(json.dumps(payload, default=_serialise, ensure_ascii=False))

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(serialised, f, ensure_ascii=False, indent=2)

    return str(filepath)


def load_session(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    codebook_raw = data.get("codebook")
    if codebook_raw:
        data["codebook"] = Codebook(**codebook_raw)

    transcripts_raw = data.get("transcripts", {})
    data["transcripts"] = {
        pid: InterviewJSON(**t) for pid, t in transcripts_raw.items()
    }

    coding_raw = data.get("coding_results", {})
    coding_results = {}
    for pid, cr in coding_raw.items():
        dims = {}
        for dim_id, ds in cr.get("dimensions", {}).items():
            dims[dim_id] = DimensionScore(**ds)
        coding_results[pid] = CodingResult(
            participant=cr["participant"],
            dimensions=dims,
            model=cr.get("model", ""),
            prompt_version=cr.get("prompt_version", ""),
            timestamp=cr.get("timestamp", ""),
            summary=cr.get("summary", ""),
            human_reviewed=cr.get("human_reviewed", False),
        )
    data["coding_results"] = coding_results

    scores_raw = data.get("scores", {})
    data["scores"] = {pid: ParticipantScore(**s) for pid, s in scores_raw.items()}

    return data


def list_sessions() -> list[dict]:
    data_dir = Path("data")
    if not data_dir.exists():
        return []

    sessions = []
    for f in sorted(data_dir.glob("*.json"), reverse=True):
        try:
            with open(f, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            stat = f.stat()
            sessions.append({
                "path": str(f),
                "study_name": data.get("study_name", "Unknown"),
                "timestamp": data.get("saved_at", ""),
                "participant_count": len(data.get("coding_results", {})),
            })
        except Exception:
            continue

    return sessions
