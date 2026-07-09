# Architectural Decision Records — ZK-MCP-Server

This file records the key design decisions made during development, the
alternatives considered, and what would change in a production system.
It exists because decisions that "live in your head" provide no value to
a reviewer, a future team-member, or your future self six months later.

---

## ADR-001 — SQLite as the backing database

**Decision**: Use SQLite for the demo database.

**Why**:
- Zero configuration — no separate database server to spin up
- Ships with Python (`sqlite3` in stdlib) — no extra dependencies
- Full PRAGMA introspection support: `PRAGMA table_info()`, `PRAGMA foreign_key_list()`, `PRAGMA index_list()` — the exact mechanism the "zero-knowledge" concept depends on
- The entire database is a single portable file, which makes `--seed` demos and CI trivial
- Foreign key support works with `PRAGMA foreign_keys = ON`

**Alternative considered — PostgreSQL**:  
More realistic for production but requires a running server, credentials,
and network config. That friction would obscure the actual engineering being
demonstrated (the introspection and security pipeline) behind setup noise.

**What changes at scale / in production**:

| Concern | SQLite (current) | Production path |
|---------|-----------------|-----------------|
| Concurrency | Single-writer | PostgreSQL / MySQL with connection pooling (`psycopg2` + `pgBouncer`, or SQLAlchemy async) |
| Schema introspection | `PRAGMA` statements | `information_schema` queries (standard SQL, database-agnostic) |
| Audit log | In-memory list | Dedicated `audit_log` table in the same DB, or an append-only event store |
| DB path config | CLI flag / env var | `DATABASE_URL` env var (12-factor app pattern) |
| Migrations | Manual re-seed | `alembic` migration scripts |

The architecture is database-agnostic by design — only `src/introspector.py`
contains SQLite-specific PRAGMA calls. Swapping the backing database means
replacing ~80 lines in that single file.

---

## ADR-002 — Template-only SQL execution (Zero-Knowledge security)

**Decision**: The LLM never constructs or sees SQL. It calls named tools
with typed parameters; the server resolves those to pre-compiled, immutable
SQL templates.

**Why**:
The threat model for an LLM-facing database interface is different from a
human-facing one. An LLM can be:
- Prompted by a malicious user to attempt injection
- Confused by ambiguous input into constructing dangerous queries
- Used as an attack surface if it has any SQL-construction capability

Template-only execution eliminates the entire class of "LLM constructs bad SQL"
attacks at the architectural level, not just at the sanitization level.

**Alternative considered — allow-listed raw SQL with a sandbox**:  
A regex allow-list on raw SQL would still require parsing SQL, which is
notoriously error-prone (e.g., `SQLGlot`-based validation). Any regex approach
has edge cases. Template-only avoids parsing entirely.

**Alternative considered — read-only DB connection for SELECT, writable for writes**:  
Provides partial protection but still allows arbitrary SELECT (data exfiltration)
and requires maintaining two connections. Template-only is strictly stronger.

**What changes at scale**:
- Templates would be stored in a database table (not in-memory) so they survive restarts
- Templates would be versioned — a `template_version` column enables audit log correlation across deploys
- A template approval workflow (code-review gate) would be added before new templates enter production

---

## ADR-003 — In-memory audit log

**Decision**: Store the audit log in a Python list in the `ZeroKnowledgeValidator` instance.

**Why**:
- Zero additional dependencies
- Fast — no I/O on every query
- Sufficient for demonstrating the audit concept; the `security://audit-log` MCP resource makes it observable

**Limitation**:
The audit log is lost when the server restarts. This is an explicitly accepted
tradeoff for a demo/assessment context.

**What changes at scale / in production**:

```
Option A — SQLite audit table (cheapest production path):
  INSERT INTO _zk_audit_log (timestamp, template_id, params_json, success, error_msg)
  Each query row costs ~microseconds; the table is append-only and indexed by timestamp.

Option B — Structured logging (12-factor):
  Emit each audit event as a structured JSON log line to stderr.
  A log aggregator (Datadog, Loki, CloudWatch Logs) picks it up externally.
  Zero schema management, horizontally scalable.

Option C — Event stream:
  Publish audit events to Kafka / Pub-Sub for downstream consumers
  (alerting, SIEM, analytics). Appropriate if audit data needs to leave the service.
```

For most production use cases, Option B (structured logging) is the right
first step — it requires zero code in the audit path and makes the data
available to whatever observability stack is already in place.

---

## ADR-004 — FastMCP over the raw MCP Python SDK

**Decision**: Use `FastMCP` (the high-level wrapper) rather than building
on the raw `mcp.server.Server` class.

**Why**:
FastMCP provides decorator-based tool/prompt/resource registration and
handles all transport plumbing (stdio, SSE). The alternative — raw JSON-RPC
— would require ~200 lines of boilerplate per transport with no functional benefit.
The core engineering value in this project is the introspection pipeline and
the security layer, not the transport protocol implementation.

FastMCP is the official high-level API per the MCP specification.

---

## ADR-005 — ruff over black + flake8

**Decision**: Use `ruff` as the single linting + formatting tool instead of
the traditional `black` + `flake8` + `isort` trio.

**Why**:
- `ruff` is 10–100× faster than the equivalent `flake8` + plugins
- Single tool, single config block in `pyproject.toml` — no `.flake8`, no `setup.cfg`
- Covers pyflakes (F), pycodestyle (E/W), isort (I), and pyupgrade (UP) rules
- Has become the de-facto standard in new Python projects (2023+)
- No behavior change for a solo project; meaningful DX improvement in CI

---

## ADR-006 — Synchronous SQLite over async

**Decision**: Use the synchronous `sqlite3` stdlib module, not `aiosqlite`.

**Why**:
MCP tools in FastMCP run in a synchronous context by default. SQLite queries
against a local file are fast enough (sub-millisecond for the demo dataset)
that async provides no observable benefit.

**What changes at scale**:
If the server needs to handle concurrent requests (e.g., multiple LLM agents
calling it simultaneously via SSE transport), the right move is:
1. Switch to `aiosqlite` or `databases` for truly async I/O
2. Or switch to PostgreSQL + `asyncpg` and a connection pool

The security layer (`ZeroKnowledgeValidator`) would need its
`validate_and_execute` method converted to `async def` — a mechanical change
with no impact on the security model itself.
