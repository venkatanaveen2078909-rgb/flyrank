import pytest
from fastapi.testclient import TestClient
from main import app
import repository

client = TestClient(app)

# In-memory mock store used if local Postgres is not running during test execution
_mock_tasks = []

def _reset_mock():
    global _mock_tasks
    _mock_tasks = [
        {"id": 1, "title": "Review assignment requirements", "done": True},
        {"id": 2, "title": "Implement CRUD endpoints", "done": False},
        {"id": 3, "title": "Write automated test cases", "done": False},
    ]

@pytest.fixture(autouse=True)
def setup_db(monkeypatch):
    """Set up DB before each test. Uses live Postgres if available, falls back to in-memory store."""
    if repository.check_db_health():
        repository.reset_tasks()
        yield
        repository.reset_tasks()
    else:
        # Fallback in-memory mock for repository when Docker Postgres is offline
        _reset_mock()

        def mock_get_all():
            return list(_mock_tasks)

        def mock_get_by_id(task_id: int):
            for t in _mock_tasks:
                if t["id"] == task_id:
                    return t
            return None

        def mock_create(title: str):
            next_id = max([t["id"] for t in _mock_tasks], default=0) + 1
            new_task = {"id": next_id, "title": title, "done": False}
            _mock_tasks.append(new_task)
            return new_task

        def mock_update(task_id: int, title=None, done=None):
            for t in _mock_tasks:
                if t["id"] == task_id:
                    if title is not None:
                        t["title"] = title
                    if done is not None:
                        t["done"] = done
                    return t
            return None

        def mock_delete(task_id: int):
            for i, t in enumerate(_mock_tasks):
                if t["id"] == task_id:
                    _mock_tasks.pop(i)
                    return True
            return False

        monkeypatch.setattr(repository, "get_all_tasks", mock_get_all)
        monkeypatch.setattr(repository, "get_task_by_id", mock_get_by_id)
        monkeypatch.setattr(repository, "create_task", mock_create)
        monkeypatch.setattr(repository, "update_task", mock_update)
        monkeypatch.setattr(repository, "delete_task", mock_delete)
        yield
        _reset_mock()


def test_root_endpoint():
    """1. GET / returns correct API metadata."""
    res = client.get("/")
    assert res.status_code == 200
    assert res.json() == {"name": "Task API", "version": "1.0", "endpoints": ["/tasks"]}


def test_health_endpoint():
    """2. GET /health returns status ok."""
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_get_tasks():
    """3. GET /tasks returns initial three seeded tasks."""
    res = client.get("/tasks")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 3
    assert data[0]["id"] == 1
    assert data[1]["id"] == 2
    assert data[2]["id"] == 3


def test_get_task_by_id():
    """4. GET /tasks/{id} returns an existing task."""
    res = client.get("/tasks/1")
    assert res.status_code == 200
    assert res.json()["id"] == 1
    assert res.json()["title"] == "Review assignment requirements"
    assert res.json()["done"] is True


def test_get_task_not_found():
    """5. GET /tasks/{id} with unknown ID returns 404."""
    res = client.get("/tasks/999")
    assert res.status_code == 404
    assert res.json() == {"error": "Task not found"}


def test_create_task_success():
    """6. POST /tasks creates a task with 201 Created and done=False."""
    res = client.post("/tasks", json={"title": "Buy milk"})
    assert res.status_code == 201
    created = res.json()
    assert created["id"] == 4
    assert created["title"] == "Buy milk"
    assert created["done"] is False


def test_create_task_validation():
    """7. POST /tasks with missing, empty, or whitespace title returns 400."""
    assert client.post("/tasks", json={}).status_code == 400
    assert client.post("/tasks", json={"title": ""}).status_code == 400
    assert client.post("/tasks", json={"title": "   "}).status_code == 400


def test_update_task_success():
    """8. PUT /tasks/{id} updates title and/or done status."""
    res = client.put("/tasks/1", json={"title": "Updated title", "done": False})
    assert res.status_code == 200
    assert res.json()["title"] == "Updated title"
    assert res.json()["done"] is False


def test_update_task_preserves_omitted_fields():
    """9. PUT /tasks/{id} preserves fields not passed in request."""
    res = client.put("/tasks/2", json={"done": True})
    assert res.status_code == 200
    assert res.json()["title"] == "Implement CRUD endpoints"
    assert res.json()["done"] is True


def test_update_task_validation():
    """10. PUT /tasks/{id} with empty body returns 400."""
    assert client.put("/tasks/1", json={}).status_code == 400
    assert client.put("/tasks/1", json={"title": ""}).status_code == 400


def test_update_and_delete_unknown_id_404():
    """11. PUT and DELETE with unknown ID return 404."""
    assert client.put("/tasks/999", json={"title": "Ghost"}).status_code == 404
    assert client.delete("/tasks/999").status_code == 404


def test_delete_task_success():
    """12. DELETE /tasks/{id} returns 204 with empty response body."""
    res = client.delete("/tasks/2")
    assert res.status_code == 204
    assert res.content == b""
    assert client.get("/tasks/2").status_code == 404


def test_full_crud_cycle():
    """13. Complete CRUD cycle passes end-to-end."""
    # Create
    c_res = client.post("/tasks", json={"title": "Containerize API"})
    assert c_res.status_code == 201
    new_id = c_res.json()["id"]

    # Read
    r_res = client.get(f"/tasks/{new_id}")
    assert r_res.status_code == 200
    assert r_res.json()["title"] == "Containerize API"

    # Update
    u_res = client.put(f"/tasks/{new_id}", json={"done": True})
    assert u_res.status_code == 200
    assert u_res.json()["done"] is True

    # Delete
    d_res = client.delete(f"/tasks/{new_id}")
    assert d_res.status_code == 204
    assert d_res.content == b""

    # Verify Deletion
    v_res = client.get(f"/tasks/{new_id}")
    assert v_res.status_code == 404


def test_docs_and_openapi_schema():
    """14. OpenAPI schema and Swagger UI /docs are accessible."""
    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").status_code == 200
