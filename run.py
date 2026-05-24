import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from openai import OpenAI
from pydantic import BaseModel, Field

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
TRACE_FILE = BASE_DIR / "logs" / "agent_trace.jsonl"
INPUT_DIR = BASE_DIR / "input_examples"

DEFAULT_BASE_URL = "https://compass.core42.ai/v1"
DEFAULT_MODEL = "gpt-4o-mini"
MAX_RETRIES = 3

RiskCategory = Literal[
    "harassment",
    "hate_speech",
    "spam",
    "scam",
    "violence",
    "adult_content",
    "safe",
]
PolicyDecision = Literal["allow", "warn", "remove", "suspend"]

POLICY_RULES: dict[str, dict[str, Any]] = {
    "safe": {"decision": "allow", "severity": "none"},
    "spam": {"decision": "warn", "severity": "low"},
    "adult_content": {"decision": "warn", "severity": "medium"},
    "harassment": {"decision": "remove", "severity": "medium"},
    "hate_speech": {"decision": "suspend", "severity": "high"},
    "scam": {"decision": "suspend", "severity": "high"},
    "violence": {"decision": "suspend", "severity": "high"},
}


class ModerationRequest(BaseModel):
    content: str | None = Field(default=None, description="Submitted content to moderate.")
    content_id: str | None = None
    user_id: str | None = None
    sample_id: str | None = Field(default=None, description="Loads input_examples/<sample_id>.json in sample mode.")
    conversation_history: list[dict[str, str]] = Field(default_factory=list)
    user_relationship: str | None = Field(default=None, description="Known relationship between participants.")
    detected_language: str | None = Field(default=None, description="Detected language code, for example en or ar.")
    locale: str | None = Field(default=None, description="Locale code, for example en-US or ar-AE.")
    community_type: str | None = Field(default=None, description="Community or surface type, for example sports_chat.")
    human_review_approved: bool | None = Field(
        default=None,
        description="Human approval for the final PolicyAgent recommendation.",
    )
    human_rejection_reason: str | None = Field(
        default=None,
        description="Reason used when human rejects the recommendation and sends the workflow back.",
    )
    max_iterations: int = Field(
        default=2,
        ge=1,
        le=20,
        description="Maximum number of agent-to-agent collaboration iterations, from 1 to 20.",
    )


class ModerationResponse(BaseModel):
    run_id: str
    sample_mode: bool
    status: str
    detection: dict[str, Any]
    context_analysis: dict[str, Any]
    policy: dict[str, Any]
    final_action: dict[str, Any] | None
    iterations_used: int
    max_iterations: int
    trace_file: str


class TraceLogger:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def event(self, run_id: str, agent: str, event: str, payload: dict[str, Any]) -> None:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "run_id": run_id,
            "agent": agent,
            "event": event,
            "payload": redact(payload),
        }
        line = json.dumps(record, ensure_ascii=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
        print(line, flush=True)


def redact(payload: dict[str, Any]) -> dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY")
    text = json.dumps(payload, ensure_ascii=True)
    if api_key:
        text = text.replace(api_key, "[REDACTED]")
    return json.loads(text)


def parse_json_object(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise


def sample_mode_enabled() -> bool:
    return os.getenv("SAMPLE_MODE", "false").lower() == "true"


class CompassClient:
    def __init__(self) -> None:
        self.sample_mode = sample_mode_enabled()
        self.model = os.getenv("COMPASS_MODEL") or os.getenv("MODEL_FAST", DEFAULT_MODEL)
        self.base_url = os.getenv("OPENAI_BASE_URL", DEFAULT_BASE_URL)
        api_key = os.getenv("OPENAI_API_KEY")
        self.client: OpenAI | None = None
        if not self.sample_mode:
            if not api_key:
                raise RuntimeError("OPENAI_API_KEY is required unless SAMPLE_MODE=true.")
            self.client = OpenAI(api_key=api_key, base_url=self.base_url)

    def json_chat(self, system_prompt: str, payload: dict[str, Any]) -> dict[str, Any]:
        if self.sample_mode:
            raise RuntimeError("Compass is disabled in SAMPLE_MODE.")
        if self.client is None:
            raise RuntimeError("Compass client is not initialized.")

        last_error: Exception | None = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                    ],
                    temperature=0.1,
                    response_format={"type": "json_object"},
                )
                content = response.choices[0].message.content
                if not content:
                    raise RuntimeError("Compass returned an empty response.")
                return parse_json_object(content)
            except Exception as exc:
                last_error = exc
                if attempt < MAX_RETRIES:
                    time.sleep(0.6 * attempt)
        raise RuntimeError(f"Compass request failed after {MAX_RETRIES} attempts: {last_error}")


