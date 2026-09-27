# Deployment Guide — Self-Documenting Zero-Knowledge MCP Server

This guide provides end-to-end instructions for deploying, configuring, integrating, and operating the **Self-Documenting Zero-Knowledge MCP Server**. Whether running locally alongside Claude Desktop, deploying as a networked Server-Sent Events (SSE) daemon, or containerizing with Docker, this document outlines best practices, configuration options, and production hardening procedures.

---

## Table of Contents

1. [Local Development Setup](#1-local-development-setup)
2. [Claude Desktop Integration](#2-claude-desktop-integration)
3. [SSE (Network) Deployment](#3-sse-network-deployment)
4. [Testing with MCP Inspector](#4-testing-with-mcp-inspector)
5. [Docker Deployment](#5-docker-deployment)
6. [Environment Variables](#6-environment-variables)
7. [Configuration Options Reference](#7-configuration-options-reference)
8. [Security Considerations for Production](#8-security-considerations-for-production)
9. [Monitoring & Logging](#9-monitoring--logging)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Local Development Setup

### System Prerequisites
- **Python**: Version `3.10` or higher (`3.10`–`3.12` recommended)
- **Git**: Version `2.x+`
- **SQLite3**: Built into Python standard library (`libsqlite3 >= 3.35.0` for full PRAGMA support)
- **Virtual Environment Tool**: `venv` or `virtualenv`

### Step-by-Step Installation

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/Utkarsh-Srivastava29/Self-Documenting-Zero-Knowledge-MCP-Server.git
   cd Self-Documenting-Zero-Knowledge-MCP-Server
   ```

2. **Create and Activate a Virtual Environment**:
   ```bash
   # On macOS/Linux
   python3 -m venv .venv
   source .venv/bin/activate

   # On Windows (cmd.exe)
   python -m venv .venv
   .venv\Scripts\activate.bat

   # On Windows (PowerShell)
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

3. **Install Dependencies**:
   You can install standard runtime requirements:
   ```bash
   pip install -r requirements.txt
   ```
   Or install editable project mode with development and testing dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

4. **Seed the Demo Legacy Database**:
   Generate the sample e-commerce SQLite database (`legacy_store.db`):
   ```bash
   python server.py --seed
   ```
   This creates a database populated with 6 related tables: `categories`, `customers`, `orders`, `order_items`, `products`, and `reviews`.

5. **Start the Server Locally**:
   ```bash
   # Standard I/O transport (default for MCP desktop clients like Claude Desktop)
   python server.py

   # Or run with SSE network transport on custom port
   python server.py --transport sse --port 8080
   ```

> [!NOTE]
> When running with standard I/O (`stdio`), the process listens on stdin and writes JSON-RPC messages to stdout. Do not write arbitrary application prints to stdout as that will corrupt the MCP communication channel.

---

## 2. Claude Desktop Integration

Claude Desktop interacts with MCP servers locally using standard input/output (`stdio`) transport. In this mode, Claude launches the Python process and exchanges structured JSON-RPC messages.

### Configuration File Locations

Find or create your `claude_desktop_config.json` depending on your operating system:

| Platform | Path |
|---|---|
| **macOS** | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| **Windows** | `%APPDATA%\Claude\claude_desktop_config.json` |
| **Linux** | `~/.config/Claude/claude_desktop_config.json` |

### Configuration Example

Add the server definition under the `mcpServers` key. Use the absolute paths to your virtual environment Python binary and database file:

#### macOS / Linux
```json
{
  "mcpServers": {
    "zk-database": {
      "command": "/Users/utkarshsrivastava/Desktop/Self-Documenting-Zero-Knowledge-MCP-Server/.venv/bin/python",
      "args": [
        "/Users/utkarshsrivastava/Desktop/Self-Documenting-Zero-Knowledge-MCP-Server/server.py",
        "--db",
        "/Users/utkarshsrivastava/Desktop/Self-Documenting-Zero-Knowledge-MCP-Server/legacy_store.db"
      ]
    }
  }
}
```

#### Windows
```json
{
  "mcpServers": {
    "zk-database": {
      "command": "C:\\path\\to\\Self-Documenting-Zero-Knowledge-MCP-Server\\.venv\\Scripts\\python.exe",
      "args": [
        "C:\\path\\to\\Self-Documenting-Zero-Knowledge-MCP-Server\\server.py",
        "--db",
        "C:\\path\\to\\Self-Documenting-Zero-Knowledge-MCP-Server\\legacy_store.db"
      ]
    }
  }
}
```

> [!IMPORTANT]
> 1. Always use absolute paths. Shell environment expansion (`~`) may not resolve properly inside Claude Desktop on some platforms.
> 2. Point `command` specifically to the Python binary in your virtual environment (where `mcp` and dependencies are installed).
> 3. Fully restart Claude Desktop after editing `claude_desktop_config.json` for changes to take effect.

---

## 3. SSE (Network) Deployment

Server-Sent Events (SSE) transport enables remote or multi-client access over HTTP. This is ideal when hosting the MCP server inside a private network, a container, or on a remote VM.

### Starting the SSE Server

Run the server with `--transport sse` and optionally define the port:

```bash
python server.py --transport sse --port 8080
```

### Connection Characteristics

- **Protocol**: HTTP / Server-Sent Events (FastMCP SSE transport).
- **Listening Address**: Default binds to `0.0.0.0` or `127.0.0.1` on port `8080`.
- **Endpoints**:
  - SSE connection stream: `http://<host>:8080/sse`
  - Message posting endpoint: negotiated during initial SSE handshake (typically `http://<host>:8080/messages/`).
- **Client Handshake**: MCP SSE clients connect to the SSE endpoint to receive server notifications and POST back JSON-RPC requests.

> [!WARNING]
> FastMCP's built-in SSE transport provides **no authentication or authorization** out of the box. Anyone with network access to the port can execute registered tool operations. Do not expose this port directly to public networks. Refer to [Security Considerations for Production](#8-security-considerations-for-production) for hardening guidance.

---

## 4. Testing with MCP Inspector

The **MCP Inspector** is an interactive, browser-based developer tool designed to test, debug, and inspect MCP servers.

```
+--------------------+        JSON-RPC         +-------------------+
|   MCP Inspector    | <=====================> |     server.py     |
| (Web UI on :5173)  |                         |  (stdio process)  |
+--------------------+                         +-------------------+
```

### Running with the MCP CLI

If `mcp[cli]` was installed from `requirements.txt`:

```bash
# Launch the inspector with stdio transport
mcp dev server.py

# Or pass specific database arguments:
mcp dev server.py --args "--db,/path/to/legacy_store.db"
```

Alternatively, you can run it via `npx`:
```bash
npx @modelcontextprotocol/inspector python server.py
```

### What to Verify in the Inspector

1. **Tools Tab**:
   - Verify auto-generated CRUD tools for all discovered tables (`create_<table_name>`, `read_<table_name>`, `update_<table_name>`, `delete_<table_name>`, `list_<table_name>`, `search_<table_name>`).
   - Run a test query (e.g. `list_customers` with `limit=5`).
2. **Prompts Tab**:
   - Inspect relationship join prompts (`join_orders_and_customers`).
   - Test `explore_database` and `show_schema` prompts.
3. **Resources Tab**:
   - View `schema://tables` for full catalog introspections.
   - Inspect `security://templates` to verify pre-validated template lists.
   - Query `security://audit-log` and `security://report` to confirm activity tracking.

---

## 5. Docker Deployment

Deploying via Docker isolates the execution environment and allows for consistent, portable deployments across Linux servers, Kubernetes, or cloud container services (AWS ECS, GCP Cloud Run, Azure Container Instances).

### Sample Dockerfile

Create a `Dockerfile` in the root of the project:

```dockerfile
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Ensure Python output is unbuffered
ENV PYTHONUNBUFFERED=1
ENV DATABASE_PATH=/app/data/legacy_store.db

# Create non-root user for security
RUN groupadd -r mcpuser && useradd -r -g mcpuser -d /app -s /sbin/nologin mcpuser

# Install system dependencies if required
RUN apt-get update && apt-get install -y --no-install-recommends \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Create directory for persistent database storage and set permissions
RUN mkdir -p /app/data && chown -R mcpuser:mcpuser /app

# Switch to non-root user
USER mcpuser

# Expose SSE network port
EXPOSE 8080

# Default command: launch SSE transport
CMD ["python", "server.py", "--transport", "sse", "--port", "8080", "--db", "/app/data/legacy_store.db"]
```

### Docker Compose Example (`docker-compose.yml`)

Use Docker Compose to manage persistent SQLite volumes and environment settings:

```yaml
version: "3.8"

services:
  zk-mcp-server:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: zk-mcp-server
    restart: unless-stopped
    ports:
      - "127.0.0.1:8080:8080"
    volumes:
      # Mount directory containing database file
      - ./data:/app/data:rw
    environment:
      - DATABASE_PATH=/app/data/legacy_store.db
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8080/sse')"]
      interval: 30s
      timeout: 5s
      retries: 3
```

### Build and Run Commands

```bash
# Prepare data directory
mkdir -p data

# Seed database into the volume mount if needed
python server.py --seed --db data/legacy_store.db

# Build the container image
docker build -t zk-mcp-server:latest .

# Run container with volume mount
docker run -d \
  --name zk-mcp-server \
  -p 127.0.0.1:8080:8080 \
  -v "$(pwd)/data:/app/data" \
  zk-mcp-server:latest

# Or launch with docker compose
docker compose up -d
```

---

## 6. Environment Variables

The server supports configuring database paths via environment variables.

| Variable | Description | Default | Example |
|---|---|---|---|
| `DATABASE_PATH` | Path to the SQLite database file | `./legacy_store.db` | `/var/lib/mcp/production.db` |

### Configuration Precedence Order

When determining which SQLite database to introspect, the server evaluates options in the following order:

```
CLI Flag (--db <path>)
        │  (if not supplied)
        ▼
Environment Variable ($DATABASE_PATH)
        │  (if not set)
        ▼
Default Fallback (./legacy_store.db relative to server.py)
```

Setting `DATABASE_PATH` in `.env` or system environment:
```bash
export DATABASE_PATH="/var/data/custom_store.db"
python server.py
```

---

## 7. Configuration Options Reference

The server exposes command-line flags parsed by `argparse` in `server.py`:

| Flag | Type | Allowed Values | Default | Description |
|---|---|---|---|---|
| `--db` | String | Valid file path | `legacy_store.db` (or `$DATABASE_PATH`) | Path to the target SQLite database file. |
| `--transport` | String | `stdio`, `sse` | `stdio` | MCP communication transport method. Use `stdio` for Claude Desktop; `sse` for network deployments. |
| `--port` | Integer | `1` – `65535` | `8080` | Network port to listen on when using the `sse` transport. |
| `--seed` | Flag | None | `False` | Initializes and seeds the demo database with sample tables and rows prior to starting the server. |

### Example CLI Invocations

```bash
# 1. Quick demo launch with seed data on stdio
python server.py --seed

# 2. Connect to an external legacy database on stdio
python server.py --db /opt/databases/inventory.db

# 3. Host on SSE port 9000 for local network testing
python server.py --db /opt/databases/inventory.db --transport sse --port 9000
```

---

## 8. Security Considerations for Production

As documented in [SECURITY.md](file:///Users/utkarshsrivastava/Desktop/Self-Documenting-Zero-Knowledge-MCP-Server/SECURITY.md), the Zero-Knowledge security model ensures that:
- **No arbitrary SQL** can be executed (pre-validated parameterized templates only).
- **Parameters are strictly typed** against the database schema.
- **SQL injection strings** are proactively filtered via a defense-in-depth sanitization blocklist.
- **DDL statements** (`DROP`, `ALTER`, `CREATE`) are structurally prevented.

However, when hosting the server over a network via SSE, transport-layer safeguards must be added.

### 1. Reverse Proxy & TLS Termination (Nginx / Caddy)

Never expose the plain HTTP SSE port directly to the internet. Deploy a reverse proxy in front of the server to enforce HTTPS (TLS 1.3), rate limiting, and request timeouts.

#### Example Caddy Configuration (`Caddyfile`)
```caddy
mcp.example.com {
    reverse_proxy 127.0.0.1:8080 {
        # Enable streaming support for Server-Sent Events
        flush_interval -1
    }
}
```

#### Example Nginx Configuration (`nginx.conf`)
```nginx
server {
    listen 443 ssl http2;
    server_name mcp.example.com;

    ssl_certificate /etc/letsencrypt/live/mcp.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/mcp.example.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Connection '';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Disable buffering for SSE streams
        proxy_buffering off;
        proxy_cache off;
        chunked_transfer_encoding off;
        proxy_read_timeout 24h;
    }
}
```

### 2. API Key Authentication Layer

To prevent unauthorized clients from initiating tool calls over SSE, add an authentication layer using an API Bearer token.

For example, when wrapping FastMCP with a Starlette / ASGI middleware:
```python
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import os

API_KEY = os.environ.get("MCP_API_KEY")

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Allow internal health checks
        if request.url.path == "/health":
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if not auth_header or auth_header != f"Bearer {API_KEY}":
            return JSONResponse({"error": "Unauthorized"}, status_code=401)

        return await call_next(request)
```

### 3. Least Privilege & Read-Only Mounting

- **Non-Root Execution**: Always execute the server process as an unprivileged system user (`mcpuser`), never as `root`.
- **Read-Only SQLite Storage**: If the MCP server is only intended for querying, inspection, and analysis (no `INSERT`, `UPDATE`, `DELETE`), mount the SQLite database file as read-only:
  ```bash
  # Operating system level
  chmod 444 /path/to/legacy_store.db

  # Docker compose volume mount
  volumes:
    - ./data/legacy_store.db:/app/data/legacy_store.db:ro
  ```
  SQLite will automatically reject any mutating statements at the filesystem and OS kernel level.

---

## 9. Monitoring & Logging

### Standard Error Logging (`stderr`)

The MCP protocol requires `stdout` to be strictly reserved for JSON-RPC framing. All server logs, lifecycle events, and diagnostic outputs are routed to `stderr`.

- **Log Format**: `%(asctime)s [%(levelname)s] %(name)s: %(message)s`
- **Default Logger**: `zk-mcp-server`
- **Output Sample**:
  ```text
  2026-09-27 18:15:01,102 [INFO] zk-mcp-server: Phase 1: Introspecting database schema...
  2026-09-27 18:15:01,118 [INFO] zk-mcp-server: Phase 2: Building schema registry...
  2026-09-27 18:15:01,120 [INFO] zk-mcp-server: Phase 3: Generating pre-validated SQL templates...
  2026-09-27 18:15:01,124 [INFO] zk-mcp-server: Phase 4: Initializing Zero-Knowledge security validator...
  2026-09-27 18:15:01,130 [INFO] zk-mcp-server: Phase 5: Generating CRUD tools for all tables...
  2026-09-27 18:15:01,135 [INFO] zk-mcp-server: Phase 6: Analyzing relationships and generating prompts...
  2026-09-27 18:15:01,138 [INFO] zk-mcp-server: Phase 7: Registering schema resources...
  2026-09-27 18:15:01,140 [INFO] zk-mcp-server: Server ready!
  2026-09-27 18:15:01,140 [INFO] zk-mcp-server: Tables discovered: 6
  2026-09-27 18:15:01,140 [INFO] zk-mcp-server: CRUD tools registered: 36
  2026-09-27 18:15:01,140 [INFO] zk-mcp-server: Prompts registered: 8
  2026-09-27 18:15:01,140 [INFO] zk-mcp-server: SQL templates: 36
  2026-09-27 18:15:01,140 [INFO] zk-mcp-server: Security: Zero-Knowledge mode (template-only execution)
  ```

### Live MCP Security Resources

Clients can programmatically monitor server state and security operations via MCP resources:

1. **`security://audit-log`**:
   Returns the most recent 50 database operations executed by the validator:
   ```json
   [
     {
       "timestamp": "2026-09-27T18:16:42.102Z",
       "template_id": "customers_select_pk",
       "params": {"id": 12},
       "status": "success",
       "row_count": 1,
       "execution_time_ms": 1.45
     }
   ]
   ```

2. **`security://report`**:
   Provides an aggregated summary of query operations, blocked attempts, and validation failures:
   ```json
   {
     "total_queries": 45,
     "successful_queries": 44,
     "failed_queries": 1,
     "blocked_injection_attempts": 1,
     "uptime_seconds": 3600
   }
   ```

3. **`security://templates`**:
   Returns the complete registry of registered, pre-validated SQL templates that the server is permitted to run.

---

## 10. Troubleshooting

> [!TIP]
> For a comprehensive, category-by-category diagnostic guide covering protocol framing, database introspection, security rejections, and Python environments, see [TROUBLESHOOTING.md](file:///Users/utkarshsrivastava/Desktop/Self-Documenting-Zero-Knowledge-MCP-Server/docs/TROUBLESHOOTING.md).

### 1. Database File Not Found
- **Symptom**: Server terminates with `Database not found: <path>`.
- **Cause**: The database path provided in `--db` or `DATABASE_PATH` does not exist on disk.
- **Solution**:
  - Seed the demo database: `python server.py --seed`
  - Or verify the absolute path to your database:
    ```bash
    ls -lh /path/to/legacy_store.db
    ```

### 2. Port Already in Use (`Errno 48 Address already in use`)
- **Symptom**: Running with `--transport sse --port 8080` fails with an address bind error.
- **Cause**: Another process (e.g. an existing server instance or web server) is occupying port 8080.
- **Solution**:
  - Identify the process holding the port:
    ```bash
    # macOS / Linux
    lsof -i :8080
    # Or kill existing process:
    kill $(lsof -t -i :8080)
    ```
  - Or start the server on another port:
    ```bash
    python server.py --transport sse --port 8081
    ```

### 3. Python Version Mismatch
- **Symptom**: `TypeError: unsupported operand type(s) for |` or `SyntaxError`.
- **Cause**: Running with Python version older than `3.10`.
- **Solution**:
  - Check active version:
    ```bash
    python --version
    ```
  - Ensure the virtual environment was created with Python `3.10+`:
    ```bash
    python3.11 -m venv .venv
    source .venv/bin/activate
    ```

### 4. Claude Desktop Shows MCP Server Disconnected / Error
- **Symptom**: Claude Desktop displays a red warning icon next to `zk-database`.
- **Cause**: Path to Python executable or script is invalid, or dependencies are missing in that Python environment.
- **Solution**:
  - In `claude_desktop_config.json`, verify that `command` points directly to the virtual environment's Python binary (e.g., `/Users/.../.venv/bin/python`).
  - Test executing the exact command directly in your terminal to see errors printed to `stderr`:
    ```bash
    /path/to/.venv/bin/python /path/to/server.py --db /path/to/legacy_store.db
    ```
  - Inspect Claude Desktop logs:
    - **macOS**: `~/Library/Logs/Claude/mcp*.log`
    - **Windows**: `%APPDATA%\Claude\logs\mcp*.log`

### 5. Permission Denied on Database File
- **Symptom**: `sqlite3.OperationalError: attempt to write a readonly database` or file open error.
- **Cause**: The user running the server lacks read or write permissions to the SQLite file or parent directory.
- **Solution**:
  - Check file permissions:
    ```bash
    ls -l legacy_store.db
    ```
  - Grant appropriate permissions:
    ```bash
    chmod 664 legacy_store.db
    ```
