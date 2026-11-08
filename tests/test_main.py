import pytest
from fastapi.testclient import TestClient
from main import app, reset_tasks


@pytest.fixture(autouse=True)
def run_around_tests():
    """Reset tasks in memory before every single test to guarantee test isolation."""
    reset_tasks()
    yield
    reset_tasks()


client = TestClient(app)


def test_root_endpoint():
    """1. The root endpoint returns the correct API metadata."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Task API"
    assert data["version"] == "1.0"
    assert data["endpoints"] == ["/tasks"]


def test_health_endpoint():
    """2. The health endpoint returns {'status': 'ok'}."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_get_tasks():
    """3. GET /tasks returns the initial three tasks."""
    response = client.get("/tasks")
    assert response.status_code == 200
    tasks = response.json()
    assert len(tasks) == 3
    assert tasks[0]["id"] == 1
    assert tasks[1]["id"] == 2
    assert tasks[2]["id"] == 3


def test_get_task_by_id():
    """4. GET /tasks/{id} returns an existing task."""
    response = client.get("/tasks/1")
    assert response.status_code == 200
    task = response.json()
    assert task["id"] == 1
    assert task["title"] == "Review assignment requirements"
    assert task["done"] is True


def test_get_task_not_found():
    """5. An unknown task ID returns 404 and the expected JSON error."""
    response = client.get("/tasks/99")
    assert response.status_code == 404
    assert response.json() == {"error": "Task 99 not found"}


def test_create_task_success():
    """6. POST creates a task with the next ID and returns 201."""
    response = client.post("/tasks", json={"title": "Buy milk"})
    assert response.status_code == 201
    created = response.json()
    assert created["id"] == 4
    assert created["title"] == "Buy milk"
    assert created["done"] is False

    # Verify task was added to task list
    list_res = client.get("/tasks")
    assert len(list_res.json()) == 4


def test_create_task_validation_errors():
    """7. POST with a missing, empty, or whitespace-only title returns 400."""
    # Empty title
    r1 = client.post("/tasks", json={"title": ""})
    assert r1.status_code == 400
    assert "error" in r1.json()

    # Whitespace-only title
    r2 = client.post("/tasks", json={"title": "   "})
    assert r2.status_code == 400
    assert "error" in r2.json()

    # Missing title field
    r3 = client.post("/tasks", json={})
    assert r3.status_code == 400
    assert "error" in r3.json()

    # Invalid JSON body structure (e.g. list instead of str)
    r4 = client.post("/tasks", json={"title": ["bad", "type"]})
    assert r4.status_code == 400
    assert "error" in r4.json()


def test_update_task_success():
    """8. PUT updates the title and/or done status."""
    # Update title only
    r1 = client.put("/tasks/1", json={"title": "Updated title"})
    assert r1.status_code == 200
    assert r1.json()["title"] == "Updated title"
    assert r1.json()["done"] is True  # Preserved

    # Update done status only
    r2 = client.put("/tasks/1", json={"done": False})
    assert r2.status_code == 200
    assert r2.json()["title"] == "Updated title"  # Preserved
    assert r2.json()["done"] is False

    # Update both
    r3 = client.put("/tasks/1", json={"title": "Final title", "done": True})
    assert r3.status_code == 200
    assert r3.json()["title"] == "Final title"
    assert r3.json()["done"] is True


def test_update_task_preserves_omitted_fields():
    """9. PUT preserves fields omitted from the update."""
    original = client.get("/tasks/2").json()
    assert original["title"] == "Implement CRUD endpoints"
    assert original["done"] is False

    response = client.put("/tasks/2", json={"done": True})
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == original["title"]
    assert data["done"] is True


def test_update_task_validation_errors():
    """10. PUT with an invalid body returns 400."""
    # Empty update body (no fields provided)
    r1 = client.put("/tasks/1", json={})
    assert r1.status_code == 400
    assert "error" in r1.json()

    # Empty title
    r2 = client.put("/tasks/1", json={"title": ""})
    assert r2.status_code == 400
    assert "error" in r2.json()

    # Whitespace-only title
    r3 = client.put("/tasks/1", json={"title": "   "})
    assert r3.status_code == 400
    assert "error" in r3.json()