class DetectionAgent:
    name = "DetectionAgent"

    system_prompt = """
    Detect possible harmful content. Return only JSON:
    {
      "category": "harassment|hate_speech|spam|scam|violence|adult_content|safe",
      "confidence": 0.0,
      "risk_score": 0.0,
      "signals": ["brief evidence labels"],
      "rationale": "brief reason"
    }
    """

    def __init__(self, compass: CompassClient, trace: TraceLogger) -> None:
        self.compass = compass
        self.trace = trace

    def run(
        self,
        run_id: str,
        content: str,
        context_feedback: dict[str, Any] | None = None,
        human_rejection_reason: str | None = None,
    ) -> dict[str, Any]:
        if self.compass.sample_mode:
            result = detect_locally(content)
        else:
            result = self.compass.json_chat(
                self.system_prompt,
                {
                    "content": content,
                    "context_feedback": context_feedback,
                    "human_rejection_reason": human_rejection_reason,
                },
            )
        result = normalize_detection(result)
        if context_feedback:
            result = apply_context_feedback(result, context_feedback)
        if human_rejection_reason:
            result["human_feedback"] = human_rejection_reason
            result["confidence"] = max(0.2, round(result["confidence"] - 0.1, 2))

        self.trace.event(run_id, self.name, "detection_completed", result)
        return result


class ContextAnalysisAgent:
    name = "ContextAnalysisAgent"

    system_prompt = """
    Analyze moderation context: conversation history, sarcasm, previous messages,
    user relationships, detected language, locale, and community type. Return only JSON:
    {
      "context_risk_modifier": -0.2,
      "sarcasm_or_joking_likely": false,
      "relationship_context": "brief summary",
      "language_context": "brief summary",
      "locale_context": "brief summary",
      "community_context": "brief summary",
      "needs_more_context": false,
      "feedback_to_detection": "specific feedback",
      "rationale": "brief reason"
    }
    """

    def __init__(self, compass: CompassClient, trace: TraceLogger) -> None:
        self.compass = compass
        self.trace = trace

    def run(
        self,
        run_id: str,
        payload: dict[str, Any],
        detection: dict[str, Any],
        policy_question: str | None = None,
    ) -> dict[str, Any]:
        if self.compass.sample_mode:
            result = analyze_context_locally(payload, detection, policy_question)
        else:
            result = self.compass.json_chat(
                self.system_prompt,
                {
                    "content": payload["content"],
                    "conversation_history": payload.get("conversation_history", []),
                    "user_relationship": payload.get("user_relationship"),
                    "detected_language": payload.get("detected_language"),
                    "locale": payload.get("locale"),
                    "community_type": payload.get("community_type"),
                    "detection": detection,
                    "policy_question": policy_question,
                },
            )
        result = normalize_context(result)
        self.trace.event(run_id, self.name, "context_feedback_completed", result)
        return result


