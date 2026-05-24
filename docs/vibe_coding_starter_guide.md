# Vibe Coding Starter Guide

G42 AGENTATHON | Hack the Future of AI Agents

This guide helps beginner and intermediate builders use AI coding tools such as **Cursor**, **Claude Code**, and **GitHub Copilot** to move from idea to working prototype quickly — without producing fake demos, hardcoded outputs, or non-compliant submissions.

Use this guide if you want to:

- Scaffold a working multi-agent app fast
- Connect your app to **Compass**, the mandatory LLM platform
- Build a compliant `/run` API on port `8000`
- Generate useful logs that prove real multi-agent collaboration
- Use AI coding assistants safely and productively
- Avoid common disqualification mistakes

---

## 1. What “Vibe Coding” Means for the Agentathon

“Vibe coding” means using AI coding tools as a fast pair-programmer: you describe what you want, let the tool draft code, then you inspect, test, correct, and harden the result.

For this hackathon, vibe coding is allowed and encouraged — but your final submission must still be a real working system.

### Allowed

You may use AI coding tools to help with:

- Project scaffolding
- FastAPI endpoint creation
- Agent orchestration code
- Prompt design
- Debugging errors
- Test generation
- README writing
- Dockerfile creation
- Architecture documentation
- Log formatting
- Refactoring

### Not Allowed

You must not submit:

- Hardcoded outputs
- Fake “agent” responses that do not call Compass or real logic
- A single prompt wrapped as multiple “agents”
- A linear A → B → C pipeline with no feedback loop
- Runtime use of non-Compass LLMs
- API keys committed to GitHub
- Manual setup steps that judges cannot reproduce

> **Non-negotiable:** Your submitted agent must connect to Compass. Judges will test the Compass integration. Agents that cannot connect to Compass cannot be evaluated or considered for deployment.

---

## 2. The Best Vibe Coding Workflow

Use this loop throughout the build sprint:

```text
Describe → Generate → Inspect → Run → Log → Test → Refine → Document
```

Do not accept generated code blindly. AI coding tools often create code that looks correct but fails under evaluation.

### Recommended Build Loop

1. **Describe the exact requirement**
   - Use case ID
   - Agents and roles
   - Required endpoint
   - Compass integration
   - Logging requirements
   - Submission structure

2. **Generate the smallest working version**
   - Do not ask for the entire final app at once.
   - Start with `run.py`, `/run`, and two or three agents.

3. **Run it immediately**
   - Test locally before adding features.
   - Confirm port `8000` works.

4. **Inspect logs**
   - Confirm agents actually interact.
   - Confirm there are retries, critique, or refinement steps.

5. **Add one feature at a time**
   - Data loading
   - Memory
   - RAG
   - Tool calls
   - UI, if needed

6. **Document as you go**
   - README
   - Architecture diagram
   - Input/output examples
   - Limitations

---

## 3. Mandatory Technical Shape of Your App

Your final repository must follow the standard Agentathon structure.

```text
/project-root
│── app/                # Core agent logic
│── data/               # Optional static datasets, max 500MB
│── scripts/            # Optional helper scripts
│── run.py              # Standard entry point - MANDATORY
│── requirements.txt    # All Python dependencies
│── Dockerfile          # Recommended
│── entrypoint.sh       # Optional
│── run_ui.py           # Optional UI - must use port 8001
│── metadata.json       # Structured metadata - MANDATORY
│── input_examples/     # Minimum 3 sample inputs
│── output_examples/    # Minimum 3 sample outputs
│── logs/               # Agent interaction logs
│── .env.example        # Environment variable template - MANDATORY
│── README.md           # Full setup and run instructions
```

Your app must expose:

```text
POST /run
Port: 8000
```

Optional UI:

```text
Port: 8001
```

Execution must complete within **15 minutes** under standard CPU conditions.

---

## 4. Compass Setup

Compass is Core42’s sovereign AI platform and is mandatory for the final submitted version.

Compass is OpenAI-protocol compatible. Most OpenAI-compatible tools work by changing only:

```bash
OPENAI_API_KEY=<your-compass-api-key>
OPENAI_BASE_URL=https://compass.core42.ai/v1
```

### Local `.env`

Create a local `.env` file. Do **not** commit it.

```bash
OPENAI_API_KEY=your-compass-api-key-here
OPENAI_BASE_URL=https://compass.core42.ai/v1
COMPASS_MODEL=gpt-4.1
COMPASS_REASONING_MODEL=gpt-5.1
EMBEDDING_MODEL=text-embedding-3-large
SAMPLE_MODE=false
```

### `.env.example`

Commit only this safe template:

