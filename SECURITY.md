# Security Policy

## Zero-Knowledge Security Model

This MCP server enforces a strict **Zero-Knowledge** security model.
The LLM never constructs, sees, or executes arbitrary SQL — ever.

---

## How It Works

### Layer 1 — Template-Only Execution
Only SQL from the pre-generated template registry can execute.
There is no raw SQL endpoint. No exceptions.

### Layer 2 — Parameter Validation
Every parameter is type-checked against the introspected schema
before being passed to any template. Wrong types are rejected.

### Layer 3 — Input Sanitization
A defense-in-depth blocklist catches SQL injection patterns
in parameter values, even though parameterized queries already
prevent injection at the database driver level.

### Layer 4 — Audit Trail
Every database operation is logged with:
- Timestamp
- Template ID
- Parameters used
- Success / failure status

Accessible via the `security://audit-log` MCP resource.

### Layer 5 — No DDL
Only SELECT, INSERT, UPDATE, DELETE are permitted.
No CREATE, DROP, ALTER, or any schema manipulation is possible.

---

## What the LLM Sees vs What It Cannot Do

| The LLM CAN | The LLM CANNOT |
|---|---|
| Call named MCP tools | Write or inject SQL |
| Pass typed parameters | Access the DB directly |
| Read schema resources | Execute arbitrary queries |
| View audit logs | Modify table structure |

---

## Reporting a Vulnerability

If you discover a security issue, please open a GitHub Issue
with the label `[SECURITY]`.

**Do not include exploit code or attack details in public issues.**
Describe the class of vulnerability and we will follow up.

---

## Known Scope Boundary — Transport-Layer Authentication

> This section exists because naming your own gaps is more valuable than hoping
> a reviewer doesn't notice them.

**The MCP transport layer itself has no built-in authentication.**

| Transport | Threat surface | Current status |
|-----------|---------------|----------------|
| `stdio` (default) | Local process only — no network exposure | ✅ Appropriate for Claude Desktop use |
| `sse` (network) | Any client that can reach the port can call tools | ⚠️ Needs auth layer for production |

**What you would add for production SSE deployments:**

1. **API key middleware** — An HTTP middleware layer (e.g., Starlette `BaseHTTPMiddleware`) that checks an `Authorization: Bearer <token>` header on every SSE connection before the MCP handshake. Token stored as an environment variable, not in code.

2. **mTLS (mutual TLS)** — Client and server both present certificates. Appropriate for service-to-service deployments where the LLM agent runs in a controlled environment.

3. **API gateway** — Put an AWS API Gateway, Nginx, or Caddy instance in front of the SSE endpoint. Handles auth, rate limiting, and TLS termination without touching the application code.

**Why it is out of scope here:**

The `stdio` transport (the default and primary use case) communicates via stdin/stdout with a local parent process (Claude Desktop). There is no network socket to authenticate against. Adding network auth infrastructure would add complexity that obscures the actual engineering being demonstrated — the introspection pipeline and the Zero-Knowledge security model.

For any production SSE deployment, option 1 (API key middleware) is the 20-line, no-dependency starting point.