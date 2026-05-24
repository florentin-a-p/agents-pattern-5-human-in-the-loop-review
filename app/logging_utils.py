import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def summarise(value: Any, max_chars: int = 500) -> str:
    """
    Produces a short log-safe summary.
    Do not log secrets, API keys, or full private datasets.
    """
    if value is None:
        return ""

    if isinstance(value, str):
        text = value
    else:
        try:
            text = json.dumps(value, ensure_ascii=False)
        except Exception:
            text = str(value)

    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key:
        text = text.replace(api_key, "[REDACTED]")
    return text[:max_chars]


def write_trace(
        run_id: str,
        agent_name: str,
        action: str,
        input_summary: Any,
        output_summary: Any,
        target_agent: Optional[str] = None,
        confidence: Optional[float] = None,
        retry_count: int = 0,
        status: str = "success",
        metadata: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """
    Writes one JSONL trace record to logs/<run_id>.jsonl.

    Required collaboration fields:
        - timestamp
        - agent_name
        - action
        - input_summary
        - output_summary
        - target_agent
        - confidence
        - retry_count
        - status
    """
    record = {
        "timestamp": utc_now_iso(),
        "run_id": run_id,
        "agent_name": agent_name,
        "action": action,
        "input_summary": summarise(input_summary),
        "output_summary": summarise(output_summary),
        "target_agent": target_agent,
        "confidence": confidence,
        "retry_count": retry_count,
        "status": status,
        "metadata": metadata or {},
    }

    trace_path = LOG_DIR / f"{run_id}.jsonl"
    with trace_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(json.dumps(record, ensure_ascii=False))
    return record


def read_trace(run_id: str) -> list[dict[str, Any]]:
    trace_path = LOG_DIR / f"{run_id}.jsonl"

    if not trace_path.exists():
        return []

    records = []
    with trace_path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    return records