```bash
OPENAI_API_KEY=
OPENAI_BASE_URL=https://compass.core42.ai/v1
COMPASS_MODEL=gpt-4.1
COMPASS_REASONING_MODEL=gpt-5.1
EMBEDDING_MODEL=text-embedding-3-large
SAMPLE_MODE=false
```

### Verify Compass Connection

```bash
curl "$OPENAI_BASE_URL/models" \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

If this fails, ask for help in the **Compass Troubleshooting** channel on genai.works.

---

## 5. Choose a Simple, Strong Architecture First

Beginner and intermediate teams should avoid overbuilding. A strong simple architecture beats a complex broken one.

Recommended starter pattern:

```text
Planner ↔ Executor ↔ Evaluator
       ↘ Retry / Refine ↗
```

### Example Agent Roles

| Agent | Responsibility |
|---|---|
| Planner Agent | Understands the user request, decomposes the task, decides which data/tools are needed |
| Executor Agent | Performs retrieval, analysis, calculations, or content generation |
| Evaluator Agent | Reviews the executor output, checks quality, flags gaps, requests revisions |

### Why This Pattern Works

It demonstrates real collaboration:

- Planner delegates work
- Executor acts on the plan
- Evaluator critiques the output
- Planner or executor revises based on feedback
- Logs show feedback loops and non-linear flow

This is much stronger than:

```text
Agent A → Agent B → Agent C → Final Answer
```

A simple linear pipeline may fail screening if there is no evidence of meaningful collaboration.

---

## 6. Scaffold a Compliant App with Cursor

Cursor is useful for creating and editing a full codebase with AI assistance.

### Step 1: Open an Empty Folder

```bash
mkdir agentathon-submission
cd agentathon-submission
cursor .
```

### Step 2: Use This Cursor Prompt

Paste this into Cursor Chat:

```text
You are helping me build a G42 Agentathon submission.

Create a Python 3.11 FastAPI multi-agent app with the following mandatory requirements:

- Standard repo structure:
  app/
  data/
  scripts/
  logs/
  input_examples/
  output_examples/
  run.py
  requirements.txt
  Dockerfile
  metadata.json
  .env.example
  README.md

- run.py must start a FastAPI server on port 8000.
- It must expose POST /run.
- The app must use Compass through the OpenAI-compatible SDK:
  OPENAI_API_KEY from environment
  OPENAI_BASE_URL from environment, default https://compass.core42.ai/v1
- Do not hardcode outputs.
- Implement three agents:
  PlannerAgent
  ExecutorAgent
  EvaluatorAgent
- Agents must collaborate with at least one feedback loop:
  Planner creates a plan.
  Executor produces a draft.
  Evaluator critiques the draft.
  Executor revises if the evaluator finds issues.
- Save JSONL trace logs to logs/agent_trace.jsonl.
- Also print important trace events to stdout.
- Include retry handling and clear error responses.
- Include SAMPLE_MODE=true support using sample input data only, not hardcoded final outputs.
- Include metadata.json using use_case_id "12" as an example.
- Include three input examples and three output examples.
- Include a Dockerfile that exposes port 8000 and runs python run.py.
- Include a README with setup, local run, Docker run, endpoint contract, agent roles, limitations, and Compass configuration.

Generate minimal, readable, production-ready code. Avoid unnecessary frameworks.
```

### Step 3: Review What Cursor Generates

Check for these items immediately:

- Does `run.py` actually start a server?
- Is the port `8000`?
- Is `/run` implemented?
- Does the code use `OPENAI_BASE_URL`?
- Are Compass calls real?
- Are outputs generated dynamically from input?
- Are logs written to `/logs/`?
- Are agents clearly named?
- Is there a feedback loop?

### Step 4: Run the App

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export OPENAI_API_KEY=your-compass-api-key
export OPENAI_BASE_URL=https://compass.core42.ai/v1

python run.py
```

In another terminal:

```bash
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "test-001",
    "user_query": "Turn this product idea into a PRD and implementation plan: an AI assistant that summarizes meetings and tracks decisions.",
    "context": {
      "use_case_id": "12"
    }
  }'
```

---

## 7. Scaffold with Claude Code

Claude Code is useful for terminal-based development, repo-wide edits, and debugging.

> Important: Claude Code may use a non-Compass model as a development assistant. That is acceptable for coding help. Your submitted application must not depend on Claude or any non-Compass runtime model.

### Step 1: Initialize the Project

```bash
mkdir agentathon-submission
cd agentathon-submission
git init
claude
```

### Step 2: Use This Claude Code Prompt

