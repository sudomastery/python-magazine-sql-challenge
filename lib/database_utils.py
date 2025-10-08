"""SQLite database utilities.

Provides the database filename, a connection factory, and table creation with
foreign key constraints.
"""

from __future__ import annotations

import sqlite3


# SQLite database filename. The file is created in the project root when first written.
DB_FILE = "magazine.db"


def get_connection() -> sqlite3.Connection:
	"""Open a new connection to ``DB_FILE``.

	Foreign key enforcement in SQLite is disabled by default and must be
	enabled per connection using ``PRAGMA foreign_keys = ON;``. This function
	does not enable it; callers enable the pragma as required.
	"""
	conn = sqlite3.connect(DB_FILE)
	# Access columns by name: row["column"]
	conn.row_factory = sqlite3.Row
	return conn


def create_tables() -> None:
	"""Create the ``authors``, ``magazines``, and ``articles`` tables.

	The operation is idempotent and enables foreign key enforcement for the
	active connection.
	"""
	with get_connection() as conn:
		cur = conn.cursor()

		# Enable foreign key enforcement for this connection.
		cur.execute("PRAGMA foreign_keys = ON;")

		# Create base tables.
		cur.execute(
			"""
			CREATE TABLE IF NOT EXISTS authors (
				id   INTEGER PRIMARY KEY,
				name TEXT    NOT NULL UNIQUE
			);
			"""
		)

		cur.execute(
			"""
			CREATE TABLE IF NOT EXISTS magazines (
				id       INTEGER PRIMARY KEY,
				name     TEXT    NOT NULL UNIQUE,
				category TEXT
			);
			"""
		)

		# Create referencing table with foreign keys to authors and magazines.
		cur.execute(
			"""
			CREATE TABLE IF NOT EXISTS articles (
				id          INTEGER PRIMARY KEY,
				title       TEXT    NOT NULL,
				content     TEXT,
				author_id   INTEGER NOT NULL,
				magazine_id INTEGER NOT NULL,
				FOREIGN KEY (author_id)   REFERENCES authors(id),
				FOREIGN KEY (magazine_id) REFERENCES magazines(id)
			);
			"""
		)

		conn.commit()


if __name__ == "__main__":
	# Initialize the database when executed as a script.
	create_tables()


