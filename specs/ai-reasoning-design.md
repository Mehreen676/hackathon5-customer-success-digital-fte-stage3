# AI Reasoning Design — Nexora Customer Success Digital FTE (Stage 3)

**Module:** `src/llm/`
**Project Owner:** Mehreen Asghar

---

## Overview

The AI reasoning layer is a **3-tier response strategy** that activates when the rule-based knowledge base cannot answer a customer query. It sits between the KB search step and ticket creation in the agent workflow.

---

## When AI Is Invoked

```
KB Search Result
      │
      ├── matched: True  ──►  Use KB content directly  (Tier 1: KB)
      │
      └── matched: False ──►  Invoke LLM               (Tier 2: AI)
                                      │
                                      ├── LLM responds  ──►  Use LLM content
                                      │
                                      └── LLM fails     ──►  Holding message  (Tier 3: Fallback)
```

---

## 3-Tier Response Strategy

### Tier 1: KB Hit (No LLM Cost)
- Source: `"kb"`
- When: `kb_results["matched"] == True`
- Confidence: ~0.9
- Cost: $0 (no LLM call)
- Channel formatting applied via `format_kb_response()`

### Tier 2: LLM Generation
- Source: `"llm"`
- When: KB miss AND LLM provider configured AND API key present
- Confidence: ~0.75
- Cost: varies by provider (see cost table below)
- System prompt encodes Nexora brand voice and channel guidelines
- Customer context (account tier, VIP status, ticket history) injected into prompt
- Max tokens: channel-aware (email=2400, whatsapp=600, web_form=1200)

### Tier 3: Rule-Based Fallback
- Source: `"fallback"`
- When: KB miss AND (LLM unavailable OR LLM raises exception)
- Confidence: ~0.3
- Cost: $0
- Polite holding message: "We've logged your query, a specialist will follow up"
- Ticket status set to `pending_review` (not `auto-resolved`)

---

## LLM Provider Abstraction

The `LLMClient` class provides a unified interface across providers:

```python
client = LLMClient(provider="anthropic")   # or "openai" or "gemini"
response = client.generate(system_prompt, user_prompt, max_tokens=1024)
# → LLMResponse(content, provider, model, input_tokens, output_tokens, latency_ms)
```

Provider is resolved via:
1. `provider` argument
2. `LLM_PROVIDER` environment variable
3. Default: `"anthropic"`

Model is resolved via:
1. `model` argument
2. `LLM_MODEL` environment variable
3. Provider default (anthropic→claude-sonnet-4-6, openai→gpt-4o-mini, gemini→gemini-1.5-flash)

---

## Prompt Engineering

### System Prompt
Contains:
- Company context (Nexora, products, plans, SLAs)
- Agent role and boundaries
- Knowledge areas (billing, integrations, SSO, etc.)
- Escalation triggers (never answer legal/security/refund-above-policy without escalation)
- **Channel-specific tone** appended based on channel:
  - Email: formal, 150-400 words, "Dear [Name]"
  - WhatsApp: concise, 40-100 words, emoji, "Hi [Name]! 👋"
  - Web Form: balanced, 80-200 words, ticket reference

### User Prompt (KB Miss path)
Contains:
- Customer name
- Channel
- Classified intent
- Optional: recent ticket history (last 5 tickets)
- Optional: customer context (account tier, VIP flag)
- Instruction: answer based on Nexora product knowledge, do not fabricate
- Verbatim customer message appended

---

## Fallback Hierarchy

```
1. KB article match                     → serve KB content
2. LLM available + API key configured   → call LLM
3. LLM unavailable                      → generic holding message
4. LLM throws exception                 → generic holding message
5. Escalation detected (any tier)       → skip all above, escalation path
```

Escalation **always takes priority** over the KB/LLM reasoning chain.

---

## Token Budget Management

| Channel | Max Output Tokens | Rationale |
|---------|------------------|-----------|
| email | 2,400 | ~400 words × 6 tokens/word |
| whatsapp | 600 | ~100 words × 6 tokens/word |
| web_form | 1,200 | ~200 words × 6 tokens/word |

Input tokens (system prompt + context + customer message) typically 300-800 tokens.

---

## Cost Estimation

| Provider | Model | Input ($/1K tokens) | Output ($/1K tokens) | Avg cost / interaction |
|----------|-------|---------------------|---------------------|------------------------|
| Anthropic | claude-sonnet-4-6 | $0.003 | $0.015 | ~$0.003 |
| OpenAI | gpt-4o-mini | $0.00015 | $0.0006 | ~$0.0002 |
| OpenAI | gpt-4o | $0.005 | $0.015 | ~$0.003 |
| Google | gemini-1.5-flash | $0.000075 | $0.0003 | ~$0.0001 |

At 1,000 AI interactions/day: ~$0.20-$3.00/day depending on provider.

---

## Security Considerations

1. **No PII in prompts** — prompts include customer name but not email, phone, payment data
2. **No secrets in prompts** — API keys never passed to LLM context
3. **Prompt injection resistance** — customer message is clearly delimited in the user prompt
4. **Cost controls** — max_tokens enforced per channel to prevent runaway costs
5. **Graceful degradation** — LLM failure never crashes the pipeline; always returns a response

