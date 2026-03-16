# Database Schema — Customer Success Digital FTE (Stage 2)

**Author:** Mehreen Asghar
**Database:** SQLite (development) / PostgreSQL (production)
**ORM:** SQLAlchemy 2.x with Mapped/mapped_column

---

## Overview

Stage 2 introduces a PostgreSQL-ready relational schema with 7 tables.
SQLite is used in development and testing with zero configuration.
Switch to PostgreSQL by setting the `DATABASE_URL` environment variable.

---

## Tables

### customers

Stores the core customer account record.

| Column       | Type         | Constraints              | Notes                              |
|--------------|--------------|---------------------------|------------------------------------|
| id           | VARCHAR(36)  | PK, NOT NULL              | UUID v4                            |
| external_id  | VARCHAR(50)  | UNIQUE, NOT NULL, INDEX   | Stage 1 IDs: CUST-001, CUST-002   |
| name         | VARCHAR(200) | NOT NULL                  | Customer display name              |
| email        | VARCHAR(200) | NULL                      | Primary email                      |
| account_tier | VARCHAR(50)  | DEFAULT 'starter'         | starter/growth/business/enterprise |
| is_vip       | BOOLEAN      | DEFAULT false             | Enterprise flag for escalation     |
| created_at   | DATETIME(tz) | DEFAULT now()             |                                    |
| updated_at   | DATETIME(tz) | DEFAULT now(), ON UPDATE  |                                    |

---

### customer_identifiers

Maps channel-specific identifiers to customers.
Allows lookup by email, phone number, or session ID.

| Column      | Type         | Constraints       | Notes                          |
|-------------|--------------|-------------------|--------------------------------|
| id          | VARCHAR(36)  | PK                | UUID v4                        |
| customer_id | VARCHAR(36)  | FK customers.id   |                                |
| channel     | VARCHAR(50)  | NOT NULL          | email / whatsapp / web_form    |
| identifier  | VARCHAR(200) | NOT NULL, INDEX   | email address, phone, session  |
| created_at  | DATETIME(tz) | DEFAULT now()     |                                |

---

### conversations

A support conversation thread. One customer can have multiple conversations
across channels.

| Column     | Type         | Constraints       | Notes                          |
|------------|--------------|-------------------|--------------------------------|
| id         | VARCHAR(36)  | PK                | UUID v4                        |
| customer_id| VARCHAR(36)  | FK customers.id   |                                |
| channel    | VARCHAR(50)  | NOT NULL          | email / whatsapp / web_form    |
| status     | VARCHAR(50)  | DEFAULT 'active'  | active / escalated / closed    |
| started_at | DATETIME(tz) | DEFAULT now()     |                                |
| updated_at | DATETIME(tz) | DEFAULT now(), ON UPDATE |                         |

---

### messages

Individual messages within a conversation (customer or agent).

| Column          | Type         | Constraints             | Notes                    |
|-----------------|--------------|--------------------------|--------------------------|
| id              | VARCHAR(36)  | PK                       | UUID v4                  |
| conversation_id | VARCHAR(36)  | FK conversations.id      |                          |
| role            | VARCHAR(20)  | NOT NULL                 | customer / agent         |
| content         | TEXT         | NOT NULL                 | Full message text        |
| channel         | VARCHAR(50)  | NOT NULL                 | Channel at message time  |
| created_at      | DATETIME(tz) | DEFAULT now()            | Ordered by this column   |

---

### tickets

Support ticket with full lifecycle tracking.

