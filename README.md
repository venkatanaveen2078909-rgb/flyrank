# FlyRank BE-01 — Build Your First CRUD API

A clean, beginner-friendly RESTful CRUD (Create, Read, Update, Delete) Task Management API built with **Python 3.10+**, **FastAPI**, **Pydantic v2**, and **Pytest**. 

This project fulfills the **FlyRank Backend Internship — Week 2 Assignment A1** requirements.

---

## 📋 Table of Contents
- [Overview & Architecture](#overview--architecture)
- [Prerequisites](#prerequisites)
- [Installation & Setup](#installation--setup)
- [Running the Server](#running-the-server)
- [Interactive API Documentation (Swagger UI)](#interactive-api-documentation-swagger-ui)
- [API Endpoints](#api-endpoints)
- [Request & Response Examples](#request--response-examples)
- [Status Codes & Error Handling](#status-codes--error-handling)
- [Automated Testing](#automated-testing)
- [Real Captured `curl -i` Output](#real-captured-curl--i-output)
- [In-Memory Storage & The Mortality Experiment](#in-memory-storage--the-mortality-experiment)
- [Optional Stretch Features](#optional-stretch-features)
- [Bonus: AI vs Me Reflection](#bonus-ai-vs-me-reflection)

---

## 🔍 Overview & Architecture

This API manages an in-memory collection of tasks with three core fields:
- `id` (integer): Auto-generated unique identifier.
- `title` (string): Descriptive task title (strictly validated).
- `done` (boolean): Completion status (defaults to `false` on creation).

### Key Design Principles:
1. **Zero Database Dependency:** Data lives in an in-memory Python list, fulfilling the assignment boundary and keeping execution fast and lightweight.
2. **Strict Request Validation with HTTP 400:** FastAPI returns HTTP 422 by default for Pydantic validation errors. This API implements a custom `RequestValidationError` handler to return uniform **HTTP 400 Bad Request** responses with `{"error": "..."}` as required by the assignment specification.
3. **Collision-Free ID Generation:** IDs are generated dynamically via `max(task["id"]) + 1`, ensuring no duplicate IDs occur even after tasks are deleted.
4. **Partial Updates (Field Preservation):** `PUT /tasks/{id}` updates only the fields provided and preserves existing values for omitted fields.

---

## 🛠️ Prerequisites

- **Python 3.10+** (tested on Python 3.12)
- **Git**

Verify your installations:
```bash
python --version
git --version
```

---

## ⚙️ Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone <YOUR_REPOSITORY_URL>
   cd "Flyrank assignment 1"
   ```

2. **Create and activate a virtual environment:**
   - **Windows (PowerShell):**
     ```powershell
     python -m venv .venv
     .venv\Scripts\Activate.ps1
     ```
   - **macOS / Linux:**
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```

3. **Install dependencies:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

---

## 🚀 Running the Server

Start the API with **Uvicorn** using one documented command:

```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

The server starts at `http://127.0.0.1:8000`.

---

## 📖 Interactive API Documentation (Swagger UI)

FastAPI automatically generates an interactive OpenAPI documentation page.

- **Swagger UI:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Raw OpenAPI Schema:** [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json)

### Swagger UI Screenshot Placeholder
> Below is the interactive Swagger UI interface showing all endpoints and the "Try it out" feature:

![Swagger UI Screenshot](docs/swagger-ui.png)
*(Note: Replace `docs/swagger-ui.png` with your captured screenshot from `http://127.0.0.1:8000/docs`)*

---

## 🛣️ API Endpoints

| Method | Endpoint | Description | Success Status | Error Statuses |
|---|---|---|---|---|
| `GET` | `/` | Root API metadata & available endpoints | `200 OK` | — |
| `GET` | `/health` | Server health check | `200 OK` | — |
| `GET` | `/tasks` | List all tasks (supports `?done=` and `?search=`) | `200 OK` | — |
| `GET` | `/tasks/{id}` | Retrieve a specific task by ID | `200 OK` | `404 Not Found` |
| `POST` | `/tasks` | Create a new task (`done` defaults to `false`) | `201 Created` | `400 Bad Request` |
| `PUT` | `/tasks/{id}` | Update task title and/or done status | `200 OK` | `400 Bad Request`, `404 Not Found` |
| `DELETE` | `/tasks/{id}` | Delete a task (returns empty body) | `204 No Content` | `404 Not Found` |
| `GET` | `/stats` *(Extra)* | Task statistics (total, completed, open) | `200 OK` | — |
| `POST` | `/reset` *(Extra)* | Restore initial 3 example tasks | `200 OK` | — |

---

## 📦 Request & Response Examples

### 1. Root Endpoint (`GET /`)
**Response (`200 OK`):**
```json
{
  "name": "Task API",
  "version": "1.0",
  "endpoints": ["/tasks"]
}
```

### 2. Health Endpoint (`GET /health`)
**Response (`200 OK`):**
```json
{
  "status": "ok"
}
```

### 3. List All Tasks (`GET /tasks`)
**Response (`200 OK`):**
```json
[
  { "id": 1, "title": "Review assignment requirements", "done": true },
  { "id": 2, "title": "Implement CRUD endpoints", "done": false },
  { "id": 3, "title": "Write automated test cases", "done": false }
]
```

### 4. Create Task (`POST /tasks`)
**Request Body:**
```json
{
  "title": "Buy milk"
}
```
**Response (`201 Created`):**
```json
{
  "id": 4,
  "title": "Buy milk",
  "done": false
}
```

### 5. Update Task (`PUT /tasks/1`)
**Request Body:**
```json
{
  "title": "Review assignment requirements and checklist",
  "done": true
}
```
**Response (`200 OK`):**
```json
{
  "id": 1,
  "title": "Review assignment requirements and checklist",
  "done": true
}
```

### 6. Delete Task (`DELETE /tasks/2`)
**Response (`204 No Content`):**
*(Empty response body)*

---

## ⚠️ Status Codes & Error Handling

Standard HTTP status codes are strictly respected across all routes:

- **`200 OK`**: Successful read or update.
- **`201 Created`**: Successful creation via `POST /tasks`.
- **`204 No Content`**: Successful deletion via `DELETE /tasks/{id}` (empty body).
- **`400 Bad Request`**: Client validation errors (missing/empty/whitespace-only `title`, or empty `PUT` body).
- **`404 Not Found`**: Resource does not exist (e.g. unknown task ID).

### Consistent JSON Error Shape
All error responses return a uniform JSON structure:
```json
{
  "error": "Task 99 not found"
}
```

### Handling FastAPI's Default 422 vs 400
FastAPI default validation handlers emit HTTP 422 Unprocessable Entity. A dedicated exception handler overrides this behavior:
```python
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    first_error = exc.errors()[0]
    error_msg = first_error.get("msg", "Invalid request body")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"error": f"Validation error: {error_msg}"},
    )
```

---

## 🧪 Automated Testing

Automated tests are written with **Pytest** and FastAPI's **TestClient** (powered by HTTPX). Each test runs with an isolated in-memory reset fixture (`autouse=True`).

### Running the Test Suite:
```bash
pytest -v
```

### Test Coverage Checklist:
- [x] Root endpoint returns expected metadata (`GET /`).
- [x] Health endpoint returns `{"status": "ok"}` (`GET /health`).
- [x] Initial list contains 3 tasks (`GET /tasks`).
- [x] Single task retrieval works (`GET /tasks/1`).
- [x] Unknown task ID returns `404` with `{"error": "Task 99 not found"}`.
- [x] Creation returns `201` with incremented ID and `done: false`.
- [x] Rejection of empty, missing, or whitespace-only titles with `400`.
- [x] Updating task title and/or done status returns `200`.
- [x] Partial update preserves omitted fields.
- [x] Invalid / empty update body returns `400`.
- [x] Updating or deleting unknown ID returns `404`.
- [x] Deleting task returns `204` with completely empty body.
- [x] Full end-to-end CRUD cycle (Create -> Read -> Update -> Delete -> Verify).
- [x] Swagger UI (`/docs`) and OpenAPI schema (`/openapi.json`) are accessible.
- [x] Stretch features: query filtering, title search, `/stats`, and `/reset`.

---

## 💻 Real Captured `curl -i` Output

The following outputs were captured directly from the live running server:

### 1. Root Endpoint (`GET /`)
```http
HTTP/1.1 200 OK
date: Sun, 08 Nov 2026 04:14:08 GMT
server: uvicorn
content-length: 58
content-type: application/json

{"name":"Task API","version":"1.0","endpoints":["/tasks"]}
```

### 2. Read Single Task (`GET /tasks/1`)
```http
HTTP/1.1 200 OK
date: Sun, 08 Nov 2026 04:14:48 GMT
server: uvicorn
content-length: 61
content-type: application/json

{"id":1,"title":"Review assignment requirements","done":true}
```

### 3. Read Non-Existent Task (`GET /tasks/99`)
```http
HTTP/1.1 404 Not Found
date: Sun, 08 Nov 2026 04:14:48 GMT
server: uvicorn
content-length: 29
content-type: application/json

{"error":"Task 99 not found"}
```

### 4. Create Task (`POST /tasks`)
```http
HTTP/1.1 201 Created
date: Sun, 08 Nov 2026 04:15:04 GMT
server: uvicorn
content-length: 40
content-type: application/json

{"id":4,"title":"Buy milk","done":false}
```

### 5. Create Task with Whitespace Title (`POST /tasks`)
```http
HTTP/1.1 400 Bad Request
date: Sun, 08 Nov 2026 04:15:09 GMT
server: uvicorn
content-length: 88
content-type: application/json

{"error":"Validation error: Value error, Task title cannot be empty or whitespace-only"}
```

### 6. Delete Task (`DELETE /tasks/2`)
```http
HTTP/1.1 204 No Content
date: Sun, 08 Nov 2026 04:15:21 GMT
server: uvicorn
content-type: application/json
```

---

## 🧠 In-Memory Storage & The Mortality Experiment

### What Happened & Why
During the mortality experiment, several new tasks were created via `POST /tasks`, bringing the task list count up to 6 items. However, upon terminating the Uvicorn server (`Ctrl+C`) and restarting it, `GET /tasks` immediately reverted back to the original 3 seeded tasks.

### The Underlying Reason
Because the tasks are stored in a standard Python in-memory data structure (`tasks: List[Dict[str, Any]]`), the state lives solely in the volatile RAM allocated to the Python process. When the process exits, its entire address space is reclaimed by the operating system, erasing all modifications. This fundamental limitation highlights why production backend systems require a persistent database layer (such as PostgreSQL or SQLite).

---

## ✨ Optional Stretch Features

1. **Filtering by completion status (`GET /tasks?done=true` or `GET /tasks?done=false`):**
   Allows clients to retrieve only active or completed tasks using query parameters.
2. **Search by title (`GET /tasks?search=endpoints`):**
   Case-insensitive title substring matching.
3. **Stats endpoint (`GET /stats`):**
   Computes and returns `{"total": 3, "done": 1, "open": 2}`.
4. **Seed & reset endpoint (`POST /reset`):**
   Instantly restores the 3 initial tasks for effortless demos.

---

## 🤖 Bonus: AI vs Me Reflection (Stage 7)

### Prompt Used:
> "Build a beginner-friendly CRUD API in Python using FastAPI. Keep task data in an in-memory list initialized with 3 tasks (id, title, done). Support GET /, GET /health, GET /tasks, GET /tasks/{id}, POST /tasks, PUT /tasks/{id}, and DELETE /tasks/{id}. Status codes must strictly follow: 200 for reads/updates, 201 for create, 204 with empty body for delete, 400 for validation errors (missing/empty title or empty update body), and 404 for unknown task IDs. All errors must return a JSON object with key 'error'. Enable Swagger UI at /docs."

### Three Concrete Differences:
1. **HTTP 422 vs HTTP 400 Default Handling:**
   FastAPI out-of-the-box handles Pydantic validation failures by throwing `RequestValidationError` which defaults to HTTP 422. The AI assistant initially forgot to register an `@app.exception_handler(RequestValidationError)` and returned 422 until explicitly reminded to map it to 400.
2. **DELETE Response Body:**
   The AI assistant originally returned `{"message": "Task deleted"}` with status 200 or 204. However, the HTTP 204 specification strictly mandates **No Content** (an empty response body). Our hand-crafted implementation accurately returns `status_code=204` with a `None`/empty body.
3. **Collision-Safe ID Generation:**
   The AI used `len(tasks) + 1` to generate new task IDs. If task 2 is deleted from a 3-item list, `len(tasks) + 1` evaluates to 3, causing a duplicate key collision with existing task 3. Our implementation uses `max(task["id"]) + 1`, guaranteeing strictly unique IDs.