```text
Build a minimal but compliant G42 Agentathon starter repo.

Hard constraints:
- Python 3.11
- FastAPI app
- run.py starts API on port 8000
- POST /run endpoint
- Uses Compass via OpenAI-compatible SDK
- Reads OPENAI_API_KEY and OPENAI_BASE_URL from environment
- Default OPENAI_BASE_URL is https://compass.core42.ai/v1
- No hardcoded outputs
- No committed secrets
- CPU-only
- Must finish within 15 minutes
- Must log multi-agent interaction to logs/agent_trace.jsonl

Architecture:
- PlannerAgent creates a task plan from user input
- ExecutorAgent executes the plan using Compass
- EvaluatorAgent critiques the result
- If critique identifies gaps, ExecutorAgent revises once
- Final response includes plan, critique, final answer, confidence, and trace_id

Required files:
- app/agents.py
- app/compass_client.py
- app/tracing.py
- app/schemas.py
- run.py
- requirements.txt
- Dockerfile
- metadata.json
- .env.example
- README.md
- input_examples/example_1.json, example_2.json, example_3.json
- output_examples/example_1.json, example_2.json, example_3.json
- logs/.gitkeep

After creating files, explain how to run and test locally.
```

### Step 3: Ask Claude Code to Add Tests

```text
Add a small tests/ directory with pytest tests that verify:
- metadata.json exists and has required fields
- .env.example exists and contains OPENAI_BASE_URL
- POST /run returns a JSON object
- logs/agent_trace.jsonl is written during a run
- the final output changes when the input query changes
Do not mock the entire agent system in a way that hides broken logic.
```

### Step 4: Ask Claude Code to Check for Disqualification Risks

```text
Review this repository against the G42 Agentathon disqualification checklist.

Check for:
- Missing run.py
- Missing POST /run
- Wrong port
- Missing metadata.json
- Missing .env.example
- API keys committed
- Hardcoded outputs
- No Compass connection
- No multi-agent evidence in logs
- Manual setup steps
- Docker build risks
- Runtime dependency installation
- Data over 500MB

Give me a table of risks and specific fixes.
```

---

## 8. Use GitHub Copilot Effectively

GitHub Copilot is strongest when you write clear comments and function signatures.

### Good Copilot Comment

```python
# Implement a PlannerAgent that:
# - receives a user query and optional context
# - asks Compass GPT-4.1 to produce a JSON plan
# - returns a dict with objective, subtasks, required_tools, and success_criteria
# - raises a clear exception if Compass fails
# - does not return hardcoded content
```

### Poor Copilot Comment

```python
# make planner
```

### Copilot Prompt for Trace Logging

```python
# Write a JSONL trace logger for multi-agent events.
# Each event must include:
# timestamp, trace_id, agent_name, action, input_summary,
# output_summary, target_agent, confidence, retry_count, status.
# Append events to logs/agent_trace.jsonl and also print them to stdout.
```

### Copilot Prompt for Error Handling

```python
# Add robust error handling for Compass API calls:
# - timeout
# - missing API key
# - quota exceeded
# - invalid response JSON
# - retry once with shorter prompt
# Return structured error details without exposing secrets.
```

---

## 9. Minimal Compass Client Pattern

Your app should centralize Compass calls. This makes debugging much easier.

Example `app/compass_client.py`:

```python
import os
from openai import OpenAI

DEFAULT_BASE_URL = "https://compass.core42.ai/v1"


def get_compass_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL", DEFAULT_BASE_URL)

    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Set your Compass API key as an environment variable."
        )

    return OpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=60.0,
        max_retries=1,
    )


def call_compass_chat(
    messages: list[dict],
    model: str | None = None,
    temperature: float = 0.2,
) -> str:
    client = get_compass_client()
    selected_model = model or os.getenv("COMPASS_MODEL", "gpt-4.1")

    response = client.chat.completions.create(
        model=selected_model,
        messages=messages,
        temperature=temperature,
    )

    return response.choices[0].message.content
```

This pattern avoids repeating API setup across agents.

---

## 10. Minimal `/run` Request and Response Contract

Use a simple JSON contract that automated evaluation can call.

### Request Example

```json
{
  "request_id": "example-001",
  "user_query": "Analyze customer reviews and recommend the top three experience improvements.",
  "context": {
    "use_case_id": "18",
    "data_source": "sample_reviews"
  }
}
```

### Response Example

