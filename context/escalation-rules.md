# Escalation Rules — Customer Success Digital FTE

These rules define when the AI agent must stop and hand off to a human agent.
The agent checks these triggers BEFORE attempting to generate an auto-response.

---

## Rule 1: Refund Request

**Trigger keywords:** refund, money back, reimburse, charge back, return my money, I want my money

**Action:** Flag for human review. Do NOT auto-approve or deny.

**Why:** Refund decisions require checking account history, payment records, and policy eligibility. Automated refund denials increase churn risk.

**Response template before escalation:**
> "Thank you for reaching out. I've flagged your refund request and a member of our billing team will review and respond within 1 business day."

**Priority:** MEDIUM

---

## Rule 2: Pricing Negotiation

**Trigger keywords:** negotiate, discount, cheaper, competitor price, match price, better deal, reduce price, lower rate

**Action:** Route to Sales / Account Management team.

**Why:** Price exceptions and custom deals require approval from Sales. The support agent should never commit to pricing changes.

**Response template before escalation:**
> "I've passed your request to our account team, who can discuss plan options with you. Expect a reply within 1 business day."

**Priority:** MEDIUM

---

## Rule 3: Legal Complaint or Threat

**Trigger keywords:** lawsuit, legal action, attorney, lawyer, sue, litigation, court, file a complaint, regulatory, GDPR breach, data breach

**Action:** Immediate escalation to Customer Success Manager and Legal team.

**Why:** Any legal language — even informal — requires human judgment and legal awareness. Automated responses to legal threats can be used against the company.

**Response template before escalation:**
> "I've escalated your message to our customer success team immediately. A senior team member will contact you within 2 hours."

**Priority:** HIGH — do not auto-respond with KB content

---

## Rule 4: Angry or Distressed Customer

**Trigger keywords:** unacceptable, outraged, furious, disgusting, terrible, worst, pathetic, I'm done, fed up, completely disappointed, waste of money

**Action:** Escalate with empathy note. Human agent should open with acknowledgment, not solution.

**Why:** Angry customers need to feel heard before they can receive solutions. An AI response to an emotional message often makes the situation worse.

**Response template before escalation:**
> "I'm really sorry to hear about your experience. I've flagged this as a priority and a team member will be in touch shortly to make this right."

**Priority:** MEDIUM-HIGH

---

## Rule 5: VIP / Enterprise Account Complaint

**Trigger:** Customer is tagged as Enterprise or VIP tier in their profile AND the message contains any complaint or cancellation signal.

**Action:** Immediate escalation to assigned Account Manager.

**Why:** Enterprise accounts represent high revenue. Any churn risk must be handled personally and promptly.

**Priority:** HIGH

---

## Rule 6: Security or Data Issue

**Trigger keywords:** hacked, unauthorized access, data breach, my account was accessed, someone logged in, stolen data, privacy violation, leak

**Action:** Immediate escalation to Security team AND Customer Success Manager. Log incident.

**Why:** Security incidents have legal and regulatory implications. They must never be handled by automated responses.

**Response template before escalation:**
> "I've flagged this as a security priority. Our security team has been notified and will contact you immediately. Please change your password now as a precaution."

**Priority:** CRITICAL

---

## Non-Escalation Cases (Auto-Respond OK)

The following categories do NOT require escalation and the agent can respond automatically:

- Password reset instructions
- How-to questions (feature questions)
- Billing FAQ (how to find invoice, change payment method)
- Integration how-to (connect Slack, Google Workspace)
- Account setup questions
- Plan feature comparison
- Data export instructions

---

## Escalation Severity Scale

| Severity | Action | Response Time |
|---|---|---|
| CRITICAL | Security / Legal | Immediately |
| HIGH | Legal / Enterprise VIP | Within 2 hours |
| MEDIUM-HIGH | Angry customer | Within 4 hours |
| MEDIUM | Refund / Pricing | Within 1 business day |
| LOW | General inquiry | Auto-respond |