---

## Agents SDK Layer (`agent/`)

In addition to the `src/llm/` reasoning layer, Stage 3 introduces a standalone
**Agents SDK style** agent package at the root `agent/` directory.

### Architecture

This layer mirrors the OpenAI Agents SDK pattern:

```
Real OpenAI Agents SDK          This repo (agent/ package)
───────────────────────         ──────────────────────────
agents.Agent                 →  CustomerSuccessAgent
agents.Runner                →  AgentRunner
agents.function_tool         →  @function_tool (agent/tools.py)
agents.FunctionTool          →  FunctionTool (agent/tools.py)
Runner.run_sync(agent, msg)  →  AgentRunner.run_sync(agent, msg, ctx, db)
```

### How Tools Are Registered

The `@function_tool` decorator wraps a Python function as a `FunctionTool`:

```python
from agent.tools import function_tool
from agent.models import SearchKBInput, SearchKBOutput

@function_tool
def search_knowledge_base(inputs: SearchKBInput, db: Session) -> SearchKBOutput:
    """Search the Nexora knowledge base for articles matching a customer query."""
    result = call_tool("search_kb", query=inputs.query, db=db)
    return SearchKBOutput(matched=result["matched"], ...)
```

At decoration time, the tool is:
1. Wrapped in a `FunctionTool` instance with `name`, `description`, and `input_model`
2. Registered in the module-level `_TOOL_REGISTRY` dict
3. Available via `get_tool(name)` or `list_registered_tools()`

### How Tools Are Called

The `AgentRunner` dispatches tool calls via `_call_tool()`:

```
_call_tool("search_knowledge_base", {"query": "invoice"}, tool_calls=[...])
    ↓
agent.get_tool("search_knowledge_base") → FunctionTool instance
    ↓
FunctionTool.call(inputs_dict, db=session)
    ↓
SearchKBInput(query="invoice")   ← Pydantic validation (raises ValidationError if invalid)
    ↓
search_knowledge_base(validated_input, db=session)
    ↓
call_tool("search_kb", query="invoice", db=session)   ← existing MCP tool
    ↓
SearchKBOutput(matched=True, ...)   → model_dump() → dict
    ↓
ToolCall(tool_name="search_knowledge_base", input={...}, output={...}, success=True)
```

### Agent Pipeline (7 steps)

```
AgentRunner.run(agent, message, context)
    │
    ├── Step 1: get_customer_context     → name, account_tier, is_vip, recent_tickets
    ├── Step 2: detect_escalation        → (escalated, reason, severity)
    ├── Step 3: search_knowledge_base    → (matched, top_topic, top_content)
    ├── Step 4: generate response        → KB-grounded OR LLM OR fallback
    ├── Step 5: create_ticket            → ticket_ref, ticket_id
    ├── Step 6: escalate_issue           → (only if escalated=True)
    └── Step 7: send_channel_response    → delivered=True
    │
    └── AgentResult(
            success, response, channel, customer_id,
            escalated, ticket_ref, kb_used, ai_used,
            tool_calls=[ToolCall×7], response_time_ms
        )
```

### How It Maps to `src/agents/workflow.py`

Both pipelines call the same underlying tools — `agent/` adds typed wrappers:

| Aspect | workflow.py | agent/ |
|--------|------------|--------|
| Tool dispatch | `call_tool("search_kb", ...)` | `FunctionTool.call(SearchKBInput(...))` |
| Input validation | Manual / implicit | Pydantic (ValidationError on bad input) |
| Step recording | Dict keys | `ToolCall` objects in `AgentResult.tool_calls` |
| Result type | Raw dict | `AgentResult` Pydantic model |
| Used by | FastAPI endpoints | Standalone / tests / future integrations |

### Swapping in the Real SDK

If `pip install openai-agents` becomes available:

```python
# Replace in agent/tools.py:
from agents import function_tool, FunctionTool   # real SDK

# Replace in agent/customer_success_agent.py:
from agents import Agent as CustomerSuccessAgent
from agents import Runner as AgentRunner

# Tool functions stay identical — only the decorator/base class changes
```

The Pydantic input models in `agent/models.py` remain unchanged because the
real SDK also uses Pydantic for typed tool inputs.

---

## Future Improvements

| Improvement | Priority | Description |
|-------------|----------|-------------|
| Retrieval-Augmented Generation (RAG) | High | Embed KB articles with vector search (e.g. Chroma) for semantic matching before LLM |
| Few-shot examples | Medium | Add 2-3 example Q&A pairs to system prompt to improve format consistency |
| Fine-tuning | Low | Fine-tune on Nexora support logs once volume is sufficient |
| Response caching | Medium | Cache LLM responses for frequently repeated queries |
| Confidence threshold | Medium | Only use LLM response if confidence > threshold, else escalate |
| Multi-turn context | Medium | Pass recent conversation history to LLM for better follow-up handling |
| Feedback loop | High | Collect agent ratings to improve prompts over time |