```json
{
  "request_id": "example-001",
  "trace_id": "trace-20260514-001",
  "status": "success",
  "agents_used": [
    "PlannerAgent",
    "ExecutorAgent",
    "EvaluatorAgent"
  ],
  "result": {
    "summary": "The system identified three recurring customer pain points...",
    "recommendations": [
      {
        "priority": 1,
        "recommendation": "Improve response time for support tickets",
        "rationale": "Mentioned in 42% of negative reviews"
      }
    ],
    "confidence": 0.82
  },
  "collaboration": {
    "feedback_loop_completed": true,
    "revision_count": 1,
    "evaluator_findings": [
      "Initial answer lacked prioritization evidence",
      "Executor revised the output with stronger rationale"
    ]
  },
  "log_path": "logs/agent_trace.jsonl"
}
```

---

## 11. What Your Agent Logs Must Prove

Your logs are not just for debugging. Judges and automated validators use them to check whether you built a real multi-agent system.

### Required Trace Fields

Each log event should include:

```json
{
  "timestamp": "2026-05-19T10:30:00Z",
  "trace_id": "trace-abc123",
  "agent_name": "PlannerAgent",
  "action": "create_plan",
  "input_summary": "User asked for CX analysis on customer reviews",
  "output_summary": "Created 4-step plan with sentiment analysis and prioritization",
  "target_agent": "ExecutorAgent",
  "confidence": 0.87,
  "retry_count": 0,
  "status": "success"
}
```

### Strong Log Pattern

```text
PlannerAgent → ExecutorAgent: create analysis plan
ExecutorAgent → EvaluatorAgent: submit draft answer
EvaluatorAgent → ExecutorAgent: critique missing evidence
ExecutorAgent → EvaluatorAgent: submit revised answer
EvaluatorAgent → PlannerAgent: approve final
PlannerAgent → User: final response
```

### Weak Log Pattern

```text
Agent1 ran
Agent2 ran
Agent3 ran
Done
```

The weak pattern does not prove collaboration.

---

## 12. Avoiding Fake Functionality and Hardcoded Outputs

This is one of the most important sections of the guide.

### What Counts as Hardcoded Output?

These are not acceptable:

```python
if user_query == "Analyze customer reviews":
    return {
        "summary": "Customers are unhappy with delivery times.",
        "recommendations": ["Improve delivery", "Add support", "Lower prices"]
    }
```

```python
return "This is a multi-agent analysis with great recommendations."
```

```python
sample_output = open("output_examples/example_1.json").read()
return sample_output
```

```python
# Fake Compass call
def call_llm(prompt):
    return "The answer is generated by AI."
```

### What Is Acceptable?

You may use sample **input data** and sample **datasets** for reproducibility.

Acceptable:

```python
if os.getenv("SAMPLE_MODE") == "true":
    reviews = load_sample_reviews()
else:
    reviews = fetch_public_reviews_or_runtime_input()
```

Not acceptable:

```python
if os.getenv("SAMPLE_MODE") == "true":
    return load_prewritten_final_answer()
```

### Safe Rule

Use sample mode for:

- Sample input data
- Small local CSV files
- Offline fallback data
- Deterministic test fixtures

Do not use sample mode for:

- Prewritten final answers
- Fake agent interaction
- Bypassing Compass
- Pretending external APIs worked

---

## 13. Hardcoded Output Self-Check

Before submission, run these checks.

### Search for Suspicious Returns

```bash
grep -R "return {" app/ run.py
grep -R "return \"" app/ run.py
grep -R "sample_output" .
grep -R "output_examples" app/ run.py
```

These are not automatically wrong, but inspect them carefully.

### Test Different Inputs

Run your app with two different queries:

```bash
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"request_id":"a","user_query":"Create a PRD for a meeting summary app"}'
```

```bash
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"request_id":"b","user_query":"Analyze supplier risk for a procurement decision"}'
```

If both outputs are almost identical, your app may be too generic or hardcoded.

### Ask Your AI Coding Tool to Audit

Use this prompt:

```text
Audit this codebase for hardcoded outputs or fake functionality.

Look for:
- final answers stored in code
- sample outputs returned at runtime
- functions that pretend to call an LLM
- agents that do not use their input
- repeated generic responses
- output_examples used as runtime responses
- if/else branches matching known test prompts
- fake logs that are not tied to actual agent execution

Return a table with file, line, risk, and fix.
```

---

## 14. How to Prompt AI Coding Tools Without Creating Bad Code

The quality of your generated code depends heavily on your prompt.

### Bad Prompt

```text
Build a hackathon winning multi-agent app.
```

This is too broad. It encourages fake complexity.

### Better Prompt

