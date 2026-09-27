# API Reference — Self-Documenting Zero-Knowledge MCP Server

This document provides a comprehensive technical reference for the **Self-Documenting Zero-Knowledge MCP Server**. The server autonomously discovers undocumented SQLite database schemas at boot time, exposes dynamic Model Context Protocol (MCP) tools, prompts, and resources, and strictly enforces **Zero-Knowledge security** by disallowing raw SQL execution in favor of pre-validated parameterized templates.

---

## Table of Contents

1. [Architecture & Protocol Overview](#architecture--protocol-overview)
2. [MCP Tools (Auto-Generated CRUD & Search)](#1-mcp-tools-auto-generated-per-table)
   - [`create_{table}`](#create_table)
   - [`read_{table}`](#read_table)
   - [`update_{table}`](#update_table)
   - [`delete_{table}`](#delete_table)
   - [`list_{table}`](#list_table)
   - [`search_{table}`](#search_table)
3. [MCP Prompts](#2-mcp-prompts)
   - [`join_{table_a}_and_{table_b}`](#join_table_a_and_table_b)
   - [`explore_database`](#explore_database)
   - [`show_schema`](#show_schema)
4. [MCP Resources](#3-mcp-resources)
   - [`schema://tables`](#schematables)
   - [`schema://tables/{name}`](#schematablesname)
   - [`security://audit-log`](#securityaudit-log)
   - [`security://report`](#securityreport)
   - [`security://templates`](#securitytemplates)
5. [Core Python Modules (Internal API)](#4-core-python-modules-internal-api)
   - [`DatabaseIntrospector` (src/introspector.py)](#databaseintrospector-srcintrospectorpy)
   - [`SchemaRegistry` (src/schema_registry.py)](#schemaregistry-srcschema_registrypy)
   - [`SQLTemplateGenerator` & `SQLTemplateRegistry` (src/sql_templates.py)](#sqltemplategenerator--sqltemplateregistry-srcsql_templatespy)
   - [`ZeroKnowledgeValidator` (src/security.py)](#zeroknowledgevalidator-srcsecuritypy)
   - [`CRUDGenerator` (src/crud_generator.py)](#crudgenerator-srccrud_generatorpy)
   - [`JoinAnalyzer` (src/join_analyzer.py)](#joinanalyzer-srcjoin_analyzerpy)
6. [CLI Arguments](#5-cli-arguments)
7. [Environment Variables](#6-environment-variables)
8. [Zero-Knowledge Security Specification](#7-zero-knowledge-security-specification)

---

## Architecture & Protocol Overview

The server operates as an autonomous pipeline connecting an unknown SQLite database to an LLM client via the Model Context Protocol:

```
┌────────────────────────┐
│ Undocumented Database  │ (SQLite file)
└───────────┬────────────┘
            │ 1. PRAGMA Introspection
            ▼
┌────────────────────────┐
│  DatabaseIntrospector  │ Discovers tables, columns, PKs, FKs, indexes
└───────────┬────────────┘
            │ 2. Populates
            ▼
┌────────────────────────┐
│     SchemaRegistry     │ In-memory structural schema metadata
└─────┬─────────────┬────┘
      │             │ 3. Generates pre-compiled SQL
      │             ▼
      │   ┌──────────────────────┐
      │   │ SQLTemplateGenerator │ Parameterized SQL templates (CREATE, READ, etc.)
      │   └─────────┬────────────┘
      │             │ 4. Registers
      │             ▼
      │   ┌──────────────────────┐
      │   │ ZeroKnowledgeValidator│ Enforces template-only execution & type safety
      │   └─────────┬────────────┘
      ▼             ▼
┌────────────────────────┐
│   MCP Server Surface   │ Tools, Prompts, and Resources registered via FastMCP
└────────────────────────┘
```

The system establishes a strict **Zero-Knowledge Boundary**: the LLM client never generates, views, or executes raw SQL queries. All interactions are restricted to predefined template identifiers and strictly typed arguments.

---

## 1. MCP Tools (Auto-Generated per Table)

During the server initialization phase, [`CRUDGenerator`](file:///Users/utkarshsrivastava/Desktop/Self-Documenting-Zero-Knowledge-MCP-Server/src/crud_generator.py#L92-L270) inspects every discovered table and binds six discrete MCP tools to the FastMCP runtime.

| Tool Name Pattern | HTTP/RPC Action | Modifies Data | Primary Parameters | Result Output |
| :--- | :--- | :---: | :--- | :--- |
| `create_{table}` | INSERT | Yes | `data: dict` | Success confirmation + `last_insert_id` |
| `read_{table}` | SELECT (PK) | No | `data: dict` (PK columns) | Row JSON object or not-found text |
| `update_{table}` | UPDATE (PK) | Yes | `data: dict` (all columns + PK) | Affected row count message |
| `delete_{table}` | DELETE (PK) | Yes | `data: dict` (PK columns) | Affected row count message |
| `list_{table}` | SELECT (Paged) | No | `limit: int`, `offset: int` | List of row dictionaries |
| `search_{table}` | SELECT (LIKE) | No | `query: str` | List of matching row dictionaries |

---

### `create_{table}`

Inserts a new row into `{table}`. Non-primary-key columns are dynamically populated based on the table's schema.

- **Tool Name**: `create_{table}` (e.g., `create_customers`, `create_products`)
- **Template ID**: `create_{table}`
- **Mutability**: Write operation (commits transaction)

#### Parameters

| Name | Type | Description |
| :--- | :--- | :--- |
| `data` | `dict[str, Any]` | JSON object containing non-primary key column values. Required columns must be supplied; nullable columns with default values may be omitted or set to `null`. |

#### Example Invocation

```json
{
  "name": "create_customers",
  "arguments": {
    "data": {
      "first_name": "Eleanor",
      "last_name": "Vance",
      "email": "eleanor.vance@example.com",
      "phone": "+1-555-0199",
      "address": "42 Hill House Lane",
      "city": "Boston",
      "country": "USA"
    }
  }
}
```

#### Example Output

```text
Successfully created row in 'customers'. Insert ID: 104
```

---

### `read_{table}`

Fetches a single row from `{table}` by its primary key.

- **Tool Name**: `read_{table}` (e.g., `read_customers`, `read_orders`)
- **Template ID**: `read_{table}`
- **Mutability**: Read-only

#### Parameters

| Name | Type | Description |
| :--- | :--- | :--- |
| `data` | `dict[str, Any]` | JSON object containing the primary key column(s) and their values. |

#### Example Invocation

```json
{
  "name": "read_customers",
  "arguments": {
    "data": {
      "customer_id": 104
    }
  }
}
```

#### Example Output

```json
[
  {
    "customer_id": 104,
    "first_name": "Eleanor",
    "last_name": "Vance",
    "email": "eleanor.vance@example.com",
    "phone": "+1-555-0199",
    "address": "42 Hill House Lane",
    "city": "Boston",
    "country": "USA",
    "created_at": "2026-09-27T10:15:00Z"
  }
]
```

*Note: If no record matches the given primary key, the tool returns the string:*
```text
No row found in 'customers' with the given key.
```

---

### `update_{table}`

Updates an existing row in `{table}` identifying it by primary key. All non-primary-key columns must be provided in the payload.

- **Tool Name**: `update_{table}` (e.g., `update_customers`)
- **Template ID**: `update_{table}`
- **Mutability**: Write operation (commits transaction)

#### Parameters

| Name | Type | Description |
| :--- | :--- | :--- |
| `data` | `dict[str, Any]` | JSON object containing the primary key column(s) plus all non-primary key columns with their new values. |

#### Example Invocation

```json
{
  "name": "update_customers",
  "arguments": {
    "data": {
      "customer_id": 104,
      "first_name": "Eleanor",
      "last_name": "Vance-Crain",
      "email": "eleanor.crain@example.com",
      "phone": "+1-555-0199",
      "address": "42 Hill House Lane",
      "city": "Boston",
      "country": "USA"
    }
  }
}
```

#### Example Output

```text
Updated 1 row(s) in 'customers'.
```

---

### `delete_{table}`

Deletes a single row from `{table}` by its primary key.

- **Tool Name**: `delete_{table}` (e.g., `delete_customers`)
- **Template ID**: `delete_{table}`
- **Mutability**: Write operation (commits transaction)

#### Parameters

| Name | Type | Description |
| :--- | :--- | :--- |
| `data` | `dict[str, Any]` | JSON object containing the primary key column(s) specifying the row to delete. |

#### Example Invocation

```json
{
  "name": "delete_customers",
  "arguments": {
    "data": {
      "customer_id": 104
    }
  }
}
```

#### Example Output

```text
Deleted 1 row(s) from 'customers'.
```

---

### `list_{table}`

Retrieves a paginated list of rows from `{table}` sorted in natural database order.

- **Tool Name**: `list_{table}` (e.g., `list_customers`, `list_products`)
- **Template ID**: `list_{table}`
- **Mutability**: Read-only

#### Parameters

| Name | Type | Default | Constraints | Description |
| :--- | :--- | :---: | :--- | :--- |
| `limit` | `int` | `20` | `min: 1`, `max: 100` | Maximum number of rows to return. Values greater than 100 are clamped to 100. |
| `offset` | `int` | `0` | `min: 0` | Number of rows to skip before returning results. |

#### Example Invocation

```json
{
  "name": "list_customers",
  "arguments": {
    "limit": 2,
    "offset": 0
  }
}
```

#### Example Output

```json
[
  {
    "customer_id": 1,
    "first_name": "Alice",
    "last_name": "Smith",
    "email": "alice@example.com",
    "phone": "555-0101",
    "city": "New York",
    "country": "USA"
  },
  {
    "customer_id": 2,
    "first_name": "Bob",
    "last_name": "Jones",
    "email": "bob@example.com",
    "phone": "555-0102",
    "city": "Chicago",
    "country": "USA"
  }
]
```

---

### `search_{table}`

Performs substring matching across all `TEXT`, `VARCHAR`, and `CHAR` columns for `{table}` using SQL `LIKE %query%`.

- **Tool Name**: `search_{table}` (e.g., `search_customers`, `search_orders`)
- **Template ID**: `search_{table}`
- **Mutability**: Read-only
- **Result Limit**: Capped at `50` records maximum

#### Parameters

| Name | Type | Description |
| :--- | :--- | :--- |
| `query` | `str` | Text search string to match against any text column in the table. |

#### Example Invocation

```json
{
  "name": "search_customers",
  "arguments": {
    "query": "Boston"
  }
}
```

#### Example Output

```json
[
  {
    "customer_id": 104,
    "first_name": "Eleanor",
    "last_name": "Vance",
    "email": "eleanor.vance@example.com",
    "phone": "+1-555-0199",
    "address": "42 Hill House Lane",
    "city": "Boston",
    "country": "USA"
  }
]
```

---

## 2. MCP Prompts

MCP Prompts provide guided workflows and contextual knowledge to LLM clients. Registered by [`JoinAnalyzer`](file:///Users/utkarshsrivastava/Desktop/Self-Documenting-Zero-Knowledge-MCP-Server/src/join_analyzer.py#L36-L258), they explain table relationships, data schemas, and recommended database workflows.

### `join_{table_a}_and_{table_b}`

Provides detailed relationship guidance and canonical join query syntax between two foreign-key-related tables.

- **Prompt Name Pattern**: `join_{table_a}_and_{table_b}` (tables sorted alphabetically, e.g., `join_customers_and_orders`)
- **Relationship Support**:
  - **One-to-Many Direct**: Direct foreign key relationship (e.g., `orders.customer_id -> customers.id`).
  - **Many-to-Many Indirect**: Junction table relationship with 2+ foreign keys (e.g., `orders` and `products` connected via `order_items`).

#### Example Output (`join_customers_and_orders`)

```markdown
## One-to-Many: customers → orders

Each row in 'customers' can have many related rows in 'orders'.

**Join column**: `orders.customer_id` → `customers.customer_id`

**How to join:**
```sql
SELECT a.*, b.*
FROM orders a
INNER JOIN customers b ON a.customer_id = b.customer_id
```

**Use case**: Get orders data along with their parent customers info.
```

#### Example Output (`join_orders_and_products` via `order_items`)

```markdown
## Many-to-Many: orders ↔ products

These tables are connected through the junction table 'order_items'.

**How to join:**
```sql
SELECT a.*, b.*
FROM orders a
INNER JOIN order_items j ON a.order_id = j.order_id
INNER JOIN products b ON j.product_id = b.product_id
```

**Relationship**: Many orders can be associated with many products.
**Use case**: Find all products related to a specific orders (or vice versa).
```

---

### `explore_database`

A comprehensive exploration guide giving the LLM immediate awareness of the entire database topology without needing external documentation.

- **Prompt Name**: `explore_database`
- **Contents**:
  1. **Available Tables**: List of all discovered tables with current row counts and first 5 column names.
  2. **Relationships**: Summary of discovered foreign key paths (both one-to-many and junction-based many-to-many).
  3. **Available Operations**: Catalog of auto-generated CRUD tools (`list_{table}`, `read_{table}`, `create_{table}`, `update_{table}`, `delete_{table}`, `search_{table}`).
  4. **Usage Guidelines & Tips**: Recommendations for safely navigating and querying data through pre-validated templates.

---

### `show_schema`

Provides a raw summary dump of the full auto-discovered database schema alongside Zero-Knowledge security notices.

- **Prompt Name**: `show_schema`
- **Contents**:
  - Database file location.
  - Complete column listings per table, including data types, `[PK]` markers, nullability, and default values.
  - Foreign key bindings and indices.
  - Zero-Knowledge security notice reminding the caller that raw SQL execution is forbidden and all operations are restricted to pre-validated templates.

---

## 3. MCP Resources

MCP Resources expose readable, URI-addressable endpoints that provide direct data and state inspection for clients and administrators.

| Resource URI | MIME Type | Description |
| :--- | :--- | :--- |
| `schema://tables` | `text/plain` | Full database schema overview across all tables, columns, indexes, and FK relationships. |
| `schema://tables/{name}` | `text/plain` | Granular schema specification for a single named table. |
| `security://audit-log` | `application/json` | Recent 50 query executions with timestamps, template IDs, parameters, and results. |
| `security://report` | `application/json` | Security metric summary: total queries, success/failure counts, and recent violations. |
| `security://templates` | `application/json` | All registered SQL templates (the only allowed executable queries). |

---

### `schema://tables`

Returns a formatted plain-text schema overview of the entire database.

#### Example Output

```text
Database: /Users/utkarshsrivastava/Desktop/Self-Documenting-Zero-Knowledge-MCP-Server/legacy_store.db
Total Tables: 4
==================================================

Table: customers (100 rows)
Columns:
  - customer_id: INTEGER [PK] (NOT NULL)
  - first_name: TEXT (NOT NULL)
  - last_name: TEXT (NOT NULL)
  - email: TEXT (NOT NULL)
  - phone: TEXT (nullable)
  - city: TEXT (nullable)
  - country: TEXT (nullable)
Indexes:
  - idx_customers_email: [email] (UNIQUE)
----------------------------------------

Table: orders (250 rows)
Columns:
  - order_id: INTEGER [PK] (NOT NULL)
  - customer_id: INTEGER (NOT NULL)
  - order_date: TIMESTAMP (NOT NULL) DEFAULT CURRENT_TIMESTAMP
  - total_amount: REAL (NOT NULL)
Foreign Keys:
  - customer_id -> customers.customer_id
----------------------------------------

Relationships:
  orders.customer_id -> customers.customer_id
```

---

### `schema://tables/{name}`

Returns the schema summary for a specific table identified by `{name}`.

- **URI**: `schema://tables/{name}` (e.g., `schema://tables/customers`)

#### Example Output (`schema://tables/customers`)

```text
Table: customers (100 rows)
Columns:
  - customer_id: INTEGER [PK] (NOT NULL)
  - first_name: TEXT (NOT NULL)
  - last_name: TEXT (NOT NULL)
  - email: TEXT (NOT NULL)
  - phone: TEXT (nullable)
  - city: TEXT (nullable)
  - country: TEXT (nullable)
Indexes:
  - idx_customers_email: [email] (UNIQUE)
```

---

### `security://audit-log`

Returns the 50 most recent query execution log entries in reverse chronological order as a JSON array.

- **URI**: `security://audit-log`

#### Example Output

```json
[
  {
    "timestamp": "2026-09-27T12:45:10.123456+00:00",
    "template_id": "list_customers",
    "operation": "LIST",
    "table": "customers",
    "params": {
      "limit": 20,
      "offset": 0
    },
    "success": true,
    "error": null,
    "row_count": 20
  },
  {
    "timestamp": "2026-09-27T12:44:02.882190+00:00",
    "template_id": "create_customers",
    "operation": "CREATE",
    "table": "customers",
    "params": {
      "first_name": "Eleanor",
      "last_name": "Vance",
      "email": "eleanor.vance@example.com"
    },
    "success": true,
    "error": null,
    "row_count": 1
  }
]
```

---

### `security://report`

Provides aggregate statistics summarizing server activity, total executions, success/failure counts, and recorded security violations.

- **URI**: `security://report`

#### Example Output

```json
{
  "total_queries": 42,
  "successful": 41,
  "failed": 1,
  "registered_templates": 27,
  "recent_failures": [
    {
      "timestamp": "2026-09-27T12:40:01.002931+00:00",
      "template_id": "read_customers",
      "operation": "READ",
      "table": "customers",
      "params": {
        "customer_id": "invalid'; DROP TABLE customers;--"
      },
      "success": false,
      "error": "Potentially dangerous content detected in parameter 'customer_id': value matches blocked pattern. Input rejected.",
      "row_count": null
    }
  ]
}
```

---

### `security://templates`

Returns the full registry of all compiled, pre-validated SQL templates. These represent the **only** queries permitted to run against the underlying SQLite engine.

- **URI**: `security://templates`

#### Example Output

```json
[
  {
    "id": "create_customers",
    "description": "Insert a new row into customers",
    "sql": "INSERT INTO [customers] ([first_name], [last_name], [email], [phone], [city], [country]) VALUES (?, ?, ?, ?, ?, ?)",
    "params": ["first_name", "last_name", "email", "phone", "city", "country"],
    "param_types": {
      "first_name": "TEXT",
      "last_name": "TEXT",
      "email": "TEXT",
      "phone": "TEXT",
      "city": "TEXT",
      "country": "TEXT"
    },
    "operation": "CREATE",
    "table": "customers",
    "is_write": true
  },
  {
    "id": "read_customers",
    "description": "Read a single row from customers by primary key",
    "sql": "SELECT * FROM [customers] WHERE [customer_id] = ?",
    "params": ["customer_id"],
    "param_types": {
      "customer_id": "INTEGER"
    },
    "operation": "READ",
    "table": "customers",
    "is_write": false
  },
  {
    "id": "list_customers",
    "description": "List rows from customers with pagination",
    "sql": "SELECT * FROM [customers] LIMIT ? OFFSET ?",
    "params": ["limit", "offset"],
    "param_types": {
      "limit": "INTEGER",
      "offset": "INTEGER"
    },
    "operation": "LIST",
    "table": "customers",
    "is_write": false
  }
]
```

---

## 4. Core Python Modules (Internal API)

The server codebase is organized in `src/` as a modular pipeline. Below is the technical specification of the public API for each internal component.

```
src/
├── introspector.py       # Scans database with PRAGMA queries
├── schema_registry.py    # Holds and exposes schema metadata
├── sql_templates.py      # Generates parameterized SQL templates
├── security.py           # Zero-Knowledge execution validator & audit log
├── crud_generator.py     # Registers MCP tools for each table
└── join_analyzer.py      # Analyzes relationships and registers prompts
```

---

### `DatabaseIntrospector` ([`src/introspector.py`](file:///Users/utkarshsrivastava/Desktop/Self-Documenting-Zero-Knowledge-MCP-Server/src/introspector.py#L136-L240))

Autonomously extracts database metadata from an arbitrary SQLite file using native PRAGMA introspection statements (`PRAGMA table_info`, `PRAGMA foreign_key_list`, `PRAGMA index_list`, and `sqlite_master`).

#### Class Definition

```python
class DatabaseIntrospector:
    def __init__(self, db_path: str):
        ...
    def introspect(self) -> DatabaseSchema:
        ...
```

#### Methods

- [`DatabaseIntrospector.__init__(db_path: str)`](file:///Users/utkarshsrivastava/Desktop/Self-Documenting-Zero-Knowledge-MCP-Server/src/introspector.py#L142-L144):
  Initializes introspector with the filesystem path to the SQLite database file.
- [`DatabaseIntrospector.introspect() -> DatabaseSchema`](file:///Users/utkarshsrivastava/Desktop/Self-Documenting-Zero-Knowledge-MCP-Server/src/introspector.py#L152-L183):
  Executes discovery queries and returns a populated [`DatabaseSchema`](file:///Users/utkarshsrivastava/Desktop/Self-Documenting-Zero-Knowledge-MCP-Server/src/introspector.py#L112-L134) object.

#### Data Models

- [`ColumnInfo`](file:///Users/utkarshsrivastava/Desktop/Self-Documenting-Zero-Knowledge-MCP-Server/src/introspector.py#L17-L33): Represents a single column.
  - Attributes: `name: str`, `data_type: str`, `is_nullable: bool`, `default_value: str | None`, `is_primary_key: bool`.
  - Method: `to_dict() -> dict`
- [`ForeignKeyInfo`](file:///Users/utkarshsrivastava/Desktop/Self-Documenting-Zero-Knowledge-MCP-Server/src/introspector.py#L36-L50): Represents a foreign key constraint.
  - Attributes: `from_table: str`, `from_column: str`, `to_table: str`, `to_column: str`.
  - Method: `to_dict() -> dict`
- [`IndexInfo`](file:///Users/utkarshsrivastava/Desktop/Self-Documenting-Zero-Knowledge-MCP-Server/src/introspector.py#L53-L67): Represents a table index.
  - Attributes: `name: str`, `table: str`, `columns: list[str]`, `is_unique: bool`.
  - Method: `to_dict() -> dict`
- [`TableInfo`](file:///Users/utkarshsrivastava/Desktop/Self-Documenting-Zero-Knowledge-MCP-Server/src/introspector.py#L70-L109): Encapsulates all metadata for a table.
  - Attributes: `name: str`, `columns: list[ColumnInfo]`, `foreign_keys: list[ForeignKeyInfo]`, `indexes: list[IndexInfo]`, `row_count: int`.
  - Properties: `primary_key_columns -> list[str]`, `non_pk_columns -> list[str]`, `column_names -> list[str]`.
  - Methods: `get_column(name: str) -> ColumnInfo | None`, `to_dict() -> dict`.
- [`DatabaseSchema`](file:///Users/utkarshsrivastava/Desktop/Self-Documenting-Zero-Knowledge-MCP-Server/src/introspector.py#L112-L134): Complete schema collection.
  - Attributes: `tables: dict[str, TableInfo]`, `db_path: str`.
  - Properties: `table_names -> list[str]`.
  - Methods: `get_all_relationships() -> list[ForeignKeyInfo]`, `to_dict() -> dict`.

---

### `SchemaRegistry` ([`src/schema_registry.py`](file:///Users/utkarshsrivastava/Desktop/Self-Documenting-Zero-Knowledge-MCP-Server/src/schema_registry.py#L16-L133))

Maintains an in-memory repository of discovered schema structures and exposes query helpers for downstream components.

#### Class Definition

```python
class SchemaRegistry:
    def __init__(self, schema: DatabaseSchema):
        ...
```

#### Public Methods

- [`get_table_names() -> list[str]`](file:///Users/utkarshsrivastava/Desktop/Self-Documenting-Zero-Knowledge-MCP-Server/src/schema_registry.py#L32-L34): Returns alphabetical list of table names.
- [`get_table(table_name: str) -> TableInfo | None`](file:///Users/utkarshsrivastava/Desktop/Self-Documenting-Zero-Knowledge-MCP-Server/src/schema_registry.py#L36-L38): Fetches [`TableInfo`](file:///Users/utkarshsrivastava/Desktop/Self-Documenting-Zero-Knowledge-MCP-Server/src/introspector.py#L70-L109) for a specific table.
- [`get_columns(table_name: str) -> list[ColumnInfo]`](file:///Users/utkarshsrivastava/Desktop/Self-Documenting-Zero-Knowledge-MCP-Server/src/schema_registry.py#L40-L43): Returns list of column objects for a table.
- [`get_column_names(table_name: str) -> list[str]`](file:///Users/utkarshsrivastava/Desktop/Self-Documenting-Zero-Knowledge-MCP-Server/src/schema_registry.py#L45-L48): Returns list of column name strings.
- [`get_primary_key(table_name: str) -> list[str]`](file:///Users/utkarshsrivastava/Desktop/Self-Documenting-Zero-Knowledge-MCP-Server/src/schema_registry.py#L50-L53): Returns list of primary key column names.
- [`get_non_pk_columns(table_name: str) -> list[str]`](file:///Users/utkarshsrivastava/Desktop/Self-Documenting-Zero-Knowledge-MCP-Server/src/schema_registry.py#L55-L58): Returns non-primary-key column names.
- [`get_foreign_keys(table_name: str) -> list[ForeignKeyInfo]`](file:///Users/utkarshsrivastava/Desktop/Self-Documenting-Zero-Knowledge-MCP-Server/src/schema_registry.py#L60-L63): Returns outbound foreign keys defined on `table_name`.
- [`get_all_relationships() -> list[ForeignKeyInfo]`](file:///Users/utkarshsrivastava/Desktop/Self-Documenting-Zero-Knowledge-MCP-Server/src/schema_registry.py#L65-L67): Returns all foreign key relationships across all tables.
- [`get_tables_referencing(table_name: str) -> list[tuple[str, str, str]]`](file:///Users/utkarshsrivastava/Desktop/Self-Documenting-Zero-Knowledge-MCP-Server/src/schema_registry.py#L69-L79): Finds inbound foreign keys pointing to `table_name`. Returns list of `(from_table, from_column, to_column)` tuples.
- [`get_table_summary(table_name: str) -> str`](file:///Users/utkarshsrivastava/Desktop/Self-Documenting-Zero-Knowledge-MCP-Server/src/schema_registry.py#L81-L106): Produces formatted text summary of table columns, PKs, FKs, and indexes.
- [`get_full_schema_summary() -> str`](file:///Users/utkarshsrivastava/Desktop/Self-Documenting-Zero-Knowledge-MCP-Server/src/schema_registry.py#L108-L128): Produces complete plain text dump for all tables.
- [`to_dict() -> dict`](file:///Users/utkarshsrivastava/Desktop/Self-Documenting-Zero-Knowledge-MCP-Server/src/schema_registry.py#L130-L132): Returns dictionary serialization of the full schema.

---

### `SQLTemplateGenerator` & `SQLTemplateRegistry` ([`src/sql_templates.py`](file:///Users/utkarshsrivastava/Desktop/Self-Documenting-Zero-Knowledge-MCP-Server/src/sql_templates.py#L1-L283))

Synthesizes pre-validated, parameterized SQL queries at boot time for every table and relationship.

#### Data Models & Registry

- [`SQLTemplate`](file:///Users/utkarshsrivastava/Desktop/Self-Documenting-Zero-Knowledge-MCP-Server/src/sql_templates.py#L24-L46): Represents an immutable SQL template.
  - Attributes:
    - `id: str`: Unique identifier (e.g., `create_customers`, `read_orders`).
    - `description: str`: Human-readable summary.
    - `sql: str`: Parameterized SQL statement with `?` placeholders.
    - `params: list[str]`: Ordered parameter names matching positional `?` placeholders.
    - `param_types: dict[str, str]`: Mapping of parameter name to expected SQLite data type.
    - `operation: str`: One of `CREATE`, `READ`, `UPDATE`, `DELETE`, `LIST`, `SEARCH`, `JOIN`.
    - `table: str`: Target table name.
    - `is_write: bool`: Flag indicating whether the statement modifies state (`True` commits transaction).
  - Method: `to_dict() -> dict`

- [`SQLTemplateRegistry`](file:///Users/utkarshsrivastava/Desktop/Self-Documenting-Zero-Knowledge-MCP-Server/src/sql_templates.py#L48-L86): Container holding all registered templates.
  - [`register(template: SQLTemplate) -> None`](file:///Users/utkarshsrivastava/Desktop/Self-Documenting-Zero-Knowledge-MCP-Server/src/sql_templates.py#L60-L65): Adds a template to the registry.
  - [`get(template_id: str) -> SQLTemplate | None`](file:///Users/utkarshsrivastava/Desktop/Self-Documenting-Zero-Knowledge-MCP-Server/src/sql_templates.py#L67-L69): Looks up template by ID.
  - [`list_templates() -> list[SQLTemplate]`](file:///Users/utkarshsrivastava/Desktop/Self-Documenting-Zero-Knowledge-MCP-Server/src/sql_templates.py#L71-L73): Returns all templates.
  - [`list_by_table(table_name: str) -> list[SQLTemplate]`](file:///Users/utkarshsrivastava/Desktop/Self-Documenting-Zero-Knowledge-MCP-Server/src/sql_templates.py#L75-L77): Filters templates by target table.
  - [`list_by_operation(operation: str) -> list[SQLTemplate]`](file:///Users/utkarshsrivastava/Desktop/Self-Documenting-Zero-Knowledge-MCP-Server/src/sql_templates.py#L79-L81): Filters templates by operation type.
  - [`count -> int`](file:///Users/utkarshsrivastava/Desktop/Self-Documenting-Zero-Knowledge-MCP-Server/src/sql_templates.py#L83-L85): Property returning total template count.

#### Generator Class

- [`SQLTemplateGenerator.__init__(schema_registry: SchemaRegistry)`](file:///Users/utkarshsrivastava/Desktop/Self-Documenting-Zero-Knowledge-MCP-Server/src/sql_templates.py#L104-L106):
  Initializes template generator with reference to the schema registry.
- [`SQLTemplateGenerator.generate_all() -> SQLTemplateRegistry`](file:///Users/utkarshsrivastava/Desktop/Self-Documenting-Zero-Knowledge-MCP-Server/src/sql_templates.py#L108-L117):
  Generates all CRUD, SEARCH, and JOIN templates and returns the populated [`SQLTemplateRegistry`](file:///Users/utkarshsrivastava/Desktop/Self-Documenting-Zero-Knowledge-MCP-Server/src/sql_templates.py#L48-L86).

---

### `ZeroKnowledgeValidator` ([`src/security.py`](file:///Users/utkarshsrivastava/Desktop/Self-Documenting-Zero-Knowledge-MCP-Server/src/security.py#L77-L307))

The gatekeeper of the Zero-Knowledge security architecture. All SQL execution is routed through this class; direct database execution outside this class is architecturally prohibited.

#### Exceptions & Models

- [`SecurityError`](file:///Users/utkarshsrivastava/Desktop/Self-Documenting-Zero-Knowledge-MCP-Server/src/security.py#L47-L49): Raised on invalid template IDs, parameter mismatches, type violations, or pattern blocklist hits.
- [`AuditLogEntry`](file:///Users/utkarshsrivastava/Desktop/Self-Documenting-Zero-Knowledge-MCP-Server/src/security.py#L52-L75): Data class recording a single execution event.
  - Attributes: `timestamp`, `template_id`, `operation`, `table`, `params`, `success`, `error`, `row_count`.
  - Method: `to_dict() -> dict`

#### Class Definition & Methods

```python
class ZeroKnowledgeValidator:
    def __init__(self, db_path: str, template_registry: SQLTemplateRegistry):
        ...
```

- [`validate_and_execute(template_id: str, params: dict[str, Any]) -> list[dict]`](file:///Users/utkarshsrivastava/Desktop/Self-Documenting-Zero-Knowledge-MCP-Server/src/security.py#L113-L182):
  Validates incoming parameters, sanitizes input, binds arguments to the identified template, executes the query, records an audit log entry, and returns rows as dictionaries.
  - *Raises*: [`SecurityError`](file:///Users/utkarshsrivastava/Desktop/Self-Documenting-Zero-Knowledge-MCP-Server/src/security.py#L47-L49) if validation fails or SQLite raises an exception.
- [`get_audit_log(limit: int = 50) -> list[dict]`](file:///Users/utkarshsrivastava/Desktop/Self-Documenting-Zero-Knowledge-MCP-Server/src/security.py#L287-L290):
  Returns the most recent audit log entries up to `limit`.
- [`get_security_report() -> dict`](file:///Users/utkarshsrivastava/Desktop/Self-Documenting-Zero-Knowledge-MCP-Server/src/security.py#L292-L306):
  Calculates aggregate metrics (total queries, successes, failures, registered templates) and includes the 10 most recent failure entries.

---

### `CRUDGenerator` ([`src/crud_generator.py`](file:///Users/utkarshsrivastava/Desktop/Self-Documenting-Zero-Knowledge-MCP-Server/src/crud_generator.py#L92-L270))

Dynamically binds MCP tools to the FastMCP server instance for each table discovered in the schema registry.

#### Class Definition

```python
class CRUDGenerator:
    def __init__(
        self,
        mcp: FastMCP,
        schema_registry: SchemaRegistry,
        validator: ZeroKnowledgeValidator,
    ):
        ...
    def generate_all_tools(self) -> list[str]:
        ...
```

- [`generate_all_tools() -> list[str]`](file:///Users/utkarshsrivastava/Desktop/Self-Documenting-Zero-Knowledge-MCP-Server/src/crud_generator.py#L114-L129):
  Iterates over all discovered tables, generates create, read, update, delete, list, and search handlers with closure variables, registers each on `mcp.tool()`, and returns a list of registered tool names.

---

### `JoinAnalyzer` ([`src/join_analyzer.py`](file:///Users/utkarshsrivastava/Desktop/Self-Documenting-Zero-Knowledge-MCP-Server/src/join_analyzer.py#L36-L258))

Analyzes foreign key graphs, classifies relationships into one-to-many or junction-based many-to-many, and registers instructional MCP prompts.

#### Class Definition

```python
class JoinAnalyzer:
    def __init__(
        self,
        mcp: FastMCP,
        schema_registry: SchemaRegistry,
        validator: ZeroKnowledgeValidator,
    ):
        ...
    def analyze_and_register(self) -> list[str]:
        ...
```

- [`analyze_and_register() -> list[str]`](file:///Users/utkarshsrivastava/Desktop/Self-Documenting-Zero-Knowledge-MCP-Server/src/join_analyzer.py#L54-L69):
  Discovers all relationships, generates join prompt handlers, adds `explore_database` and `show_schema` prompts to FastMCP, and returns all registered prompt names.

#### Data Model

- [`Relationship`](file:///Users/utkarshsrivastava/Desktop/Self-Documenting-Zero-Knowledge-MCP-Server/src/join_analyzer.py#L25-L34): Encapsulates a discovered relationship.
  - Attributes: `from_table: str`, `from_column: str`, `to_table: str`, `to_column: str`, `relationship_type: str` (`"one-to-many"` or `"many-to-many"`), `junction_table: str | None`.

---

## 5. CLI Arguments

The server executable is [`server.py`](file:///Users/utkarshsrivastava/Desktop/Self-Documenting-Zero-Knowledge-MCP-Server/server.py). It accepts the following command-line flags:

```bash
python server.py [OPTIONS]
```

| Flag | Type | Default | Description |
| :--- | :---: | :--- | :--- |
| `--db PATH` | `str` | `$DATABASE_PATH` or `./legacy_store.db` | Filesystem path to the SQLite database file to introspect and manage. |
| `--transport {stdio,sse}` | `str` | `stdio` | MCP transport protocol. Use `stdio` for local client integrations (e.g. Claude Desktop) or `sse` for HTTP Server-Sent Events. |
| `--port PORT` | `int` | `8080` | Network port for HTTP/SSE transport (only applicable when `--transport sse` is set). |
| `--seed` | Flag | `False` | Automatically seeds a sample legacy e-commerce database with demonstration data prior to starting the server. |

### Usage Examples

#### Run via Stdio Transport (Default, for Claude Desktop)

```bash
python server.py
```

#### Seed Demo Database and Run via SSE Transport

```bash
python server.py --seed --transport sse --port 8080
```

#### Connect to a Custom SQLite Database

```bash
python server.py --db /var/data/app.db
```

---

## 6. Environment Variables

The server inspects environment variables for configuration defaults:

| Variable | Type | Default Value | Description |
| :--- | :---: | :--- | :--- |
| `DATABASE_PATH` | String | `./legacy_store.db` | Overrides the default SQLite database path if `--db` is not explicitly supplied on the command line. |

### Precedence Hierarchy

1. Command-line argument: `--db <path>` *(highest priority)*
2. Environment variable: `DATABASE_PATH=<path>`
3. Fallback default: `legacy_store.db` relative to server root *(lowest priority)*

---

## 7. Zero-Knowledge Security Specification

The core design principle of this server is **Zero-Knowledge SQL execution**. The LLM client operates as an untrusted agent and is prohibited from formulating or executing arbitrary SQL syntax.

### 1. Template-Only Execution
- Queries are compiled and registered exclusively at server startup.
- The execution engine only accepts a recognized `template_id`. Any query attempt with an unverified template ID immediately raises [`SecurityError`](file:///Users/utkarshsrivastava/Desktop/Self-Documenting-Zero-Knowledge-MCP-Server/src/security.py#L47-L49) and logs an audit failure.

### 2. Strict Parameter Validation
- **Missing Parameters**: If any parameter required by the template placeholder is omitted, execution is aborted.
- **Extra Parameters**: Any extraneous parameter not defined in the template is rejected to prevent payload smuggling.
- **Type Checking**: Parameters are validated against expected SQLite column types (`INTEGER`, `REAL`, `TEXT`, `BLOB`, `TIMESTAMP`).

### 3. Defense-in-Depth Pattern Sanitization
All string parameters are checked against [`DANGEROUS_PATTERNS`](file:///Users/utkarshsrivastava/Desktop/Self-Documenting-Zero-Knowledge-MCP-Server/src/security.py#L28-L45) regex rules to block SQL injection and escape sequences:

- Comment injection: `--`, `/* ... */`
- Multi-statement execution: `; DROP`, `; DELETE`, `; UPDATE`, `; INSERT`, `; ALTER`, `; CREATE`
- Subquery exploitation: `UNION SELECT`
- System commands & PRAGMA access: `ATTACH DATABASE`, `DETACH DATABASE`, `PRAGMA `, `sqlite_master`, `exec(`, `xp_`

### 4. Comprehensive Audit Trail
Every single database invocation — successful or rejected — is logged to the in-memory audit trail, accessible via the `security://audit-log` resource and `security://report` dashboard.
