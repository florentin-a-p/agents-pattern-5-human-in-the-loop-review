- Do not hardcode outputs.
- Implement three agents:
  DetectionAgent
  ContextAnalysisAgent
  PolicyAgent
- Agents must collaborate with at least one feedback loop:
  DetectionAgent detects possible harmful content, gives initial confidence score
  ContextAnalysisAgent checks conversation history, sarcasm, previous messages, user relationships, cultural/context clues then sends feedback back to DetectionAgent 
  PolicyAgent decides allow, warn, remove, suspend. But sometimes it may need more context again. Then it asks Agent 2 again.
- Human reviews final recommendation, approves or rejects. if rejected, workflow loops back again 
- Save JSONL trace logs to logs/agent_trace.jsonl.
- Also print important trace events to stdout.
- Include retry handling and clear error responses.
- Include SAMPLE_MODE=true support using sample input data only, not hardcoded final outputs.
- Include metadata.json using use_case_id "12" as an example.
- Include three input examples and three output examples.

Generate minimal, readable, production-ready code. Avoid unnecessary frameworks.

diagram
```mermaid
flowchart TD
    U[User submits content] --> A1[Agent 1: Detection Agent]

    A1 --> A2[Agent 2: Context Analysis Agent]

    A2 --> A1

    A1 -->|Updated risk assessment| A3[Agent 3: Policy Agent]

    A3 --> A2

    A2 -->|Need more context| A3

    A3 --> H{Human moderator approves?}

    H -- No --> A1
    H -- Yes --> F[Final moderation action]
```
