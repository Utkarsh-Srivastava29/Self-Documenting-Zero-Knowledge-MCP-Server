# Contributing to ZK-MCP-Server

Thank you for your interest in this project.
This guide gets you from zero to a working dev environment in under five minutes.

---

## Prerequisites

- Python 3.10 or later
- `git`
- No database server required (SQLite ships with Python)

---

## Dev Environment Setup

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/MCP-SERVER.git
cd "MCP SERVER"

# 2. Create and activate a virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

# 3. Install the project + all dev dependencies in editable mode
pip install -e ".[dev]"

# 4. Seed the demo database
python server.py --seed

# 5. Verify the installation
python -m pytest           # should be green
ruff check .               # should produce zero warnings
```

---

## Running the Server

```bash
# stdio transport (for Claude Desktop)
python server.py

# SSE transport (for network access / testing with curl)
python server.py --transport sse --port 8080

# Custom database
python server.py --db /path/to/your.db
```

---

## Running Tests

```bash
# All tests with coverage report
python -m pytest --cov=src --cov-report=term-missing

# Single test file
python -m pytest tests/test_security.py -v

# Single test
python -m pytest tests/test_security.py::test_sql_injection_in_params_blocked -v

# Fast run (no coverage overhead)
python -m pytest
```

The test suite must stay green before any commit. Coverage must stay above 70%.

---

## Linting

```bash
# Check for lint errors
ruff check .

# Auto-fix safe issues
ruff check . --fix
```

`ruff` covers pyflakes, pycodestyle, isort, and pyupgrade — no separate tools needed.

---

## Project Structure Quick Reference

```
src/
├── introspector.py      ← PRAGMA-based schema discovery (start here to understand the pipeline)
├── schema_registry.py   ← In-memory schema registry (what was discovered)
├── sql_templates.py     ← Pre-validated SQL template engine (how queries are built)
├── security.py          ← Zero-Knowledge validator (the security enforcement point)
├── crud_generator.py    ← Dynamic MCP tool registration
└── join_analyzer.py     ← FK analysis and JOIN prompt generation

tests/
├── conftest.py          ← Shared pytest fixtures (DB setup, stack construction)
├── test_introspector.py ← Schema discovery tests
├── test_crud.py         ← CRUD operation tests
├── test_security.py     ← Security validation tests
└── test_joins.py        ← Relationship and join tests

docs/
├── APPROACH.md          ← Full technical write-up
├── DECISIONS.md         ← Architectural Decision Records (ADRs)
└── MCP_architecture.png ← Architecture diagram
```

---

## Adding a New Source Module

1. Create `src/your_module.py`
2. Add it to `src/__init__.py` if it exports a public class
3. Add a corresponding `tests/test_your_module.py`
4. Run `python -m pytest` and `ruff check .` before committing

---

## Commit Message Convention

Follow the format used in this repo's history:

```
<type>: <short imperative description>

Types: feat, fix, docs, test, build, ci, chore, refactor
```

Examples:
- `feat: add rate-limiting middleware to SSE transport`
- `fix: handle NULL primary keys in introspector`
- `docs: expand README with PostgreSQL migration path`
- `test: add edge case for empty table introspection`
- `ci: increase coverage threshold to 80%`

---

## Opening Issues and PRs

- **Bug reports**: Include the Python version, OS, and exact error output.
- **Feature requests**: Describe the problem you're solving, not just the solution.
- **Security issues**: See [SECURITY.md](SECURITY.md) — please do not post exploit details publicly.