class PolicyAgent:
    name = "PolicyAgent"

    system_prompt = """
    Decide the moderation policy action. Allowed decisions: allow, warn, remove, suspend.
    Sometimes request more context before finalizing. Return only JSON:
    {
      "decision": "allow|warn|remove|suspend",
      "severity": "none|low|medium|high",
      "confidence": 0.0,
      "needs_more_context": false,
      "context_question": "",
      "rationale": "brief reason",
      "user_message": "brief user-facing message"
    }
    """

    def __init__(self, compass: CompassClient, trace: TraceLogger) -> None:
        self.compass = compass
        self.trace = trace

    def run(
        self,
        run_id: str,
        detection: dict[str, Any],
        context: dict[str, Any],
        content_id: str,
        user_id: str,
        prior_policy: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if self.compass.sample_mode:
            result = decide_policy_locally(detection, context, prior_policy)
        else:
            result = self.compass.json_chat(
                self.system_prompt,
                {
                    "detection": detection,
                    "context_analysis": context,
                    "content_id": content_id,
                    "user_id": user_id,
                    "prior_policy": prior_policy,
                },
            )
        result = normalize_policy(result, content_id, user_id)
        self.trace.event(run_id, self.name, "policy_completed", result)
        return result


def detect_locally(content: str) -> dict[str, Any]:
    text = content.lower()
    checks = [
        ("scam", ["wire money", "guaranteed return", "send crypto", "password", "bank login"]),
        ("hate_speech", ["inferior race", "ethnic slur", "deport all", "hate them because"]),
        ("violence", ["kill", "bomb", "shoot", "stab", "attack them"]),
        ("adult_content", ["explicit", "nude", "porn", "sexual"]),
        ("harassment", ["idiot", "worthless", "shut up", "loser", "humiliate"]),
        ("spam", ["buy now", "free prize", "click this link", "limited offer", "subscribe now"]),
    ]
    matches: list[tuple[str, str]] = []
    for category, terms in checks:
        for term in terms:
            if term in text:
                matches.append((category, term))

    if not matches:
        return {
            "category": "safe",
            "confidence": 0.82,
            "risk_score": 0.05,
            "signals": ["no sample-mode risk terms matched"],
            "rationale": "No configured harmful-content signals were detected.",
        }

    category = matches[0][0]
    score = min(0.98, 0.45 + 0.14 * len(matches))
    return {
        "category": category,
        "confidence": round(min(0.96, score + 0.08), 2),
        "risk_score": round(score, 2),
        "signals": [term for _, term in matches[:6]],
        "rationale": f"Matched sample-mode signals associated with {category}.",
    }


def analyze_context_locally(
    payload: dict[str, Any],
    detection: dict[str, Any],
    policy_question: str | None,
) -> dict[str, Any]:
    history = payload.get("conversation_history", [])
    relationship = (payload.get("user_relationship") or "").lower()
    detected_language = payload.get("detected_language") or "unknown"
    locale = payload.get("locale") or "unknown"
    community_type = payload.get("community_type") or "unknown"
    content = payload["content"].lower()
    joking = any(token in content for token in ["lol", "jk", "just kidding", "/s"])
    friends = any(token in relationship for token in ["friend", "teammate", "family"])
    casual_community = any(token in community_type.lower() for token in ["sports", "gaming", "casual"])
    modifier = 0.0
    feedback = "No strong contextual adjustment."

    if joking or friends or casual_community:
        modifier -= 0.18
        feedback = "Conversation context suggests possible joking or familiar banter."
    if policy_question and len(history) < 2:
        return {
            "context_risk_modifier": modifier,
            "sarcasm_or_joking_likely": joking,
            "relationship_context": payload.get("user_relationship") or "unknown",
            "language_context": detected_language,
            "locale_context": locale,
            "community_context": community_type,
            "needs_more_context": True,
            "feedback_to_detection": "PolicyAgent asked for more context, but history is limited.",
            "rationale": "More conversation history would reduce uncertainty.",
        }
    if detection["category"] in {"scam", "violence", "hate_speech"}:
        modifier += 0.08
        feedback = "Context does not reduce severity for high-risk category."

    return {
        "context_risk_modifier": round(modifier, 2),
        "sarcasm_or_joking_likely": joking,
        "relationship_context": payload.get("user_relationship") or "unknown",
        "language_context": detected_language,
        "locale_context": locale,
        "community_context": community_type,
        "needs_more_context": False,
        "feedback_to_detection": feedback,
        "rationale": f"Reviewed {len(history)} prior message(s), relationship, language, locale, and community type.",
    }


def decide_policy_locally(
    detection: dict[str, Any],
    context: dict[str, Any],
    prior_policy: dict[str, Any] | None,
) -> dict[str, Any]:
    adjusted_score = detection["risk_score"]
    category = detection["category"]
    rule = POLICY_RULES[category]
    decision = rule["decision"]

    if adjusted_score < 0.2:
        decision = "allow"
    elif context.get("sarcasm_or_joking_likely") and category == "harassment" and adjusted_score < 0.7:
        decision = "warn"
    elif adjusted_score < 0.45 and decision in {"remove", "suspend"}:
        decision = "warn"
    elif adjusted_score > 0.86 and category in {"hate_speech", "scam", "violence"}:
        decision = "suspend"

    needs_more_context = (
        0.4 <= adjusted_score <= 0.75
        and not context.get("sarcasm_or_joking_likely")
        and category not in {"safe", "spam"}
    )
    return {
        "decision": decision,
        "severity": rule["severity"],
        "confidence": round(max(detection["confidence"] - abs(context["context_risk_modifier"]) / 2, 0.2), 2),
        "needs_more_context": needs_more_context,
        "context_question": (
            "Check prior messages, relationship context, locale, language, and community type before final action."
            if needs_more_context
            else ""
        ),
        "rationale": f"Policy decision based on {category} with adjusted risk {adjusted_score:.2f}.",
        "user_message": user_message_for(decision),
    }


def normalize_detection(result: dict[str, Any]) -> dict[str, Any]:
    category = result.get("category")
    if category not in POLICY_RULES:
        category = "safe"
    confidence = clamp_float(result.get("confidence"), 0.0)
    risk_score = clamp_float(result.get("risk_score"), confidence)
    return {
        "category": category,
        "confidence": confidence,
        "risk_score": risk_score,
        "signals": list(result.get("signals") or []),
        "rationale": str(result.get("rationale") or ""),
    }


def normalize_context(result: dict[str, Any]) -> dict[str, Any]:
    try:
        modifier = float(result.get("context_risk_modifier", 0.0))
    except (TypeError, ValueError):
        modifier = 0.0
    return {
        "context_risk_modifier": round(max(-0.4, min(0.4, modifier)), 2),
        "sarcasm_or_joking_likely": bool(result.get("sarcasm_or_joking_likely", False)),
        "relationship_context": str(result.get("relationship_context") or "unknown"),
        "language_context": str(result.get("language_context") or "unknown"),
        "locale_context": str(result.get("locale_context") or "unknown"),
        "community_context": str(result.get("community_context") or "unknown"),
        "needs_more_context": bool(result.get("needs_more_context", False)),
        "feedback_to_detection": str(result.get("feedback_to_detection") or ""),
        "rationale": str(result.get("rationale") or ""),
    }


def normalize_policy(result: dict[str, Any], content_id: str, user_id: str) -> dict[str, Any]:
    decision = result.get("decision")
    if decision not in {"allow", "warn", "remove", "suspend"}:
        decision = "warn"
    policy = {
        "decision": decision,
        "severity": str(result.get("severity") or "medium"),
        "confidence": clamp_float(result.get("confidence"), 0.5),
        "needs_more_context": bool(result.get("needs_more_context", False)),
        "context_question": str(result.get("context_question") or ""),
        "rationale": str(result.get("rationale") or ""),
        "user_message": str(result.get("user_message") or user_message_for(decision)),
    }
    policy["action"] = {
        "content_id": content_id,
        "user_id": user_id,
        "action_type": decision,
        "user_message": policy["user_message"],
    }
    return policy


def apply_context_feedback(detection: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    adjusted = dict(detection)
    adjusted["risk_score"] = round(
        max(0.0, min(1.0, detection["risk_score"] + context["context_risk_modifier"])),
        2,
    )
    adjusted["context_feedback_applied"] = context["feedback_to_detection"]
    if adjusted["risk_score"] < 0.2:
        adjusted["category"] = "safe"
    return adjusted


def clamp_float(value: Any, default: float) -> float:
    try:
        return round(max(0.0, min(1.0, float(value))), 2)
    except (TypeError, ValueError):
        return default


def user_message_for(decision: str) -> str:
    return {
        "allow": "Your content is live.",
        "warn": "Your content is live with a warning because it may approach our safety limits.",
        "remove": "Your content was removed because it violates platform policy.",
        "suspend": "Your account action is under restriction due to a serious policy violation.",
    }[decision]


def load_sample(sample_id: str | None) -> dict[str, Any]:
    selected = sample_id or "sample_1"
    path = INPUT_DIR / f"{selected}.json"
    if not path.exists():
        raise HTTPException(status_code=400, detail=f"Sample input not found: {selected}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def request_to_payload(request: ModerationRequest, sample_mode: bool) -> dict[str, Any]:
    payload = request.model_dump(exclude_none=True, exclude_unset=True)
    if sample_mode and (request.sample_id or not request.content):
        sample = load_sample(request.sample_id)
        sample.update(payload)
        payload = sample
    if not payload.get("content"):
        raise HTTPException(status_code=400, detail="Field 'content' is required.")
    payload.setdefault("content_id", f"content-{uuid.uuid4().hex[:8]}")
    payload.setdefault("user_id", "anonymous")
    payload.setdefault("conversation_history", [])
    payload.setdefault("max_iterations", 2)
    return payload


def run_workflow(
    run_id: str,
    payload: dict[str, Any],
    compass: CompassClient,
    trace: TraceLogger,
) -> dict[str, Any]:
    detection_agent = DetectionAgent(compass, trace)
    context_agent = ContextAnalysisAgent(compass, trace)
    policy_agent = PolicyAgent(compass, trace)

    detection: dict[str, Any] | None = None
    context: dict[str, Any] | None = None
    policy: dict[str, Any] | None = None
    approved = payload.get("human_review_approved")
    human_rejection_reason = payload.get("human_rejection_reason") or "Human moderator rejected the recommendation."
    policy_question: str | None = None

    for iteration in range(1, payload["max_iterations"] + 1):
        trace.event(run_id, "Orchestrator", "iteration_started", {"iteration": iteration})
        rejection_feedback = human_rejection_reason if approved is False and iteration > 1 else None
        if rejection_feedback:
            trace.event(
                run_id,
                "HumanModerator",
                "recommendation_rejected",
                {"iteration": iteration, "reason": rejection_feedback},
            )

        initial_detection = detection_agent.run(
            run_id,
            payload["content"],
            context_feedback=context,
            human_rejection_reason=rejection_feedback,
        )
        context = context_agent.run(run_id, payload, initial_detection, policy_question)
        detection = detection_agent.run(
            run_id,
            payload["content"],
            context_feedback=context,
            human_rejection_reason=rejection_feedback,
        )
        policy = policy_agent.run(
            run_id,
            detection,
            context,
            payload["content_id"],
            payload["user_id"],
            prior_policy=policy,
        )

        if approved is False:
            policy_question = "Human rejected the recommendation; gather more context before another policy pass."
        elif policy["needs_more_context"]:
            policy_question = policy["context_question"]
            trace.event(
                run_id,
                "Orchestrator",
                "policy_requested_more_context",
                {"iteration": iteration, "question": policy_question},
            )
        else:
            break

    iterations_used = iteration
    if approved is True:
        trace.event(run_id, "HumanModerator", "recommendation_approved", {"decision": policy["decision"]})

    final_action = None
    status = "needs_human_review"
    if payload.get("human_review_approved") is True and policy is not None:
        final_action = policy["action"]
        status = "completed"
    elif payload.get("human_review_approved") is False:
        status = "needs_human_review"

    if detection is None or context is None or policy is None:
        raise RuntimeError("Agent workflow did not produce a complete result.")

    return {
        "status": status,
        "detection": detection,
        "context_analysis": context,
        "policy": policy,
        "final_action": final_action,
        "iterations_used": iterations_used,
        "max_iterations": payload["max_iterations"],
    }


def build_app() -> FastAPI:
    trace = TraceLogger(TRACE_FILE)
    app = FastAPI(title="Human-in-the-Loop Harm Detection Agents", version="1.0.0")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/run", response_model=ModerationResponse)
    def run_agents(request: ModerationRequest) -> ModerationResponse:
        run_id = str(uuid.uuid4())
        try:
            compass = CompassClient()
            payload = request_to_payload(request, compass.sample_mode)
            trace.event(run_id, "Orchestrator", "run_started", {"sample_mode": compass.sample_mode})
            result = run_workflow(run_id, payload, compass, trace)
            trace.event(run_id, "Orchestrator", "run_completed", {"status": result["status"]})
            return ModerationResponse(
                run_id=run_id,
                sample_mode=compass.sample_mode,
                trace_file=str(TRACE_FILE),
                **result,
            )
        except HTTPException:
            raise
        except Exception as exc:
            trace.event(run_id, "Orchestrator", "run_failed", {"error": str(exc)})
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    return app


app = build_app()


if __name__ == "__main__":
    uvicorn.run("run:app", host="0.0.0.0", port=8000)