| Column               | Type         | Constraints           | Notes                                    |
|----------------------|--------------|-----------------------|------------------------------------------|
| id                   | VARCHAR(36)  | PK                    | UUID v4                                  |
| ticket_ref           | VARCHAR(20)  | UNIQUE, NOT NULL, IDX | Human-readable: TKT-XXXXXXXX             |
| customer_id          | VARCHAR(36)  | FK customers.id       |                                          |
| conversation_id      | VARCHAR(36)  | FK conversations.id, NULL |                                      |
| channel              | VARCHAR(50)  | NOT NULL              | Originating channel                      |
| subject              | VARCHAR(500) | NOT NULL              | Brief subject line                       |
| description          | TEXT         | NOT NULL              | Full message / description               |
| priority             | VARCHAR(20)  | DEFAULT 'low'         | low / medium / high / critical           |
| status               | VARCHAR(50)  | DEFAULT 'open'        | open / escalated / auto-resolved / closed|
| escalated            | BOOLEAN      | DEFAULT false         |                                          |
| escalation_reason    | VARCHAR(100) | NULL                  | refund_request / legal_complaint / etc.  |
| escalation_severity  | VARCHAR(20)  | NULL                  | low / medium / high / critical           |
| assigned_team        | VARCHAR(100) | NULL                  | Billing / Security / Legal / etc.        |
| resolved_at          | DATETIME(tz) | NULL                  | Set on close                             |
| created_at           | DATETIME(tz) | DEFAULT now()         |                                          |
| updated_at           | DATETIME(tz) | DEFAULT now(), ON UPDATE |                                       |

---

### knowledge_base

Searchable knowledge base articles.

| Column     | Type         | Constraints        | Notes                                |
|------------|--------------|--------------------|--------------------------------------|
| id         | VARCHAR(36)  | PK                 | UUID v4                              |
| topic      | VARCHAR(100) | UNIQUE, NOT NULL, IDX | password_reset / billing_invoice / etc. |
| keywords   | TEXT         | NOT NULL           | Comma-separated search keywords      |
| content    | TEXT         | NOT NULL           | Full article text                    |
| category   | VARCHAR(100) | DEFAULT 'general'  | account / billing / integration / etc.|
| active     | BOOLEAN      | DEFAULT true       | Soft delete via active flag          |
| created_at | DATETIME(tz) | DEFAULT now()      |                                      |
| updated_at | DATETIME(tz) | DEFAULT now(), ON UPDATE |                               |

---

### agent_metrics

Performance and outcome tracking for every agent interaction.

| Column            | Type         | Constraints           | Notes                          |
|-------------------|--------------|-----------------------|--------------------------------|
| id                | VARCHAR(36)  | PK                    | UUID v4                        |
| ticket_id         | VARCHAR(36)  | FK tickets.id, NULL   |                                |
| conversation_id   | VARCHAR(36)  | FK conversations.id, NULL |                            |
| channel           | VARCHAR(50)  | NOT NULL              |                                |
| intent            | VARCHAR(100) | NULL                  | billing / account / etc.       |
| escalated         | BOOLEAN      | DEFAULT false         |                                |
| escalation_reason | VARCHAR(100) | NULL                  |                                |
| kb_used           | BOOLEAN      | DEFAULT false         |                                |
| kb_topic          | VARCHAR(100) | NULL                  | Which KB article matched       |
| processing_time_ms| FLOAT        | NULL                  | End-to-end pipeline latency    |
| created_at        | DATETIME(tz) | DEFAULT now()         |                                |

---

## Relationships

```
customers ──< customer_identifiers    (one customer, many channel IDs)
customers ──< conversations           (one customer, many threads)
customers ──< tickets                 (one customer, many tickets)
conversations ──< messages            (one conversation, many messages)
conversations ──< tickets             (one conversation, many tickets)
tickets ──< agent_metrics             (one ticket, one metric record)
conversations ──< agent_metrics
```

---

## Environment Configuration

```bash
# Development (default — no configuration needed)
# DATABASE_URL not set → uses SQLite

# Production (PostgreSQL)
DATABASE_URL=postgresql://user:password@localhost:5432/nexora_support
```

---

## Notes

- All primary keys are UUID v4 strings (compatible with PostgreSQL uuid type)
- All timestamps include timezone information
- Knowledge base seeding is idempotent (safe to run on every startup)
- Customer seeding includes Stage 1 sample customers (CUST-001 through CUST-005)