```text
Create a minimal FastAPI app for the G42 Agentathon.

It must:
- expose POST /run on port 8000
- use Compass through OPENAI_API_KEY and OPENAI_BASE_URL
- implement PlannerAgent, ExecutorAgent, EvaluatorAgent
- include one feedback loop where Evaluator critiques Executor and Executor revises
- write JSONL logs for each agent action
- avoid hardcoded outputs
- include Dockerfile, metadata.json, .env.example, README, and sample I/O

Keep the implementation simple and testable.
```

### Best Prompt

```text
We are building use case 18: Customer Experience Intelligence.

Goal:
Analyze customer feedback, identify sentiment and pain points, map journey stages, and recommend prioritized improvements.

Architecture:
- FeedbackAggregator: loads user-provided reviews or sample reviews
- SentimentAgent: classifies sentiment and extracts themes using Compass GPT-4.1
- JourneyMapper: maps themes to customer journey stages
- EvaluatorAgent: checks whether recommendations are specific, evidence-based, and prioritized
- RecommenderAgent: revises recommendations based on evaluator feedback

Hard constraints:
- FastAPI POST /run on port 8000
- Compass only at runtime
- OPENAI_API_KEY and OPENAI_BASE_URL from env
- logs/agent_trace.jsonl with agent-to-agent events
- no hardcoded final outputs
- SAMPLE_MODE can load sample reviews but cannot return prewritten final answers
- CPU-only
- 15-minute max execution
- include error handling for Compass quota failures
- include README and metadata.json

Generate the smallest working implementation first.
```

---

## 15. Debugging with AI Coding Tools

When something breaks, do not paste “it doesn’t work.” Give the tool context.

### Good Debug Prompt

```text
I am building a G42 Agentathon FastAPI app.

Expected:
- python run.py starts server on port 8000
- POST /run calls Compass
- logs are written to logs/agent_trace.jsonl

Actual error:
[paste full traceback]

Relevant files:
[paste run.py]
[paste app/compass_client.py]

Environment:
- Python 3.11
- OPENAI_BASE_URL=https://compass.core42.ai/v1
- OPENAI_API_KEY is set
- OS: macOS/Linux/Windows

Please:
1. Identify the root cause.
2. Provide the minimal code change.
3. Explain how to test the fix.
4. Do not remove Compass integration.
5. Do not replace the agent call with a hardcoded response.
```

### Debugging Compass Quota Errors

If you see:

```text
You have reached the limit of your current subscription quota.
For information on your subscription limits or to expand your quota,
please contact compass.support@core42.ai
```

Do this:

1. Reduce input size.
2. Use `gpt-4.1` for most tasks.
3. Reserve `gpt-5.1` for complex reasoning only.
4. Add retries with backoff.
5. Raise the issue in the **Compass Troubleshooting** channel.
6. Contact `compass.support@core42.ai` if instructed.

Ask your coding tool:

```text
Add graceful handling for Compass quota errors.

Requirements:
- catch API exceptions
- detect quota-related error messages
- retry once after a short delay
- if still failing, return a structured error response
- do not expose API keys
- write the failure to logs/agent_trace.jsonl
```

---

## 16. Building Real Multi-Agent Collaboration

AI coding tools often create agents that are just separate functions. You need collaboration, not just function calls.

### Weak Implementation

```python
plan = planner.run(query)
draft = executor.run(plan)
final = evaluator.run(draft)
return final
```

This is linear. It may not be enough.

### Better Implementation

```python
plan = planner.run(query)

draft = executor.run(plan)

critique = evaluator.review(
    original_query=query,
    plan=plan,
    draft=draft
)

if critique["requires_revision"]:
    revised = executor.revise(
        plan=plan,
        draft=draft,
        critique=critique
    )

    final_review = evaluator.review(
        original_query=query,
        plan=plan,
        draft=revised
    )

    final = planner.prepare_final_response(
        query=query,
        plan=plan,
        result=revised,
        evaluation=final_review
    )
else:
    final = planner.prepare_final_response(
        query=query,
        plan=plan,
        result=draft,
        evaluation=critique
    )
```

This shows:

- Evaluation
- Feedback
- Conditional branching
- Revision
- Role interdependence

### Strong Collaboration Prompt

Use this with your coding assistant:

```text
Refactor my agent flow so it demonstrates real multi-agent collaboration.

Requirements:
- Planner creates plan and success criteria
- Executor produces initial result
- Evaluator critiques result against success criteria
- If quality score is below threshold, Evaluator sends specific revision instructions
- Executor revises the result
- Evaluator performs final review
- Planner synthesizes final answer
- Every handoff is logged with source agent, target agent, action, and summary
- The workflow must branch based on evaluator score
- Do not hardcode evaluator approval
```

---

## 17. Add a Safe Sample Mode

A sample mode helps judges reproduce your app when public APIs fail. It must not fake your final output.

