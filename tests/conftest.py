"""
Shared pytest fixtures for the ZK-MCP-Server test suite.

These fixtures are automatically discovered by pytest — no import needed
in individual test files.
"""

import sqlite3

import pytest

from src.introspector import DatabaseIntrospector
from src.schema_registry import SchemaRegistry
from src.security import ZeroKnowledgeValidator
from src.sql_templates import SQLTemplateGenerator

# ── Helper ────────────────────────────────────────────────────────────────────

def _build_stack(db_path: str) -> dict:
    """Build the full introspection → registry → template → validator stack."""
    introspector = DatabaseIntrospector(db_path)
    schema = introspector.introspect()
    registry = SchemaRegistry(schema)
    template_gen = SQLTemplateGenerator(registry)
    template_registry = template_gen.generate_all()
    validator = ZeroKnowledgeValidator(db_path, template_registry)
    return {
        "db_path": db_path,
        "schema": schema,
        "registry": registry,
        "template_registry": template_registry,
        "validator": validator,
    }


# ── Simple single-table fixture (used by test_crud, test_security) ────────────

@pytest.fixture
def simple_db(tmp_path):
    """
    A minimal single-table DB with an `items` table.
    Used by CRUD and security tests.
    """
    db_path = str(tmp_path / "simple.db")
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript("""
        CREATE TABLE items (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL,
            price       REAL    DEFAULT 0.0,
            quantity    INTEGER DEFAULT 0,
            description TEXT
        );
        INSERT INTO items (name, price, quantity, description)
        VALUES ('Widget', 9.99, 100, 'A useful widget');
        INSERT INTO items (name, price, quantity, description)
        VALUES ('Gadget', 19.99, 50, 'A fancy gadget');
    """)
    conn.commit()
    conn.close()
    return _build_stack(db_path)


# ── Relational multi-table fixture (used by test_joins) ──────────────────────

@pytest.fixture
def relational_db(tmp_path):
    """
    A four-table DB with one-to-many and many-to-many relationships.
    Used by join and relationship tests.
    """
    db_path = str(tmp_path / "relational.db")
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript("""
        CREATE TABLE authors (
            id   INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        );
        CREATE TABLE books (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            title     TEXT    NOT NULL,
            author_id INTEGER,
            FOREIGN KEY (author_id) REFERENCES authors(id)
        );
        CREATE TABLE tags (
            id   INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        );
        CREATE TABLE book_tags (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL,
            tag_id  INTEGER NOT NULL,
            FOREIGN KEY (book_id) REFERENCES books(id),
            FOREIGN KEY (tag_id)  REFERENCES tags(id)
        );
        INSERT INTO authors (name) VALUES ('Alice'), ('Bob');
        INSERT INTO books   (title, author_id) VALUES ('Book A', 1), ('Book B', 2), ('Book C', 1);
        INSERT INTO tags    (name) VALUES ('Fiction'), ('Science'), ('History');
        INSERT INTO book_tags (book_id, tag_id) VALUES (1,1),(1,2),(2,3),(3,1);
    """)
    conn.commit()
    conn.close()
    return _build_stack(db_path)


# ── Users-and-posts fixture (used by test_introspector) ──────────────────────

@pytest.fixture
def users_posts_db(tmp_path):
    """
    A two-table DB with users and posts (FK relationship).
    Used by introspector tests.
    """
    db_path = str(tmp_path / "users_posts.db")
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript("""
        CREATE TABLE users (
            id    INTEGER PRIMARY KEY AUTOINCREMENT,
            name  TEXT NOT NULL,
            email TEXT UNIQUE,
            age   INTEGER
        );
        CREATE TABLE posts (
            id         INTEGER   PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER   NOT NULL,
            title      TEXT      NOT NULL,
            content    TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        INSERT INTO users (name, email, age)
        VALUES ('Alice', 'alice@test.com', 30),
               ('Bob',   'bob@test.com',   25);
        INSERT INTO posts (user_id, title, content)
        VALUES (1, 'First Post',  'Hello World'),
               (1, 'Second Post', 'More content'),
               (2, 'Bob Post',    'Bob says hi');
    """)
    conn.commit()
    conn.close()
    return db_path  # introspector tests build their own stack


# ── Security-focused fixture (secrets table) ──────────────────────────────────

@pytest.fixture
def secrets_db(tmp_path):
    """
    A single-table `secrets` DB used by the security test suite.
    """
    db_path = str(tmp_path / "secrets.db")
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE secrets (
            id    INTEGER PRIMARY KEY AUTOINCREMENT,
            key   TEXT NOT NULL,
            value TEXT NOT NULL
        );
        INSERT INTO secrets (key, value) VALUES ('api_key', 'sk-12345');
        INSERT INTO secrets (key, value) VALUES ('password', 'hunter2');
    """)
    conn.commit()
    conn.close()
    return _build_stack(db_path)
