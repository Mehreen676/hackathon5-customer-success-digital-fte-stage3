# Discovery Log — Customer Success Digital FTE

**Stage:** 1 Prototype
**Author:** Mehreen Asghar

---

## Assumptions Made in Stage 1

| # | Assumption | Risk if Wrong |
|---|---|---|
| A1 | 60% of support tickets are routine and auto-respondable | Lower automation rate → less business value |
| A2 | Channel detection can be explicit in Stage 1 (caller passes channel name) | In production, channel will be inferred from webhook source |
| A3 | Keyword-based triage is sufficient to catch the most important escalation cases | False positives and missed cases in edge scenarios |
| A4 | A flat markdown KB is sufficient for Stage 1 demo purposes | KB quality affects response accuracy — needs vector search in Stage 2 |
| A5 | All customers can be identified by a customer_id in Stage 1 | Guest/anonymous customers add complexity — not handled in Stage 1 |
| A6 | Each message is processed independently (no multi-turn memory in Stage 1) | Conversations with context are a real customer expectation |

---

## Risks Identified

| Risk | Severity | Mitigation |
|---|---|---|
| Keyword triage generates false positives | Medium | Tune keyword lists; replace with LLM in Stage 2 |
| KB coverage gaps — customer asks about uncovered topic | Medium | KB is manually maintained; expand before Stage 2 launch |
| Angry customer receives an AI response that escalates the situation | High | Escalation check always runs first; AI never auto-responds to flagged cases |
| Legal language appears in a harmless context | Low-Medium | Currently causes escalation (conservative choice — preferred to under-escalating) |
| In-memory data lost on restart | Low (Stage 1 only) | Acceptable for prototype; PostgreSQL resolves this in Stage 2 |

---

## Observations from Building Stage 1

**O1: Channel formatting is more impactful than expected.**
The same answer reads very differently across channels. A formal email response pasted into WhatsApp would feel awkward and off-brand. Channel formatting needs to be a first-class concern, not an afterthought.

**O2: Triage must run before KB search.**
Early prototype had KB search running before escalation check. This caused the agent to retrieve refund policy content before realizing it needed to escalate. Correct order is always: identify → triage → KB → respond.

**O3: Escalation responses need warmth.**
Draft escalation responses that simply said "escalated to team" felt cold. Customers want to feel heard. The holding response needs empathy language even when the agent is handing off.

**O4: Mock data quality drives demo quality.**
When the sample tickets were generic, the demo felt unconvincing. Real-sounding customer names, actual product scenarios, and realistic frustration language made the prototype feel credible.

**O5: MCP tool interface design is worth getting right in Stage 1.**
The tool contracts (inputs/outputs) defined in Stage 1 will carry forward to Stage 2 when real Claude API calls are wired in. Sloppy tool design now creates migration work later.

---

## Edge Cases Discovered

| Case | How Stage 1 Handles It | Stage 2 Plan |
|---|---|---|
| Message contains both routine question and escalation trigger | Escalation wins — entire message is escalated | Multi-intent detection; split handling |
| Customer not in the mock store | Guest profile created with no history | CRM lookup; anonymous session handling |
| Non-English message | No match in KB; returns fallback | Language detection + multilingual KB |
| Very short message ("help") | No KB match; returns generic fallback | Ask for clarification flow |
| Repeated same message (3× in 10 min) | Processed independently each time | Dedup logic; auto-escalate on repeat |
| Legal keyword in harmless context ("legal copy") | False positive escalation | NLU context analysis to reduce false positives |

---

## What Was Learned in Stage 1

1. **The agent flow is sound.** The sequence of identify → triage → KB search → format → respond is the right pattern. No major architectural changes needed for Stage 2.

2. **Triage-first is non-negotiable.** Auto-responding to a legal threat or churn-risk message is worse than no response. Escalation must always be the first check.

3. **KB quality > KB quantity.** A small, accurate KB is more useful than a large, inconsistent one. Five great KB articles outperform fifty mediocre ones.

4. **Channel formatting is a product feature.** Customers notice when the response feels right for the channel. It builds trust.

5. **Stage 1 is enough to validate the concept.** A working prototype with realistic mock data is sufficient to prove the idea and identify gaps before investing in Stage 2 integrations.
