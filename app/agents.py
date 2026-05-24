import json
import os
from typing import Any

from openai import OpenAI

DEFAULT_AGENT_MODEL = os.getenv("AGENT_MODEL", "gpt-4.1")
DEFAULT_REASONING_MODEL = os.getenv("REASONING_MODEL", "gpt-5.1")


class CompassClient:
    """
    Thin wrapper around the OpenAI-compatible Compass endpoint.
    """

    def __init__(self) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL", "https://compass.core42.ai/v1")

        if not api_key and os.getenv("SAMPLE_MODE", "false").lower() != "true":
            raise ValueError(
                "OPENAI_API_KEY is not set. Set your Compass API key as an environment variable."
            )

        self.client = OpenAI(
            api_key=api_key or "sample-mode-key",
            base_url=base_url,
        )

    def chat(
            self,
            model: str,
            system_prompt: str,
            user_prompt: str,
            temperature: float = 0.2,
    ) -> str:
        """
        Calls Compass chat completions.
        """
        response = self.client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content or ""


def safe_json_parse(text: str) -> dict[str, Any]:
    """
    Best-effort JSON parser. If the model returns non-JSON text,
    keep it safely under a raw_text field.
    """
    try:
        return json.loads(text)
    except Exception:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start: end + 1])
            except Exception:
                pass

    return {"raw_text": text}


class PlannerAgent:
    name = "Planner Agent"

    system_prompt = """
    You are the Planner Agent in a multi-agent hackathon prototype.

    Your responsibilities:
    - Understand the user's task.
    - Break it into concrete steps.
    - Identify missing information or risks.
    - Produce a plan that another agent can execute.
    - If given evaluator feedback, revise the plan.

    Return only valid JSON with this schema:
    {
      "objective": "...",
      "steps": ["...", "..."],
      "assumptions": ["...", "..."],
      "risks": ["...", "..."],
      "success_criteria": ["...", "..."],
      "needs_revision_because": "..."
    }
    """

    def __init__(self, compass: CompassClient) -> None:
        self.compass = compass

    def run(
            self,
            task: str,
            context: dict[str, Any],
            evaluator_feedback: str | None = None,
    ) -> dict[str, Any]:
        if os.getenv("SAMPLE_MODE", "false").lower() == "true":
            return {
                "objective": f"Address task: {task}",
                "steps": [
                    "Clarify the requested outcome",
                    "Use available context to generate an initial answer",
                    "Check the answer against success criteria",
                    "Revise if evaluator feedback indicates gaps",
                ],
                "assumptions": ["Running in SAMPLE_MODE without Compass call"],
                "risks": ["Output may be less domain-specific than Compass-generated output"],
                "success_criteria": [
                    "Answer is relevant",
                    "Answer is actionable",
                    "Answer includes caveats and next steps",
                ],
                "needs_revision_because": evaluator_feedback or "",
            }

        user_prompt = {
            "task": task,
            "context": context,
            "evaluator_feedback": evaluator_feedback,
        }
        response = self.compass.chat(
            model=DEFAULT_REASONING_MODEL,
            system_prompt=self.system_prompt,
            user_prompt=json.dumps(user_prompt, ensure_ascii=False),
            temperature=0.1,
        )
        return safe_json_parse(response)


class ExecutorAgent:
    name = "Executor Agent"

    system_prompt = """
    You are the Executor Agent in a multi-agent hackathon prototype.

    Your responsibilities:
    - Execute the Planner Agent's plan.
    - Use the supplied context only.
    - Produce a practical, structured answer.
    - Highlight uncertainties.
    - Do not pretend to have used tools or data that were not provided.

    Return only valid JSON with this schema:
    {
      "answer": "...",
      "evidence_used": ["...", "..."],
      "actions_taken": ["...", "..."],
      "limitations": ["...", "..."],
      "recommended_next_steps": ["...", "..."],
      "confidence": 0.0
    }
    """

    def __init__(self, compass: CompassClient) -> None:
        self.compass = compass

    def run(
            self,
            task: str,
            plan: dict[str, Any],
            context: dict[str, Any],
    ) -> dict[str, Any]:
        if os.getenv("SAMPLE_MODE", "false").lower() == "true":
            revision_note = ""
            if plan.get("needs_revision_because"):
                revision_note = " The revision addresses evaluator feedback."

            return {
                "answer": (
                    f"Sample execution for task: {task}. "
                    "The system created a plan, executed it using available context, "
                    f"and prepared this output for evaluator review.{revision_note}"
                ),
                "evidence_used": list(context.keys()) or ["No external context supplied"],
                "actions_taken": plan.get("steps", []),
                "limitations": [
                    "SAMPLE_MODE is enabled",
                    "No live Compass model response was generated",
                ],
                "recommended_next_steps": [
                    "Disable SAMPLE_MODE",
                    "Run with Compass credentials",
                    "Add use-case-specific tools or datasets",
                ],
                "confidence": 0.8 if plan.get("needs_revision_because") else 0.65,
            }

        user_prompt = {
            "task": task,
            "plan": plan,
            "context": context,
        }
        response = self.compass.chat(
            model=DEFAULT_AGENT_MODEL,
            system_prompt=self.system_prompt,
            user_prompt=json.dumps(user_prompt, ensure_ascii=False),
            temperature=0.2,
        )
        return safe_json_parse(response)


class EvaluatorAgent:
    name = "Evaluator Agent"

    system_prompt = """
    You are the Evaluator Agent in a multi-agent hackathon prototype.

    Your responsibilities:
    - Critique the Executor Agent's output.
    - Decide if the answer satisfies the Planner Agent's success criteria.
    - Identify missing evidence, weak reasoning, or incomplete steps.
    - Decide whether another iteration is required.

    Return only valid JSON with this schema:
    {
      "score": 0.0,
      "passed": true,
      "critique": "...",
      "required_changes": ["...", "..."],
      "target_agent": "Planner Agent | Executor Agent | Final",
      "confidence": 0.0
    }

    Scoring guide:
    - 0.90 to 1.00: Excellent; ready as final.
    - 0.75 to 0.89: Good; acceptable with minor caveats.
    - 0.50 to 0.74: Needs revision.
    - Below 0.50: Major gaps; must revise.
    """

    def __init__(self, compass: CompassClient) -> None:
        self.compass = compass

    def run(
            self,
            task: str,
            plan: dict[str, Any],
            execution: dict[str, Any],
    ) -> dict[str, Any]:
        if os.getenv("SAMPLE_MODE", "false").lower() == "true":
            confidence = float(execution.get("confidence", 0.6))
            passed = confidence >= 0.75
            return {
                "score": confidence,
                "passed": passed,
                "critique": (
                    "Sample evaluator critique. Output is structurally valid, "
                    "but SAMPLE_MODE limits domain-specific depth."
                ),
                "required_changes": []
                if passed
                else [
                    "Add more concrete evidence",
                    "Strengthen the final recommendation",
                ],
                "target_agent": "Final" if passed else "Planner Agent",
                "confidence": confidence,
            }

        user_prompt = {
            "task": task,
            "plan": plan,
            "execution": execution,
        }
        response = self.compass.chat(
            model=DEFAULT_REASONING_MODEL,
            system_prompt=self.system_prompt,
            user_prompt=json.dumps(user_prompt, ensure_ascii=False),
            temperature=0.1,
        )
        parsed = safe_json_parse(response)

        if "passed" not in parsed:
            parsed["passed"] = float(parsed.get("score", 0.0)) >= 0.75

        if "target_agent" not in parsed:
            parsed["target_agent"] = "Final" if parsed["passed"] else "Planner Agent"

        return parsed
