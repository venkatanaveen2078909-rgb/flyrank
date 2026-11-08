# AI-Generated Version (Quarantine folder for Stage 6: AI Rematch)
# Notice Bug 1: Hardcoded DB credentials in code instead of reading from .env
# Notice Bug 2: Raw string interpolation without parameterized queries (%s)

import psycopg

DATABASE_URL = "postgres://postgres:password123@localhost:5432/tasks"

def get_tasks():
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM tasks")
            return cur.fetchall()

def get_task(task_id):
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            # Vulnerable to SQL injection: formatted string query
            cur.execute(f"SELECT * FROM tasks WHERE id = {task_id}")
            return cur.fetchone()