def test_update_and_delete_unknown_id_404():
    """11. PUT and DELETE with an unknown ID return 404."""
    r_put = client.put("/tasks/999", json={"title": "Non-existent"})
    assert r_put.status_code == 404
    assert r_put.json() == {"error": "Task 999 not found"}

    r_del = client.delete("/tasks/999")
    assert r_del.status_code == 404
    assert r_del.json() == {"error": "Task 999 not found"}


def test_delete_task_success():
    """12. DELETE returns 204 with an empty response body."""
    response = client.delete("/tasks/2")
    assert response.status_code == 204
    assert response.content == b""

    # Verify task 2 no longer exists
    get_res = client.get("/tasks/2")
    assert get_res.status_code == 404

    # Verify task list length is 2
    tasks_res = client.get("/tasks")
    assert len(tasks_res.json()) == 2


def test_complete_crud_cycle():
    """13. The complete CRUD cycle works correctly."""
    # 1. CREATE
    create_res = client.post("/tasks", json={"title": "Walk the dog"})
    assert create_res.status_code == 201
    created_task = create_res.json()
    task_id = created_task["id"]
    assert created_task["title"] == "Walk the dog"
    assert created_task["done"] is False

    # 2. READ (all tasks)
    all_res = client.get("/tasks")
    assert any(t["id"] == task_id for t in all_res.json())

    # 3. READ (single task)
    single_res = client.get(f"/tasks/{task_id}")
    assert single_res.status_code == 200
    assert single_res.json()["title"] == "Walk the dog"

    # 4. UPDATE (title and done)
    update_res = client.put(f"/tasks/{task_id}", json={"title": "Walk the dog in the park", "done": True})
    assert update_res.status_code == 200
    assert update_res.json()["title"] == "Walk the dog in the park"
    assert update_res.json()["done"] is True

    # 5. DELETE
    delete_res = client.delete(f"/tasks/{task_id}")
    assert delete_res.status_code == 204
    assert delete_res.content == b""

    # 6. VERIFY DELETION
    verify_res = client.get(f"/tasks/{task_id}")
    assert verify_res.status_code == 404


def test_docs_and_openapi_schema():
    """14. /docs and the OpenAPI schema are available."""
    docs_res = client.get("/docs")
    assert docs_res.status_code == 200
    assert "Swagger UI" in docs_res.text

    openapi_res = client.get("/openapi.json")
    assert openapi_res.status_code == 200
    schema = openapi_res.json()
    assert "paths" in schema
    assert "/" in schema["paths"]
    assert "/health" in schema["paths"]
    assert "/tasks" in schema["paths"]
    assert "/tasks/{task_id}" in schema["paths"]


# -------------------------------------------------------------
# Optional Stretch Extras Tests (Page 5 of FlyRank assignment)
# -------------------------------------------------------------

def test_filtering_and_search_query_parameters():
    """Test GET /tasks?done=true and GET /tasks?search=endpoints."""
    # Filter by done=true (initial task 1 is done=True, tasks 2 and 3 are False)
    res_done = client.get("/tasks?done=true")
    assert res_done.status_code == 200
    assert len(res_done.json()) == 1
    assert res_done.json()[0]["id"] == 1

    # Filter by done=false
    res_false = client.get("/tasks?done=false")
    assert res_false.status_code == 200
    assert len(res_false.json()) == 2

    # Search in title
    res_search = client.get("/tasks?search=endpoints")
    assert res_search.status_code == 200
    assert len(res_search.json()) == 1
    assert res_search.json()[0]["id"] == 2


def test_stats_and_reset_endpoints():
    """Test GET /stats and POST /reset endpoints."""
    # Stats on initial tasks (1 done, 2 open, total 3)
    stats_res = client.get("/stats")
    assert stats_res.status_code == 200
    assert stats_res.json() == {"total": 3, "done": 1, "open": 2}

    # Add a task and delete another
    client.post("/tasks", json={"title": "Extra task"})
    client.delete("/tasks/1")
    assert len(client.get("/tasks").json()) == 3

    # Reset endpoint
    reset_res = client.post("/reset")
    assert reset_res.status_code == 200
    assert len(reset_res.json()["tasks"]) == 3
    assert client.get("/tasks/1").status_code == 200