### Good Sample Mode

```python
def load_reviews(input_payload: dict) -> list[str]:
    if input_payload.get("reviews"):
        return input_payload["reviews"]

    if os.getenv("SAMPLE_MODE", "false").lower() == "true":
        return [
            "The app is useful but support takes too long to respond.",
            "Checkout failed twice before my payment worked.",
            "The staff were helpful, but delivery was delayed."
        ]

    raise ValueError("No reviews provided and SAMPLE_MODE is false.")
```

The agents still analyze the reviews dynamically.

### Bad Sample Mode

```python
def run_sample_mode():
    return {
        "summary": "Support is slow and delivery is delayed.",
        "recommendations": ["Improve support", "Improve delivery"]
    }
```

This is a hardcoded output.

---

## 18. Dockerize Early

Do not wait until the final day to add Docker.

### Minimal Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "run.py"]
```

### Build and Run

```bash
docker build -t agentathon-submission .

docker run -p 8000:8000 \
  -e OPENAI_API_KEY="$OPENAI_API_KEY" \
  -e OPENAI_BASE_URL="https://compass.core42.ai/v1" \
  -e COMPASS_MODEL="gpt-4.1" \
  agentathon-submission
```

Test:

```bash
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d @input_examples/example_1.json
```

### Docker Vibe Coding Prompt

```text
Review and fix my Dockerfile for the G42 Agentathon.

Requirements:
- Python 3.11
- CPU-only
- install all dependencies at build time
- no runtime pip install
- expose port 8000
- run python run.py
- keep image simple
- do not copy .env or secrets into the image
- make sure logs/ exists
```

---

## 19. Generate Documentation with AI, Then Verify It

AI tools are excellent for documentation, but they may invent features. Never let your README claim functionality that does not exist.

### README Prompt

```text
Write a README.md for this G42 Agentathon submission.

Include:
- problem statement and use_case_id
- what the app does
- agent roles and responsibilities
- architecture flow
- evidence of multi-agent collaboration
- Compass setup
- local run instructions
- Docker run instructions
- POST /run request and response examples
- input_examples and output_examples explanation
- logs/agent_trace.jsonl explanation
- limitations
- future work

Rules:
- Do not claim features that are not implemented.
- Do not mention non-Compass runtime models.
- Do not include API keys.
- Keep instructions reproducible.
```

### Documentation Audit Prompt

```text
Compare README.md against the actual codebase.

Flag:
- features claimed in README but not implemented
- run commands that will fail
- wrong port numbers
- missing environment variables
- inaccurate agent descriptions
- missing Compass setup
- missing Docker instructions
- any mention of hardcoded or fake outputs

Return exact edits.
```

---

## 20. Generate `metadata.json` Correctly

Your `metadata.json` is mandatory.

Example:

```json
{
  "use_case_id": "18",
  "agents": [
    {
      "name": "FeedbackAggregator",
      "role": "Loads and normalizes user-provided or sample customer feedback"
    },
    {
      "name": "SentimentAgent",
      "role": "Analyzes sentiment and extracts recurring themes using Compass"
    },
    {
      "name": "JourneyMapper",
      "role": "Maps themes and pain points to customer journey stages"
    },
    {
      "name": "EvaluatorAgent",
      "role": "Critiques recommendation quality and requests revisions"
    },
    {
      "name": "RecommenderAgent",
      "role": "Produces prioritized customer experience improvements"
    }
  ],
  "tools_used": [
    "fastapi",
    "openai-sdk",
    "compass-api",
    "python"
  ],
  "data_sources": [
    "input payload",
    "data/sample_reviews.json"
  ],
  "output_type": "text"
}
```

Ask your AI coding tool:

```text
Create a valid metadata.json for this project.

Use the actual agents implemented in app/.
Use the correct G42 Agentathon schema:
- use_case_id
- agents with name and role
- tools_used
- data_sources
- output_type

Do not include extra unsupported fields unless clearly harmless.
```

---

## 21. Create Input and Output Examples

You need at least three input examples and three output examples.

### Input Example

`input_examples/example_1.json`

```json
{
  "request_id": "cx-001",
  "user_query": "Analyze the following customer reviews and recommend improvements.",
  "context": {
    "use_case_id": "18",
    "industry": "retail"
  },
  "reviews": [
    "Checkout was slow and the app crashed during payment.",
    "Customer support was polite but took two days to reply.",
    "Delivery tracking was confusing and inaccurate."
  ]
}
```

### Output Examples

Output examples should be real outputs generated by your app during testing. They should not be used as runtime responses.

Save them after a successful run:

```bash
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d @input_examples/example_1.json \
  > output_examples/example_1.json
