# Multi-Agent App Starter Guide

**G42 AGENTATHON | Hack the Future of AI Agents**  
**Builder Resource — Required Reading**

This tutorial shows you how to build a production-ready starter prototype for the G42 Agentathon: a **Planner → Executor ↔ Evaluator** multi-agent application that connects to **Compass**, exposes the mandatory **`POST /run` endpoint on port 8000**, and writes agent collaboration logs to **`/logs/`**.

Use this guide before you start building your final submission. It is designed to help you avoid the most common disqualification issues: missing Compass integration, missing logs, weak “linear pipeline” behaviour, no `/run` endpoint, and hardcoded outputs.

---

## 1. What You Will Build

By the end of this guide, you will have a working multi-agent prototype with:

- **Three distinct agents**
  - **Planner Agent** — decomposes the user task into a plan.
  - **Executor Agent** — performs the work using the plan and available context.
  - **Evaluator Agent** — critiques the output, scores it, and requests revision if needed.
- **Iterative collaboration**
  - The Evaluator can send the system back to the Planner/Executor for refinement.
  - This avoids a weak one-pass `Agent A → Agent B → Agent C` chain.
- **Compass integration**
  - Uses Compass through the OpenAI-compatible API.
  - Reads credentials from environment variables only.
- **Standard hackathon execution interface**
  - FastAPI server on **port 8000**.
  - Mandatory endpoint: **`POST /run`**.
- **Agent logs**
  - JSONL trace file saved under **`logs/`**.
  - Trace entries show delegation, execution, evaluation, retry, and finalisation.
- **Submission-compatible structure**
  - `run.py`
  - `metadata.json`
  - `.env.example`
  - `requirements.txt`
  - `logs/`
  - `input_examples/`
  - `output_examples/`

---

## 2. Why This Pattern Matters

The G42 Agentathon evaluates **true multi-agent collaboration**, not isolated prompts or simple pipelines.

### Weak — Not Acceptable

```text
User Input
   ↓
Agent A
   ↓
Agent B
   ↓
Agent C
   ↓
Final Output
```

Problems:

- No feedback loops.
- No agent critique.
- No retries.
- No shared context.
- Agents behave like prompt wrappers.

### Strong — Expected

```text
User Input
   ↓
Planner Agent
   ↓
Executor Agent
   ↓
Evaluator Agent
   ↙        ↘
Revise      Accept
   ↓          ↓
Planner   Final Output
   ↓
Executor
   ↓
Evaluator
```

Strong signals:

- Agents have distinct roles.
- Evaluator critiques Executor output.
- Planner revises based on evaluator feedback.
- The workflow can branch, retry, or stop early.
- Logs show multiple agent-to-agent interactions.

---

## 3. Minimum Submission Rules This Starter Supports

Your final submission must satisfy the following:

| Requirement | Starter Support |
|---|---|
| Uses Compass | Yes, through `OPENAI_API_KEY` and `OPENAI_BASE_URL` |
| Exposes `POST /run` | Yes |
| Runs on port `8000` | Yes |
| Includes `run.py` | Yes |
| Includes `metadata.json` | Yes |
| Includes `.env.example` | Yes |
| Saves logs to `/logs/` | Yes |
| Shows multi-agent behaviour | Yes |
| Avoids hardcoded outputs | Yes |
| Runs CPU-only | Yes |
| Completes within 15 minutes | Yes, with configurable iteration limit |

---

## 4. Recommended Repository Structure

Create this structure in your project root:

```text
/project-root
│── app/
│   │── __init__.py
│   │── agents.py
│   │── orchestrator.py
│   │── logging_utils.py
│
│── logs/
│   │── .gitkeep
│
│── input_examples/
│   │── example_1.json
│   │── example_2.json
│   │── example_3.json
│
│── output_examples/
│   │── example_1.json
│   │── example_2.json
│   │── example_3.json
│
│── run.py
│── requirements.txt
│── metadata.json
│── .env.example
│── README.md
│── Dockerfile
```

You may add more folders later, such as:

```text
│── data/
│── scripts/
│── tests/
│── docs/
│── run_ui.py
```

But **do not remove the required files**.

---

## 5. Step 1 — Configure Compass

