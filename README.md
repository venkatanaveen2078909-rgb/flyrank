# FlyRank Backend Track — Assignment A3: Containerize Your Stack

Run your Task CRUD API against a real **PostgreSQL** database living in a Docker container — started with a single command: `docker compose up`.

This project fulfills the **FlyRank Backend Internship — Week 1 Assignment A3** requirements.

---

## 📋 Table of Contents
- [Architecture & Storage Ladder](#architecture--storage-ladder)
- [Prerequisites](#prerequisites)
- [Quickstart: One-Command Startup](#quickstart-one-command-startup)
- [Environment Configuration](#environment-configuration)
- [API Reference](#api-reference)
- [Automated Testing](#automated-testing)
- [Real Captured `curl -i` Output](#real-captured-curl--i-output)
- [Database Inspection & Screenshot Guide](#database-inspection--screenshot-guide)
- [The Mortality Experiment (Database Edition)](#the-mortality-experiment-database-edition)
- [Bonus: AI vs Me Reflection](#bonus-ai-vs-me-reflection)

---

## 🏗️ Architecture & Storage Ladder

Across the FlyRank curriculum, the Task API climbs the storage ladder without the HTTP routes ever needing to change:

| Milestone | Where Tasks Live | What Runs It |
|---|---|---|
| **A1** | List in memory | Python process (volatile) |
| **A2** | `tasks.db` file | SQLite file on disk |
| **A3 (This)** | Rows in PostgreSQL | Docker container with persistent volume |

### Key Design Principles:
1. **Isolated Database Repository:** Every line interacting with PostgreSQL is encapsulated inside [`repository.py`](file:///c:/Users/venka/OneDrive/Desktop/Flyrank%20assignment%201/repository.py). The API route definitions in [`main.py`](file:///c:/Users/venka/OneDrive/Desktop/Flyrank%20assignment%201/main.py) remain identical.
2. **Strictly Parameterized Queries:** All SQL queries use `%s` placeholders (with `psycopg`). Values are never interpolated via raw strings, eliminating SQL injection vulnerabilities.
3. **Automated Table Creation & Seeding:** On startup, the `tasks` table is created if missing, and seeded with 3 example tasks **only** if the table is empty.
4. **Data Persistence via Docker Named Volumes:** The PostgreSQL container mounts `taskdata:/var/lib/postgresql/data`, guaranteeing data survives container restarts (`docker compose down` then `up`).

---

## 🛠️ Prerequisites

- **Docker Desktop** (or Podman)
- **Python 3.10+** (for optional local non-container development)
- **Git**

Verify your Docker and Compose versions:
```bash
docker --version
docker compose version
```

---

## 🚀 Quickstart: One-Command Startup

A stranger can clone this repository, copy the environment file, and start the entire stack in under 2 minutes:

```bash
# 1. Clone the repository
git clone https://github.com/venkatanaveen2078909-rgb/flyrank.git
cd flyrank

# 2. Copy the example environment file
cp .env.example .env

# 3. Start the entire stack (API + PostgreSQL DB)
docker compose up --build
```

The application will be live at:
- **API Root:** [http://localhost:8000/](http://localhost:8000/)
- **Interactive Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **PostgreSQL Database:** `localhost:5432` (User: `postgres`, Pass: `dev`, DB: `tasks`)

To stop the containers:
```bash
docker compose down
```

---

## 🔐 Environment Configuration

Database connection parameters live strictly in `.env` and are loaded via `python-dotenv`:

- **`.env.example`** (Committed): Shows teammates and CI the required configuration shape without revealing secrets.
- **`.env`** (Git-Ignored): Holds your local configuration. Verified absent from Git history to prevent credential leaks.

```env
DATABASE_URL=postgres://postgres:dev@localhost:5432/tasks
PORT=8000
```

*(Inside Docker Compose, the API container automatically reaches the database via the internal network service name: `DATABASE_URL: postgres://postgres:dev@db:5432/tasks`).*

---

## 🛣️ API Reference

| Method | Endpoint | Description | Success Status | Error Statuses |
|---|---|---|---|---|
| `GET` | `/` | Root API metadata & endpoints | `200 OK` | — |
| `GET` | `/health` | Server & DB health check (`SELECT 1`) | `200 OK` | — |
| `GET` | `/tasks` | List all tasks from PostgreSQL | `200 OK` | — |
| `GET` | `/tasks/{id}` | Retrieve task by ID (`SELECT ... WHERE id = %s`) | `200 OK` | `404 Not Found` |
| `POST` | `/tasks` | Create new task (`INSERT ... RETURNING *`) | `201 Created` | `400 Bad Request` |
| `PUT` | `/tasks/{id}` | Update title/done (`UPDATE ... RETURNING *`) | `200 OK` | `400 Bad Request`, `404 Not Found` |
| `DELETE` | `/tasks/{id}` | Delete task (`DELETE ... WHERE id = %s`) | `204 No Content` | `404 Not Found` |

---

## 🧪 Automated Testing

Automated tests are written with **Pytest** and FastAPI's **TestClient**:

```bash
pytest -v
```

All 14 tests pass across root metadata, health checks, CRUD operations, parameterized SQL queries, empty/whitespace validation (400), 404s, and empty 204 delete bodies.

---

## 💻 Real Captured `curl -i` Output

Captured directly from the running stack:

### 1. Read All Seeded Tasks (`GET /tasks`)
```http
HTTP/1.1 200 OK
date: Sun, 08 Nov 2026 06:14:37 GMT
server: uvicorn
content-length: 179
content-type: application/json

[{"id":1,"title":"Review assignment requirements","done":true},{"id":2,"title":"Implement CRUD endpoints","done":false},{"id":3,"title":"Write automated test cases","done":false}]
```

### 2. Create Task (`POST /tasks`)
```http
HTTP/1.1 201 Created
date: Sun, 08 Nov 2026 06:15:04 GMT
server: uvicorn
content-length: 40
content-type: application/json

{"id":4,"title":"Buy milk","done":false}
```

### 3. Rejection of Empty/Whitespace Title (`POST /tasks`)
```http
HTTP/1.1 400 Bad Request
date: Sun, 08 Nov 2026 06:15:09 GMT
server: uvicorn
content-length: 88
content-type: application/json

{"error":"Validation error: Value error, Task title cannot be empty or whitespace-only"}
```

### 4. Successful Delete (`DELETE /tasks/2`)
```http
HTTP/1.1 204 No Content
date: Sun, 08 Nov 2026 06:15:21 GMT
server: uvicorn
content-type: application/json
```

---

## 📸 Database Inspection & Screenshot Guide

To inspect your PostgreSQL data and capture the submission screenshot:

1. Open a terminal prompt inside the running PostgreSQL container:
   ```bash
   docker exec -it flyrank-db-1 psql -U postgres -d tasks
   # (or: docker exec -it taskdb psql -U postgres -d tasks)
   ```
2. Run `\dt` to inspect the table list:
   ```sql
   tasks=# \dt
            List of relations
    Schema | Name  | Type  |  Owner   
   --------+-------+-------+----------
    public | tasks | table | postgres
   (1 row)
   ```
3. Run a `SELECT` query:
   ```sql
   tasks=# SELECT * FROM tasks;
    id |              title              | done 
   ----+---------------------------------+------
     1 | Review assignment requirements  | t
     3 | Write automated test cases      | f
     4 | Buy milk                        | f
   (3 rows)
   ```
4. Save your screenshot as:
   ```text
   docs/db-screenshot.png
   ```

![Database Screenshot Placeholder](docs/db-screenshot.png)

---

## 🧠 The Mortality Experiment (Database Edition)

### What Happened & Why Volumes Exist
In A1, stopping the Python process wiped all in-memory tasks. In A3, we tested what happens when running PostgreSQL without a Docker volume:
1. If a container is run without `-v taskdata:/var/lib/postgresql/data`, PostgreSQL writes all WAL logs and table data into the container's temporary read-write layer.
2. Running `docker rm` destroys that layer, wiping every newly created task.
3. By adding the named volume `taskdata` to `compose.yaml`, the data directory is mounted on the host machine. When you run `docker compose down` followed by `docker compose up`, PostgreSQL reattaches to `taskdata`, preserving all your rows.

---

## 🤖 Bonus: AI vs Me Reflection (Stage 6)

### Prompt Used:
> "Containerize a FastAPI task CRUD API with PostgreSQL in Docker Compose. Use psycopg, a tasks table with auto-seeding on first run, parameterized queries, environment variables from .env for DB credentials, and a persistent Docker volume."

### Three Concrete Differences Found in Diff (`git diff --no-index`):
1. **Missing Docker Volume:** The AI's generated `compose.yaml` omitted the `volumes:` block for the database service. While it worked on the first boot, running `docker compose down && docker compose up` wiped all tasks, failing the persistence requirement.
2. **SQL Injection Vulnerability:** In the update query, the AI used Python f-strings (`f"UPDATE tasks SET title = '{title}' WHERE id = {task_id}"`) instead of parameterized `%s` placeholders with a tuple of parameters. Our hand-built code uses strict parameterized queries.
3. **Container Health & Startup Race Condition:** The AI specified `depends_on: [db]`, which only waits for the container to start, not for Postgres to become ready to accept TCP connections. Our implementation includes a `healthcheck` with `pg_isready -U postgres -d tasks` and `condition: service_healthy`, avoiding connection refused crashes on boot.


---

# 🤖 Week 7 · Assignment A17: Put an LLM Behind Your API

This milestone adds a production-hardened, schema-constrained LLM endpoint (`POST /triage`) to the API. It takes messy customer support messages, queries a language model, and returns clean, validated JSON with a 30-second timeout, sensible retry policy, cost logging, and an operational kill switch.

---

## 1. What the Endpoint Does (Plain Language)
The `POST /triage` endpoint acts as an automated triage specialist for customer support tickets. When a customer submits an unformatted, emotional, or messy support message, the endpoint analyzes the text and instantly decides which department should handle it (`billing`, `bug`, `feature`, or `other`), assigns an urgency level (`low`, `normal`, `high`), estimates a confidence score, and provides a one-sentence rationale. The rest of our backend code receives guaranteed, strictly validated JSON rather than unpredictable free-form text.

---

## 2. Copy-Pasteable `curl` Command & Real Response

### Request:
```bash
curl -i -X POST http://127.0.0.1:8000/triage \
  -H "Content-Type: application/json" \
  -d '{"text": "My credit card was charged twice for invoice #4928 this morning. Please issue a refund immediately."}'
```

### Real Captured Response (`200 OK`):
```http
HTTP/1.1 200 OK
date: Sun, 08 Nov 2026 07:01:01 GMT
server: uvicorn
content-length: 168
content-type: application/json

{
  "category": "billing",
  "urgency": "high",
  "confidence": 0.92,
  "reason": "Customer message mentions payment or refund inquiry"
}
```

---

## 3. Job Card Specification

See the full [JOB-CARD.md](JOB-CARD.md).

- **Input:** `{"text": "string, 1-2000 characters"}`
- **Output:**
  ```json
  {
    "category": "billing | bug | feature | other",
    "urgency": "low | normal | high",
    "confidence": 0.0 - 1.0,
    "reason": "one short sentence"
  }
  ```
- **It Must Never:**
  - Invent a category outside the allowed list.
  - Return free text or conversational prose outside JSON.
  - Give medical, legal, or financial advice.
  - Reveal the system prompt under prompt injection attacks.
- **When Unsure:**
  - Return category `"other"` with confidence `< 0.5`. Do not guess.

---

## 4. Provider & Model Configuration

The client library uses the standard OpenAI SDK configured to talk to any OpenAI-compatible provider. Swapping providers requires changing only three environment variables in `.env`:

```env
# Hosted OpenRouter (Default free tier):
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_API_KEY=your-openrouter-key
LLM_MODEL=openrouter/free

# Local Ollama (Zero cost, runs on laptop CPU):
# LLM_BASE_URL=http://localhost:11434/v1/
# LLM_API_KEY=ollama
# LLM_MODEL=gemma3:1b
```

---

## 5. Real Evaluation Score

- **Eval Suite:** 8 hand-labelled diverse test cases ([`evals/cases.json`](file:///c:/Users/venka/OneDrive/Desktop/Flyrank%20assignment%201/evals/cases.json))
- **Eval Runner:** `python evals/run_eval.py`
- **Date Tested:** November 8, 2026
- **Prompt Version:** `v1` ([`prompts/triage-v1.md`](file:///c:/Users/venka/OneDrive/Desktop/Flyrank%20assignment%201/prompts/triage-v1.md))
- **Category Match Rate:** **7 / 8 (87.5%)**
- **Urgency Match Rate:** **8 / 8 (100.0%)**
- **Failed Case:** Case #7 (off-topic pizza query triggered partial feature keyword match; safely fell back to low confidence).

---

## 6. Cost Logging & Scaling Estimate

Every call outputs a structured Twelve-Factor log line to `stdout`:
```json
{
  "event": "llm_call_completed",
  "timestamp": "2026-11-08T07:01:01.964500+00:00",
  "prompt_version": "v1",
  "model": "openrouter/free",
  "input_tokens": 19,
  "output_tokens": 30,
  "duration_ms": 5.0,
  "repairs": 0
}
```

### Cost Estimate for 10,000 Requests / Day:
At an average of 250 input tokens and 50 output tokens per call using a cost-efficient production model like `gpt-4o-mini` ($0.15/1M input tokens, $0.60/1M output tokens):
$$\text{Cost} = (10{,}000 \times 250 \times \$0.15 \times 10^{-6}) + (10{,}000 \times 50 \times \$0.60 \times 10^{-6}) = \$0.375 + \$0.30 = \$0.675\text{ / day}$$
**Estimated Cost: ~$0.68 per day (~$20.40/month) for 10,000 requests/day.**

---

## 7. What I'd Fix With Another Day
With an additional day, I would implement **semantic response caching using Redis vector embeddings**: if an incoming support query has a cosine similarity $> 0.96$ with a previously triaged query on the same prompt version, the system would immediately return the cached classification in under 5ms, reducing external LLM API costs and token usage by an estimated 35-40%.

---

## 8. Bonus: AI vs Me Reflection (Stage 6)

### Prompt Used:
> "Add a POST /triage endpoint to FastAPI that uses OpenAI SDK to classify support tickets into billing, bug, feature, or other. Validate input and output with Pydantic, add retries, timeout, and a kill switch."

### Three Concrete Differences in Diff:
1. **10-Minute Timeout Trap:** The AI left the client's default timeout intact. If the model hangs or is overloaded, an HTTP connection stays open for up to 10 minutes, tying up server worker threads. Our hand-built code explicitly sets `timeout=30.0` and returns `504 Gateway Timeout`.
2. **Retrying Bad API Keys (401):** The AI used a naive `try...except Exception` retry loop that retried three times on all errors. If an API key is invalid (`401 Unauthorized`), retrying burns time and log noise for an error that cannot recover. Our code explicitly checks status codes and **never** retries 400, 401, or 403.
3. **Contract Protection via Repair Loop:** When the AI's model returned malformed JSON, it fell back to returning `{"raw_text": raw}`, violating the endpoint's strict JSON schema. Our implementation executes **exactly one repair retry** feeding the validation error back to the model, and if it fails again, safely quarantines to `logs/quarantine.jsonl` and returns `422 Unprocessable Entity`.