```

Repeat for three examples.

---

## 22. Recommended Model Usage

Use Compass models strategically.

| Model | Best Use |
|---|---|
| `gpt-4.1` | Most agent tasks, summarization, classification, structured outputs |
| `gpt-5.1` | Complex reasoning, final evaluation, difficult planning |
| `text-embedding-3-large` | RAG, semantic search, document similarity |
| `whisper-1` | Speech-to-text for audio use cases |

### Practical Advice

- Use `gpt-4.1` by default.
- Use `gpt-5.1` only when the task needs deeper reasoning.
- Keep prompts compact.
- Avoid sending huge raw datasets to the model.
- Summarize or chunk long inputs.
- Cache lightweight processed data where appropriate.
- Use sample data for fallback, not sample outputs.

---

## 23. Common Vibe Coding Mistakes

### Mistake 1: Building the UI First

A polished UI does not compensate for a broken backend.

Build in this order:

```text
/run API → Compass call → agents → logs → Docker → README → optional UI
```

### Mistake 2: Accepting Fake Agent Code

Generated code may create “agents” like this:

```python
class PlannerAgent:
    def run(self, query):
        return "Plan created"
```

This is not enough. Agents must process input and produce meaningful outputs.

### Mistake 3: Forgetting Compass

Some AI coding tools may default to OpenAI’s public API.

Always check:

```python
base_url=os.environ["OPENAI_BASE_URL"]
```

or equivalent framework configuration.

### Mistake 4: No Logs

If your app works but does not log agent interactions, you risk failing collaboration validation.

### Mistake 5: Overbuilding

Do not attempt all of these on day one:

- RAG
- UI
- database
- streaming
- async agents
- external APIs
- multimodal processing
- advanced memory

Start with the required system first.

### Mistake 6: Hardcoding Demo Answers

Judges may inject synthetic inputs. If your output only works for your demo input, it will fail.

---

## 24. AI Tool Prompts You Can Reuse

### Architecture Prompt

```text
Help me design a simple multi-agent architecture for G42 Agentathon use case [ID]: [NAME].

Constraints:
- Minimum 2 agents, preferably 3-5
- Must show true collaboration, not a linear pipeline
- Must expose POST /run on port 8000
- Must use Compass at runtime
- Must finish within 15 minutes
- Must log agent interactions
- Should be feasible for a beginner/intermediate team in 21 build days

Return:
1. Agent list with roles
2. Collaboration flow
3. Data sources
4. Failure handling
5. What to build first
6. What to avoid
```

### Scaffolding Prompt

```text
Generate a minimal working repo for this architecture.

Use:
- Python 3.11
- FastAPI
- OpenAI SDK configured for Compass
- JSONL agent traces
- Dockerfile
- metadata.json
- .env.example
- README
- three input examples

Do not:
- hardcode outputs
- use non-Compass runtime models
- require manual setup
- create unnecessary complexity
```

### Refactoring Prompt

```text
Refactor this code for clarity and compliance.

Goals:
- separate Compass client from agent logic
- make agents testable
- improve error handling
- ensure logs prove multi-agent collaboration
- remove hardcoded final outputs
- preserve POST /run contract
- preserve Compass integration
```

### Testing Prompt

```text
Create practical tests for this Agentathon repo.

Tests should verify:
- /run returns success for valid input
- different inputs produce different outputs
- logs/agent_trace.jsonl is created
- at least three distinct agents appear in logs
- there is at least one evaluator critique event
- metadata.json is valid
- no API keys are present in files
- output_examples are not loaded by runtime code
```

### README Prompt

```text
Write a concise but complete README for this repo.

Do not invent features.
Make the run instructions copy-pasteable.
Include Compass setup and Docker.
Include the endpoint request/response schema.
Explain the agent collaboration loop.
Mention known limitations honestly.
```

### Final Audit Prompt

```text
Perform a final G42 Agentathon compliance audit.

Check:
- run.py exists
- API runs on port 8000
- POST /run exists
- Dockerfile builds
- requirements.txt complete
- .env.example present
- metadata.json valid
- no real API keys committed
- Compass base URL supported
- logs show multi-agent collaboration
- no hardcoded outputs
- input_examples has at least 3 files
- output_examples has at least 3 files
- README run instructions match actual commands
- execution can finish within 15 minutes