Compass is mandatory for final submissions. It is OpenAI API-compatible, so most OpenAI-based code works by changing only the API key and base URL.

Create a local `.env` file for development:

```bash
OPENAI_API_KEY=your-compass-api-key-here
OPENAI_BASE_URL=https://compass.core42.ai/v1

AGENT_MODEL=gpt-4.1
REASONING_MODEL=gpt-5.1

MAX_AGENT_ITERATIONS=2
SAMPLE_MODE=false
LOG_LEVEL=INFO
```

Your submitted repository must include only `.env.example`, never `.env`.

Create `.env.example`:

```bash
OPENAI_API_KEY=your-compass-api-key-here
OPENAI_BASE_URL=https://compass.core42.ai/v1

AGENT_MODEL=gpt-4.1
REASONING_MODEL=gpt-5.1

MAX_AGENT_ITERATIONS=2
SAMPLE_MODE=false
LOG_LEVEL=INFO
```

### Verify Compass Access

Run:

```bash
curl "$OPENAI_BASE_URL/models" \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

If Compass is configured correctly, you should receive a model list or valid API response.

If you see a quota error, raise it in the **Compass Troubleshooting** channel on genai.works.

---

## 6. Step 2 — Add Dependencies

Create `requirements.txt`:

```txt
fastapi==0.115.6
uvicorn==0.34.0
openai==1.59.6
pydantic==2.10.4
python-dotenv==1.0.1
```

Install locally:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

---

## 7. Step 3 — Define Agent Logging

Logs are required. They prove your system is genuinely multi-agent.

Create `app/logging_utils.py`:

```python
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


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

    text = text.replace(os.environ.get("OPENAI_API_KEY", ""), "[REDACTED]")
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
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
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


def read_trace(run_id: str) -> list[Dict[str, Any]]:
    trace_path = LOG_DIR / f"{run_id}.jsonl"

    if not trace_path.exists():
        return []

    records = []
    with trace_path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    return records
```

### Important Logging Guidance

Do log:

- Agent names.
- Decisions.
- Delegations.
- Critiques.
- Retry count.
- Output summaries.
- Confidence scores.

Do **not** log:

- Compass API keys.
- Private credentials.
- Full sensitive datasets.
- Hidden chain-of-thought reasoning.

Your logs should show **observable collaboration**, not private reasoning text.

---

## 8. Step 4 — Create the Agents

Create `app/agents.py`:

```python
import json
import os
from typing import Any, Dict, List

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


