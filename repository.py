import os
from typing import Any, Dict, List, Optional
import psycopg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgres://postgres:dev@localhost:5432/tasks")


def get_connection() -> psycopg.Connection:
    """Create and return a new connection to PostgreSQL."""
    return psycopg.connect(DATABASE_URL)


def init_db() -> None:
    """Initialize the tasks table and seed with three initial tasks if empty."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 1. Create table if not exists
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id SERIAL PRIMARY KEY,
                    title TEXT NOT NULL,
                    done BOOLEAN NOT NULL DEFAULT FALSE
                );
            """)

            # 2. Check if table is empty
            cur.execute("SELECT COUNT(*) FROM tasks;")
            count = cur.fetchone()[0]

            # 3. Seed only if empty (A2/A3 first-run rule)
            if count == 0:
                cur.executemany(
                    "INSERT INTO tasks (title, done) VALUES (%s, %s);",
                    [
                        ("Review assignment requirements", True),
                        ("Implement CRUD endpoints", False),
                        ("Write automated test cases", False),
                    ],
                )
        conn.commit()


def check_db_health() -> bool:
    """Check if the database connection is alive by running SELECT 1."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                return cur.fetchone()[0] == 1
    except Exception:
        return False


def get_all_tasks() -> List[Dict[str, Any]]:
    """Retrieve all tasks ordered by ID."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, title, done FROM tasks ORDER BY id ASC;")
            rows = cur.fetchall()
            return [{"id": row[0], "title": row[1], "done": row[2]} for row in rows]


def get_task_by_id(task_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve a single task by ID using a parameterized query."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, title, done FROM tasks WHERE id = %s;", (task_id,))
            row = cur.fetchone()
            if row:
                return {"id": row[0], "title": row[1], "done": row[2]}
            return None


def create_task(title: str) -> Dict[str, Any]:
    """Insert a new task and return the created record."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO tasks (title, done) VALUES (%s, FALSE) RETURNING id, title, done;",
                (title,),
            )
            row = cur.fetchone()
            conn.commit()
            return {"id": row[0], "title": row[1], "done": row[2]}


def update_task(
    task_id: int, title: Optional[str] = None, done: Optional[bool] = None
) -> Optional[Dict[str, Any]]:
    """Update title and/or done status for a task, preserving omitted fields."""
    if title is None and done is None:
        return None

    set_clauses = []
    params = []

    if title is not None:
        set_clauses.append("title = %s")
        params.append(title)
    if done is not None:
        set_clauses.append("done = %s")
        params.append(done)

    params.append(task_id)
    query = f"UPDATE tasks SET {', '.join(set_clauses)} WHERE id = %s RETURNING id, title, done;"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, tuple(params))
            row = cur.fetchone()
            conn.commit()
            if row:
                return {"id": row[0], "title": row[1], "done": row[2]}
            return None


def delete_task(task_id: int) -> bool:
    """Delete a task by ID. Returns True if a row was deleted, False otherwise."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM tasks WHERE id = %s RETURNING id;", (task_id,))
            row = cur.fetchone()
            conn.commit()
            return row is not None


def reset_tasks() -> None:
    """Helper to reset database to initial state (useful for test suites & demos)."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE tasks RESTART IDENTITY;")
            cur.executemany(
                "INSERT INTO tasks (title, done) VALUES (%s, %s);",
                [
                    ("Review assignment requirements", True),
                    ("Implement CRUD endpoints", False),
                    ("Write automated test cases", False),
                ],
            )
        conn.commit()