Return:
- PASS/FAIL for each item
- exact fix for each failure
```

---

## 25. Final Local Validation Checklist

Before you submit, run through this list.

### Repository

- [ ] `run.py` exists
- [ ] `requirements.txt` exists
- [ ] `metadata.json` exists
- [ ] `.env.example` exists
- [ ] `README.md` exists
- [ ] `logs/` exists
- [ ] `input_examples/` has at least 3 files
- [ ] `output_examples/` has at least 3 files
- [ ] No real `.env` file committed
- [ ] No API keys committed

### API

- [ ] `python run.py` starts server on port `8000`
- [ ] `POST /run` works
- [ ] Response is valid JSON
- [ ] Errors are structured and readable
- [ ] Execution finishes within 15 minutes

### Compass

- [ ] Uses `OPENAI_API_KEY`
- [ ] Uses `OPENAI_BASE_URL`
- [ ] Default base URL is `https://compass.core42.ai/v1`
- [ ] Final submitted version connects to Compass
- [ ] No non-Compass runtime LLM dependency

### Agents

- [ ] Minimum 2 agents
- [ ] Agents have distinct roles
- [ ] Agents exchange information
- [ ] At least one feedback loop exists
- [ ] Evaluator or reviewer critiques another agent
- [ ] Output is revised or approved based on critique
- [ ] Logs show actual collaboration

### Logs

- [ ] Logs written to `logs/agent_trace.jsonl`
- [ ] Logs also printed to stdout or visible during run
- [ ] Logs include agent names
- [ ] Logs include actions
- [ ] Logs include source/target handoffs
- [ ] Logs include statuses
- [ ] Logs are tied to the actual request

### Anti-Hardcoding

- [ ] App does not return prewritten final answers
- [ ] App does not load `output_examples/` at runtime
- [ ] `SAMPLE_MODE` uses sample inputs only
- [ ] Different inputs produce meaningfully different outputs
- [ ] Agents use the user query and context

### Docker

- [ ] Docker build succeeds
- [ ] Docker run exposes port `8000`
- [ ] Dependencies installed at build time
- [ ] No runtime package installation
- [ ] Container does not require GPU
- [ ] Container accepts env vars at runtime

---

## 26. Suggested 12-Day Vibe Coding Plan

### Day 1: Scope

- Choose one problem statement
- Define user, input, and output
- Pick 3-agent architecture
- Create repo structure

### Day 2: Basic API

- Implement FastAPI
- Add `/run`
- Add Compass connection
- Return first dynamic response

### Day 3: Agent Loop

- Add planner, executor, evaluator
- Add feedback loop
- Add JSONL logs

### Day 4: Data

- Add sample input data
- Add public API or dataset integration if needed
- Add `SAMPLE_MODE`

### Day 5: Quality

- Improve prompts
- Add structured outputs
- Add error handling
- Add retries

### Day 6: Docker

- Add Dockerfile
- Test clean build
- Fix dependency issues

### Day 7: Examples

- Create 3 input examples
- Generate 3 real output examples
- Verify outputs are not used by runtime code

### Day 8: README

- Document setup
- Document agents
- Document API
- Document limitations

### Day 9: Testing

- Add simple tests
- Test with different inputs
- Inspect logs

### Day 10: Robustness

- Add timeout handling
- Add quota error handling
- Add fallback sample data
- Reduce token usage

### Day 11: Demo Prep

- Record 2–3 minute demo
- Show live `/run`
- Show logs
- Show final output

### Day 12: Final Audit

- Run compliance checklist
- Rebuild Docker
- Remove secrets
- Submit before deadline

---

## 27. What a Strong Beginner Submission Looks Like

A strong beginner/intermediate submission does not need to be complex. It should be clear, real, and reproducible.

### Strong Submission Characteristics

- Solves one problem statement clearly
- Has a working `/run` API
- Connects to Compass
- Uses 3–5 agents with distinct roles
- Shows evaluator feedback and revision
- Logs agent handoffs clearly
- Uses realistic input data
- Handles errors gracefully
- Has honest documentation
- Runs in Docker
- Avoids fake functionality

### Weak Submission Characteristics

- UI-only demo
- No `/run` endpoint
- No Compass connection
- Hardcoded answer
- Agents are just names in a prompt
- No logs
- No feedback loop
- Broken Docker build
- Missing metadata
- API keys committed to repo

---

## 28. Final Advice

Use AI coding tools aggressively, but stay in control.

The strongest teams will not be the ones that generate the most code. They will be the ones that:

- Scope tightly
- Build a working system early
- Prove real agent collaboration
- Keep Compass integration clean
- Log everything important
- Test with unseen inputs
- Avoid fake demos
- Document honestly

Focus on this:

```text
Working multi-agent system + real Compass calls + clear logs + reproducible submission
```

Not this:

```text
Large codebase + polished UI + fake outputs + no evaluation path
```

Build the smallest real system first. Then improve it.