def safe_json_parse(text: str) -> Dict[str, Any]:
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
                return json.loads(text[start : end + 1])
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
        context: Dict[str, Any],
        evaluator_feedback: str | None = None,
    ) -> Dict[str, Any]:
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
        plan: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        if os.getenv("SAMPLE_MODE", "false").lower() == "true":
            return {
                "answer": (
                    f"Sample execution for task: {task}. "
                    "The system created a plan, executed it using available context, "
                    "and prepared this output for evaluator review."
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
                "confidence": 0.65,
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
        plan: Dict[str, Any],
        execution: Dict[str, Any],
    ) -> Dict[str, Any]:
        if os.getenv("SAMPLE_MODE", "false").lower() == "true":
            confidence = float(execution.get("confidence", 0.6))
            passed = confidence >= 0.7
            return {
                "score": confidence,
                "passed": passed,
                "critique": (
                    "Sample evaluator critique. Output is structurally valid, "
                    "but SAMPLE_MODE limits domain-specific depth."
                ),
                "required_changes": [] if passed else [
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
```

---

## 9. Step 5 — Create the Orchestrator

The orchestrator is where multi-agent collaboration happens.

Create `app/orchestrator.py`:

```python
import uuid
from typing import Any, Dict

from app.agents import CompassClient, EvaluatorAgent, ExecutorAgent, PlannerAgent
from app.logging_utils import read_trace, write_trace


class MultiAgentOrchestrator:
    """
    Planner -> Executor -> Evaluator loop.

    This is intentionally not a one-pass linear chain.
    The Evaluator can send feedback back to the Planner,
    causing another planning and execution cycle.
    """

    def __init__(self, max_iterations: int = 2) -> None:
        self.max_iterations = max_iterations
        self.compass = CompassClient()

        self.planner = PlannerAgent(self.compass)
        self.executor = ExecutorAgent(self.compass)
        self.evaluator = EvaluatorAgent(self.compass)

    def run(
        self,
        task: str,
        context: Dict[str, Any] | None = None,
        use_case_id: str | None = None,
    ) -> Dict[str, Any]:
        run_id = str(uuid.uuid4())
        context = context or {}

        write_trace(
            run_id=run_id,
            agent_name="Orchestrator",
            action="start_run",
            input_summary={"task": task, "use_case_id": use_case_id},
            output_summary="Run started",
            target_agent="Planner Agent",
            status="success",
            metadata={"use_case_id": use_case_id},
        )

        evaluator_feedback = None
        final_plan = None
        final_execution = None
        final_evaluation = None

        for iteration in range(1, self.max_iterations + 1):
            retry_count = iteration - 1

            # 1. Planner creates or revises plan.
            plan = self.planner.run(
                task=task,
                context=context,
                evaluator_feedback=evaluator_feedback,
            )
            final_plan = plan

            write_trace(
                run_id=run_id,
                agent_name="Planner Agent",
                action="create_or_revise_plan",
                input_summary={
                    "task": task,
                    "context_keys": list(context.keys()),
                    "evaluator_feedback": evaluator_feedback,
                },
                output_summary=plan,
                target_agent="Executor Agent",
                confidence=None,
                retry_count=retry_count,
                status="success",
                metadata={"iteration": iteration},
            )

            # 2. Executor performs the task using the plan.
            execution = self.executor.run(
                task=task,
                plan=plan,
                context=context,
            )
            final_execution = execution

            write_trace(
                run_id=run_id,
                agent_name="Executor Agent",
                action="execute_plan",
                input_summary={
                    "task": task,
                    "plan_objective": plan.get("objective"),
                    "plan_steps": plan.get("steps"),
                },
                output_summary=execution,
                target_agent="Evaluator Agent",
                confidence=execution.get("confidence"),
                retry_count=retry_count,
                status="success",
                metadata={"iteration": iteration},
            )

            # 3. Evaluator critiques the result.
            evaluation = self.evaluator.run(
                task=task,
                plan=plan,
                execution=execution,
            )
            final_evaluation = evaluation

            write_trace(
                run_id=run_id,
                agent_name="Evaluator Agent",
                action="evaluate_execution",
                input_summary={
                    "task": task,
                    "success_criteria": plan.get("success_criteria"),
                    "execution_confidence": execution.get("confidence"),
                },
                output_summary=evaluation,
                target_agent=evaluation.get("target_agent"),
                confidence=evaluation.get("confidence"),
                retry_count=retry_count,
                status="success",
                metadata={"iteration": iteration},
            )

            # 4. Branch: accept or revise.
            if evaluation.get("passed") is True:
                write_trace(
                    run_id=run_id,
                    agent_name="Orchestrator",
                    action="accept_final_output",
                    input_summary=evaluation,
                    output_summary="Evaluator accepted output",
                    target_agent="Final",
                    confidence=evaluation.get("confidence"),
                    retry_count=retry_count,
                    status="success",
                    metadata={"iteration": iteration},
                )
                break

            evaluator_feedback = evaluation.get("critique", "")
            required_changes = evaluation.get("required_changes", [])

            write_trace(
                run_id=run_id,
                agent_name="Orchestrator",
                action="request_revision",
                input_summary={
                    "critique": evaluator_feedback,
                    "required_changes": required_changes,
                },
                output_summary="Revision requested from Planner Agent",
                target_agent="Planner Agent",
                confidence=evaluation.get("confidence"),
                retry_count=retry_count,
                status="needs_revision",
                metadata={"iteration": iteration},
            )

        trace = read_trace(run_id)

        status = "completed"
        if final_evaluation and not final_evaluation.get("passed"):
            status = "completed_with_caveats"

        return {
            "run_id": run_id,
            "status": status,
            "use_case_id": use_case_id,
            "task": task,
            "final_answer": final_execution,
            "final_plan": final_plan,
            "final_evaluation": final_evaluation,
            "iterations_used": len(
                [
                    item
                    for item in trace
                    if item.get("agent_name") == "Evaluator Agent"
                    and item.get("action") == "evaluate_execution"
                ]
            ),
            "agents": [
                {
                    "name": "Planner Agent",
                    "role": "Decomposes the task and revises plans based on feedback",
                },
                {
                    "name": "Executor Agent",
                    "role": "Executes the plan and creates the candidate output",
                },
                {
                    "name": "Evaluator Agent",
                    "role": "Critiques output and requests revision or accepts final answer",
                },
            ],
            "trace_path": f"logs/{run_id}.jsonl",
            "trace_excerpt": trace[-8:],
        }
```

---

## 10. Step 6 — Expose the Mandatory `/run` Endpoint

Create `run.py` in the project root:

```python
import os
from typing import Any, Dict, Optional

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.orchestrator import MultiAgentOrchestrator


load_dotenv()


class RunRequest(BaseModel):
    use_case_id: Optional[str] = Field(
        default=None,
        description="Use case ID from the 25 official Agentathon problem statements.",
    )
    task: str = Field(
        ...,
        description="The user task or problem to solve.",
        min_length=3,
    )
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Optional structured context, sample data, retrieved evidence, or constraints.",
    )
    max_iterations: Optional[int] = Field(
        default=None,
        ge=1,
        le=5,
        description="Maximum planner-executor-evaluator loops. Keep low to stay within the 15-minute limit.",
    )


class HealthResponse(BaseModel):
    status: str
    compass_configured: bool
    base_url: str
    sample_mode: bool


app = FastAPI(
    title="G42 Agentathon Multi-Agent Starter",
    version="1.0.0",
    description="Planner-Executor-Evaluator multi-agent prototype using Compass.",
)


@app.get("/")
def root() -> Dict[str, str]:
    return {
        "service": "G42 Agentathon Multi-Agent Starter",
        "status": "running",
        "run_endpoint": "POST /run",
    }


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL", "https://compass.core42.ai/v1")
    sample_mode = os.getenv("SAMPLE_MODE", "false").lower() == "true"

    return HealthResponse(
        status="ok",
        compass_configured=bool(api_key),
        base_url=base_url,
        sample_mode=sample_mode,
    )


@app.post("/run")
def run_agents(request: RunRequest) -> Dict[str, Any]:
    """
    Mandatory hackathon execution endpoint.

    Evaluators will call this endpoint programmatically.
    Keep the request/response format stable and documented.
    """
    try:
        max_iterations = request.max_iterations or int(
            os.getenv("MAX_AGENT_ITERATIONS", "2")
        )

        orchestrator = MultiAgentOrchestrator(max_iterations=max_iterations)

        result = orchestrator.run(
            task=request.task,
            context=request.context,
            use_case_id=request.use_case_id,
        )

        return result

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(exc),
                "message": "Agent run failed. Check stdout and logs/ for trace details.",
            },
        )


