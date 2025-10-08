"""Pytest tests for the Magazine SQLite project.

These tests validate:
- Schema creation (tables + PRAGMA foreign_keys behavior)
- CRUD operations for Author, Magazine, Article
- Relationship helpers and aggregate queries

Note: We keep the tests in __init__.py per request. pytest.ini adjusts discovery
      so pytest will collect tests from this file.
"""

from __future__ import annotations

import os
import sqlite3
import typing as t

import pytest

from lib.database_utils import create_tables, DB_FILE, get_connection
from lib.author import Author
from lib.magazine import Magazine
from lib.article import Article


@pytest.fixture(autouse=True)
def fresh_db():
    """Ensure a clean database for each test.

    - Remove the DB file if it exists.
    - Recreate tables with foreign keys enabled.
    """
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
    create_tables()
    yield


def _table_names() -> t.List[str]:
    with get_connection() as conn:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        return sorted([row[0] if isinstance(row, (list, tuple)) else row["name"] for row in rows])


def test_create_tables_and_foreign_keys():
    # tables exist
    names = _table_names()
    assert "authors" in names
    assert "magazines" in names
    assert "articles" in names

    # foreign keys pragma is per-connection; ensure we can enable and insert valid refs
    with get_connection() as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        # valid base rows
        cur = conn.cursor()
        cur.execute("INSERT INTO authors(name) VALUES ('A')")
        author_id = cur.lastrowid
        cur.execute("INSERT INTO magazines(name, category) VALUES ('M', 'C')")
        magazine_id = cur.lastrowid
        # referencing row succeeds
        cur.execute(
            "INSERT INTO articles(title, content, author_id, magazine_id) VALUES (?,?,?,?)",
            ("T", None, author_id, magazine_id),
        )
        conn.commit()


def test_author_crud_and_relationships():
    au = Author("Alice").save()
    mg = Magazine("Tech Today", "Technology").save()
    Article("AI Trends", author=au, magazine=mg, content="...").save()

    # find_by_id
    au2 = Author.find_by_id(au.id)
    assert au2 is not None and au2.name == "Alice"

    # relationships
    assert [a.title for a in au.articles()] == ["AI Trends"]
    assert [m.name for m in au.magazines()] == ["Tech Today"]


def test_magazine_crud_relationships_and_titles():
    au = Author("Alice").save()
    mg = Magazine("Tech Today", "Technology").save()
    Article("AI 1", au, mg).save()
    Article("AI 2", au, mg).save()

    # contributors
    names = [a.name for a in mg.contributors()]
    assert names == ["Alice"]

    # titles
    assert mg.article_titles() == ["AI 1", "AI 2"]


def test_article_crud_and_updates():
    au = Author("Alice").save()
    mg = Magazine("Tech Today", "Technology").save()
    art = Article("AI Trends", au, mg, content="v1").save()

    # update content
    art.content = "v2"
    art.save()

    # reload and verify
    art2 = Article.find_by_id(art.id)
    assert art2 is not None
    assert art2.title == "AI Trends"
    assert art2.content == "v2"
    assert art2.author.id == au.id
    assert art2.magazine.id == mg.id


def test_aggregates_contributing_authors_and_top_publisher():
    au1 = Author("Alice").save()
    au2 = Author("Bob").save()
    mg1 = Magazine("Tech Today", "Technology").save()
    mg2 = Magazine("Science Daily", "Science").save()

    # mg1: Alice writes 3, Bob writes 1
    Article("A1", au1, mg1).save()
    Article("A2", au1, mg1).save()
    Article("A3", au1, mg1).save()
    Article("B1", au2, mg1).save()

    # mg2: Alice writes 1
    Article("S1", au1, mg2).save()

    # contributing authors on mg1: only Alice (>2)
    contributor_ids = Magazine.contributing_authors(mg1.id)
    assert contributor_ids == [au1.id]

    # top publisher: mg1 has 4 articles vs mg2 has 1
    assert Magazine.top_publisher() == mg1.id
