# Human-in-the-Loop Harm Detection Agents

Minimal FastAPI service for harmful-content moderation. It implements exactly three collaborating agents:

- `DetectionAgent` detects possible harmful content and assigns category, confidence, and risk score.
- `ContextAnalysisAgent` reviews conversation history, sarcasm, previous messages, user relationships, detected language, locale, and community type, then feeds context back to detection or policy.
- `PolicyAgent` decides `allow`, `warn`, `remove`, or `suspend`; it can ask the context agent for more context before finalizing.

Important trace events are appended to `logs/agent_trace.jsonl` and printed to stdout.

## Setup

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set Compass credentials unless using sample mode:

```bash
export OPENAI_API_KEY="your_compass_api_key"
export OPENAI_BASE_URL="https://compass.core42.ai/v1"
export COMPASS_MODEL="your_model_name"
```

## Local Run

```bash
SAMPLE_MODE=true python run.py
```

The API runs at `http://localhost:8000`.

## Endpoint Contract

`GET /health` returns `{"status":"ok"}`.

`POST /run`

```json
{
  "content": "You are a worthless loser lol, just kidding after that match.",
  "content_id": "post-2002",
  "user_id": "user-84",
  "conversation_history": [
    {"role": "user-84", "content": "Great game, I cannot believe you missed that shot."},
    {"role": "user-91", "content": "I know, roast me."}
  ],
  "user_relationship": "friends and teammates",
  "detected_language": "en",
  "locale": "en-US",
  "community_type": "sports_chat",
  "human_review_approved": true,
  "human_rejection_reason": null,
  "sample_id": "sample_2",
  "max_iterations": 2
}
```

`content` is required except when `SAMPLE_MODE=true` and `sample_id` points to a file in `input_examples/`.

Response:

```json
{
  "run_id": "uuid",
  "sample_mode": true,
  "status": "completed",
  "detection": {
    "category": "harassment",
    "confidence": 0.81,
    "risk_score": 0.55,
    "signals": ["worthless", "loser"],
    "context_feedback_applied": "Conversation context suggests possible joking or familiar banter."
  },
  "context_analysis": {
    "context_risk_modifier": -0.18,
    "sarcasm_or_joking_likely": true,
    "needs_more_context": false
  },
  "policy": {
    "decision": "warn",
    "needs_more_context": false,
    "user_message": "Your content is live with a warning because it may approach our safety limits."
  },
  "final_action": {
    "content_id": "post-2002",
    "user_id": "user-84",
    "action_type": "warn",
    "user_message": "Your content is live with a warning because it may approach our safety limits."
  },
  "iterations_used": 1,
  "max_iterations": 2,
  "trace_file": "logs/agent_trace.jsonl"
}
```

## Feedback Loops

The workflow follows the requested diagram:

1. User content goes to `DetectionAgent`.
2. `ContextAnalysisAgent` checks context and sends feedback back to `DetectionAgent`.
3. `DetectionAgent` sends the updated risk assessment to `PolicyAgent`.
4. `PolicyAgent` may ask `ContextAnalysisAgent` for more context.
5. A human moderator reviews the final recommendation.
6. If `human_review_approved=false`, the rejection reason loops back to `DetectionAgent`.

`max_iterations` is supplied by the user and caps the number of full agent-to-agent collaboration passes. Each pass runs `DetectionAgent -> ContextAnalysisAgent -> DetectionAgent -> PolicyAgent`. Valid values are `1` through `20`, so callers can request higher loop budgets such as `10` or `15`. If `PolicyAgent` still needs more context, or a human rejects the recommendation, the workflow repeats until the cap is reached. If no human approval is provided, or a human rejects the recommendation and the iteration cap is reached, the response remains `needs_human_review` and no final action is applied.

Loop-heavy sample:

```bash
curl -s http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{
    "content_id": "post-many-loops",
    "user_id": "user-many-loops",
    "content": "You are an idiot and should shut up.",
    "conversation_history": [
      {"role": "user-many-loops", "content": "This person keeps derailing the thread."}
    ],
    "user_relationship": "strangers in a public discussion",
    "detected_language": "en",
    "locale": "en-US",
    "community_type": "public_forum",
    "max_iterations": 10
  }'
```

## Sample Mode

Set `SAMPLE_MODE=true` to run without Compass. Sample mode loads sample input data from `input_examples/` and applies deterministic local rules; it does not return hardcoded final outputs.

```bash
curl -s http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"sample_id":"sample_1"}'
```

Sample inputs live in `input_examples/`, with representative outputs in `output_examples/`.

## Docker Run

```bash
docker build -t harm-detection-agents .
docker run --rm -p 8000:8000 -e SAMPLE_MODE=true harm-detection-agents
```

With Compass:

```bash
docker run --rm -p 8000:8000 \
  -e OPENAI_API_KEY="$OPENAI_API_KEY" \
  -e OPENAI_BASE_URL="https://compass.core42.ai/v1" \
  -e COMPASS_MODEL="$COMPASS_MODEL" \
  harm-detection-agents
```

## Compass Configuration

The service uses the OpenAI-compatible SDK:

- `OPENAI_API_KEY`: required unless `SAMPLE_MODE=true`
- `OPENAI_BASE_URL`: defaults to `https://compass.core42.ai/v1`
- `COMPASS_MODEL`: model name available in your Compass project

Compass requests retry three times with short backoff and return clear HTTP 500 errors if all attempts fail.

## Limitations

- Sample mode is a deterministic smoke-test path, not a production moderation model.
- The policy table is intentionally small and should be replaced with real platform rules.
- Human review is represented by request fields; this service does not include a reviewer UI or queue.