if __name__ == "__main__":
    uvicorn.run(
        "run:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )
```

---

## 11. Step 7 — Add `metadata.json`

Create `metadata.json`:

```json
{
  "use_case_id": "16",
  "agents": [
    {
      "name": "Planner Agent",
      "role": "Decomposes the task into a structured plan and revises it using evaluator feedback."
    },
    {
      "name": "Executor Agent",
      "role": "Executes the planner's instructions using the provided context and produces the candidate output."
    },
    {
      "name": "Evaluator Agent",
      "role": "Reviews the executor output, scores quality, identifies gaps, and requests revision or finalisation."
    }
  ],
  "tools_used": [
    "fastapi",
    "openai-sdk",
    "compass-api"
  ],
  "data_sources": [
    "runtime user input",
    "optional context field in POST /run"
  ],
  "output_type": "text"
}
```

Update `use_case_id` to match your selected problem statement.

Examples:

| Use Case ID | Problem Statement |
|---:|---|
| 3 | Narrative Detection & Response System |
| 5 | Meeting Intelligence System |
| 12 | Idea-to-Product Automation |
| 16 | Autonomous Research Assistant |
| 18 | Customer Experience Intelligence |
| 22 | Supply Chain Prediction |

---

## 12. Step 8 — Add Input Examples

Create `input_examples/example_1.json`:

```json
{
  "use_case_id": "16",
  "task": "Create a research brief on how multi-agent systems can improve enterprise procurement workflows.",
  "context": {
    "audience": "G42 internal innovation team",
    "desired_output": "structured research brief",
    "constraints": [
      "Keep it practical",
      "Include risks",
      "Include recommended next steps"
    ]
  },
  "max_iterations": 2
}
```

Create `input_examples/example_2.json`:

```json
{
  "use_case_id": "18",
  "task": "Analyse customer feedback themes and recommend three experience improvements.",
  "context": {
    "sample_reviews": [
      "The onboarding process was fast but the support handoff was confusing.",
      "I liked the dashboard, but I could not find billing settings.",
      "The service is powerful, yet setup documentation needs more examples."
    ],
    "desired_output": "prioritised CX improvement plan"
  },
  "max_iterations": 2
}
```

Create `input_examples/example_3.json`:

```json
{
  "use_case_id": "12",
  "task": "Turn this product idea into a first version delivery plan: an internal tool that summarises long policy documents and flags operational risks.",
  "context": {
    "target_users": [
      "policy analysts",
      "operations leaders"
    ],
    "must_include": [
      "MVP scope",
      "agent roles",
      "timeline",
      "risks"
    ]
  },
  "max_iterations": 2
}
```

---

## 13. Step 9 — Run Locally

Start the server:

```bash
source .env
python run.py
```

You should see a server running on:

```text
http://localhost:8000
```

Check health:

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{
  "status": "ok",
  "compass_configured": true,
  "base_url": "https://compass.core42.ai/v1",
  "sample_mode": false
}
```

Run the agents:

```bash
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d @input_examples/example_1.json
```

You should receive a response similar to:

```json
{
  "run_id": "4e54e28d-9f8a-4d8d-bd79-68e84d93d60a",
  "status": "completed",
  "use_case_id": "16",
  "task": "Create a research brief on how multi-agent systems can improve enterprise procurement workflows.",
  "final_answer": {
    "answer": "...",
    "evidence_used": ["..."],
    "actions_taken": ["..."],
    "limitations": ["..."],
    "recommended_next_steps": ["..."],
    "confidence": 0.84
  },
  "final_plan": {
    "objective": "...",
    "steps": ["..."],
    "assumptions": ["..."],
    "risks": ["..."],
    "success_criteria": ["..."]
  },
  "final_evaluation": {
    "score": 0.84,
    "passed": true,
    "critique": "...",
    "required_changes": [],
    "target_agent": "Final",
    "confidence": 0.84
  },
  "iterations_used": 1,
  "agents": [
    {
      "name": "Planner Agent",
      "role": "Decomposes the task and revises plans based on feedback"
    },
    {
      "name": "Executor Agent",
      "role": "Executes the plan and creates the candidate output"
    },
    {
      "name": "Evaluator Agent",
      "role": "Critiques output and requests revision or accepts final answer"
    }
  ],
  "trace_path": "logs/4e54e28d-9f8a-4d8d-bd79-68e84d93d60a.jsonl",
  "trace_excerpt": []
}
```

---

## 14. Step 10 — Inspect Agent Logs

After a run, check the `logs/` folder:

```bash
ls logs/
```

Open the trace file:

```bash
cat logs/<run_id>.jsonl
```

A strong trace should include events like:

```json
{
  "agent_name": "Planner Agent",
  "action": "create_or_revise_plan",
  "target_agent": "Executor Agent",
  "retry_count": 0,
  "status": "success"
}
```

```json
{
  "agent_name": "Executor Agent",
  "action": "execute_plan",
  "target_agent": "Evaluator Agent",
  "retry_count": 0,
  "status": "success"
}
```

```json
{
  "agent_name": "Evaluator Agent",
  "action": "evaluate_execution",
  "target_agent": "Planner Agent",
  "retry_count": 0,
  "status": "success"
}
```

```json
{
  "agent_name": "Orchestrator",
  "action": "request_revision",
  "target_agent": "Planner Agent",
  "retry_count": 0,
  "status": "needs_revision"
}
```

```json
{
  "agent_name": "Planner Agent",
  "action": "create_or_revise_plan",
  "target_agent": "Executor Agent",
  "retry_count": 1,
  "status": "success"
}
```

This is the kind of evidence judges and automated validators look for.

---

## 15. Step 11 — Add Output Examples

After running your three input examples, save representative outputs.

For example:

```bash
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d @input_examples/example_1.json \
  > output_examples/example_1.json
```

Repeat:

```bash
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d @input_examples/example_2.json \
  > output_examples/example_2.json

curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d @input_examples/example_3.json \
  > output_examples/example_3.json
```

Your final submission must include at least:

```text
input_examples/example_1.json
input_examples/example_2.json
input_examples/example_3.json

output_examples/example_1.json
output_examples/example_2.json
output_examples/example_3.json
```

---

## 16. Step 12 — Add Docker Support

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p logs

EXPOSE 8000

CMD ["python", "run.py"]
```

Build:

```bash
docker build -t g42-agentathon-starter .
```

Run:

```bash
docker run --rm \
  -p 8000:8000 \
  -e OPENAI_API_KEY="$OPENAI_API_KEY" \
  -e OPENAI_BASE_URL="https://compass.core42.ai/v1" \
  -e AGENT_MODEL="gpt-4.1" \
  -e REASONING_MODEL="gpt-5.1" \
  g42-agentathon-starter
```

Test:

```bash
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d @input_examples/example_1.json
```

---

## 17. How to Adapt This Starter to Your Use Case

This starter is intentionally generic. To make it competitive, adapt it to your selected problem statement.

### Option A — Rename the Agents

For example, if you choose **Use Case 18: Customer Experience Intelligence**, you may rename:

| Starter Agent | Use-Case-Specific Agent |
|---|---|
| Planner Agent | Journey Analysis Planner |
| Executor Agent | Feedback Insight Agent |
| Evaluator Agent | CX Quality Reviewer |

If you choose **Use Case 22: Supply Chain Prediction**:

| Starter Agent | Use-Case-Specific Agent |
|---|---|
| Planner Agent | Supply Risk Planner |
| Executor Agent | Disruption Analysis Agent |
| Evaluator Agent | Mitigation Review Agent |

### Option B — Add Specialist Agents

You can add more agents as long as collaboration remains clear.

Example for **Narrative Detection & Response System**:

```text
Media Monitor
   ↓
Narrative Classifier
   ↓
Strategy Planner
   ↓
Response Writer
   ↓
Evaluator
   ↘ revision request back to Strategy Planner or Response Writer
```

Example for **Meeting Intelligence System**:

```text
Transcriber
   ↓
Action Extractor
   ↓
Decision Tracker
   ↓
Summary Reviewer
   ↘ requests clarification from Action Extractor
```

Example for **Legal Intelligence**:

```text
Clause Extractor
   ↓
Risk Analyzer
   ↓
Compliance Checker
   ↓
Legal Summary Evaluator
   ↘ sends weak clauses back to Clause Extractor
```

### Option C — Add Tools

Useful tools include:

- Public APIs.
- Local CSV or JSON files.
- RAG over documents.
- Vector search with FAISS.
- Domain-specific scoring functions.
- Lightweight statistical models.
- Rule-based validators.

Make sure any tool use is:

- Automated.
- Documented.
- CPU-compatible.
- Robust to failure.
- Complete within 15 minutes.

---

## 18. Strong Collaboration Patterns You Can Add

Use one or more of these patterns to strengthen your submission.

### Pattern 1 — Evaluator-Driven Retry

```text
Executor produces output
Evaluator identifies missing evidence
Planner revises plan
Executor reruns with revised plan
Evaluator accepts
```

Best for:

- Research assistants.
- Legal intelligence.
- Procurement intelligence.
- Customer experience intelligence.

### Pattern 2 — Specialist Escalation

```text
Executor detects high-risk issue
Orchestrator routes to Risk Agent
Risk Agent annotates output
Evaluator checks final quality
```

Best for:

- Healthcare diagnostics.
- Cybersecurity intelligence.
- Investment and M&A intelligence.
- Policy impact simulation.

### Pattern 3 — Shared Memory

```text
Planner writes assumptions to shared state
Executor writes findings
Evaluator writes critique
Planner reads critique and updates state
```

Best for:

- Multi-step workflows.
- Long-running analysis.
- Systems with multiple evidence sources.

### Pattern 4 — Confidence-Based Branching

```text
If confidence >= 0.80:
    finalise
Else:
    retry or escalate
```

Best for:

- Forecasting.
- Diagnostics.
- Risk analysis.
- Recommendation systems.

### Pattern 5 — Human-in-the-Loop Review

```text
Evaluator flags low-confidence output
System returns "needs_human_review"
Human can approve, reject, or add context
```

Best for:

- Legal.
- Healthcare.
- Finance.
- Security.

---

## 19. Required `/run` Request and Response Design

Your `/run` endpoint should be easy for automated evaluators to call.

### Recommended Request

```json
{
  "use_case_id": "16",
  "task": "Create a research brief on agentic AI adoption risks.",
  "context": {
    "audience": "enterprise AI leadership",
    "constraints": ["practical", "risk-aware", "actionable"]
  },
  "max_iterations": 2
}
```

### Recommended Response

```json
{
  "run_id": "uuid",
  "status": "completed",
  "use_case_id": "16",
  "task": "...",
  "final_answer": {},
  "final_plan": {},
  "final_evaluation": {},
  "iterations_used": 2,
  "agents": [
    {
      "name": "Planner Agent",
      "role": "..."
    }
  ],
  "trace_path": "logs/<run_id>.jsonl",
  "trace_excerpt": []
}
```

### Response Status Values

Use clear status values:

| Status | Meaning |
|---|---|
| `completed` | Evaluator accepted the output |
| `completed_with_caveats` | Max iterations reached but output returned with caveats |
| `failed` | Unrecoverable error |
| `needs_human_review` | Optional status for sensitive or low-confidence cases |

---

## 20. Compass Best Practices for Multi-Agent Apps

### Use GPT-4.1 for Most Agent Tasks

Recommended for:

- Planning.
- Summarisation.
- Extraction.
- Classification.
- Drafting.
- Review.

```bash
AGENT_MODEL=gpt-4.1
```

### Use GPT-5.1 Selectively

Recommended for:

- Complex reasoning.
- Evaluation.
- Multi-step planning.
- High-risk decisions.

```bash
REASONING_MODEL=gpt-5.1
```

### Keep Inputs Small During Development

Agent systems can consume tokens quickly. During development:

- Use small examples.
- Limit iterations.
- Avoid sending full datasets into prompts.
- Summarise retrieved data before passing it between agents.
- Use `max_iterations=1` while debugging.
- Increase to `2` or `3` for final demo runs.

### Handle Quota Errors Gracefully

Compass quota error:

```text
You have reached the limit of your current subscription quota.
For information on your subscription limits or to expand your quota,
please contact compass.support@core42.ai
```

If this happens:

1. Reduce input size.
2. Reduce iterations.
3. Use GPT-4.1 instead of GPT-5.1 for non-critical calls.
4. Retry later.
5. Raise the issue in the Compass Troubleshooting channel if blocking.

---

## 21. Avoid These Common Mistakes

### Mistake 1 — Linear Pipeline Only

Bad:

```text
Planner → Executor → Evaluator → Done
```

Better:

```text
Planner → Executor → Evaluator
              ↑         ↓
              └ Revision
```

### Mistake 2 — No Agent Logs

If your system does not save logs, reviewers cannot verify collaboration.

Minimum:

```text
logs/<run_id>.jsonl
```

Each line should show one agent action.

### Mistake 3 — Hardcoded Outputs

Do not return canned answers based on sample inputs. Evaluators may inject synthetic inputs.

Bad:

```python
if task == "example":
    return "prewritten answer"
```

Good:

```python
result = orchestrator.run(task=task, context=context)
return result
```

### Mistake 4 — Committed API Keys

Never commit:

```text
.env
*.pem
api_keys.json
credentials.json
```

Only commit:

```text
.env.example
```

### Mistake 5 — UI Without API

A UI is optional. The API is mandatory.

You must have:

```text
POST /run on port 8000
```

Even if you also provide:

```text
UI on port 8001
```

### Mistake 6 — Too Many Iterations

Multi-agent loops are good, but uncontrolled loops are dangerous.

Bad:

```python
while True:
    run_agents()
```

Good:

```python
for iteration in range(max_iterations):
    run_agents()
```

Keep execution within the **15-minute limit**.

---

## 22. Production-Ready Enhancements

Once the starter works, improve it with the following.

### Add Timeouts

Protect the `/run` endpoint from long-running calls.

```python
MAX_AGENT_ITERATIONS=2
```

You can also add request-level timeout logic if your tools call external APIs.

### Add Tool Failure Handling

If your agent uses public APIs:

```python
try:
    data = call_public_api()
except Exception:
    data = load_cached_sample()
```

Log the fallback:

```json
{
  "agent_name": "Data Agent",
  "action": "fallback_to_sample_data",
  "status": "recovered"
}
```

### Add Domain Validators

For example:

- Finance: check that numbers sum correctly.
- Legal: check required clauses are present.
- Healthcare: add safety caveats.
- Cybersecurity: classify severity.
- Research: require citations or source IDs.

### Add RAG

For document-heavy use cases:

- Use `text-embedding-3-large` via Compass.
- Store vectors in FAISS.
- Retrieve top relevant chunks.
- Pass only summaries to agents.

### Add Human Review

For sensitive domains:

```json
{
  "status": "needs_human_review",
  "reason": "Low confidence on high-risk recommendation"
}
```

---

## 23. README Checklist for This Starter

Your `README.md` should include:

```markdown
# Project Title

## Problem Statement
Use Case ID:
Problem:

## Agent Architecture
- Planner Agent:
- Executor Agent:
- Evaluator Agent:

## Collaboration Flow
Explain the feedback loop and retry behaviour.

## Compass Integration
Environment variables:
- OPENAI_API_KEY
- OPENAI_BASE_URL

## How to Run Locally
python run.py

## How to Run with Docker
docker build -t submission .
docker run -p 8000:8000 -e OPENAI_API_KEY=xxx -e OPENAI_BASE_URL=https://compass.core42.ai/v1 submission

## API
POST /run

## Example Input
...

## Example Output
...

## Logs
Logs are saved to logs/<run_id>.jsonl

## Limitations
...

## Future Work
...
```

---

## 24. Final Pre-Submission Checklist

Before submitting, verify:

### Required Files

- [ ] `run.py`
- [ ] `requirements.txt`
- [ ] `metadata.json`
- [ ] `.env.example`
- [ ] `README.md`
- [ ] `logs/`
- [ ] `input_examples/` with at least 3 examples
- [ ] `output_examples/` with at least 3 examples
- [ ] `Dockerfile` recommended

### API

- [ ] Server runs on port `8000`
- [ ] `POST /run` works
- [ ] `/health` works
- [ ] Execution completes within 15 minutes

### Compass

- [ ] Uses `OPENAI_API_KEY`
- [ ] Uses `OPENAI_BASE_URL=https://compass.core42.ai/v1`
- [ ] No non-Compass model in final submitted version
- [ ] No API keys committed

### Multi-Agent Behaviour

- [ ] At least 2 agents
- [ ] Distinct agent roles
- [ ] Logs show agent-to-agent interaction
- [ ] Evaluator critiques or validates output
- [ ] Workflow includes retry, branching, or feedback loop
- [ ] Not just a linear one-pass chain

### Logs

- [ ] Logs saved in `logs/`
- [ ] Logs printed to stdout or accessible in files
- [ ] Logs show planner, executor, evaluator actions
- [ ] Logs include retry count and target agent
- [ ] Logs do not expose secrets

---

## 25. What a Strong Final Version Looks Like

A strong submission based on this starter will:

- Use Compass correctly.
- Solve one of the 25 official problem statements.
- Have meaningful, specialised agents.
- Show at least one feedback loop.
- Use real or realistic data.
- Include clear agent traces.
- Handle errors and retries.
- Return useful outputs through `/run`.
- Explain architecture clearly in `README.md`.
- Avoid over-relying on UI polish.

Remember:

> This hackathon is about **systems, not prompts**.  
> Focus on **collaboration, not isolated automation**.  
> Build for **impact, not novelty alone**.