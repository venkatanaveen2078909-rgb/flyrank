from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator


app = FastAPI(
    title="Task API",
    description="In-memory CRUD API for tasks - FlyRank BE-01 Internship Assignment",
    version="1.0",
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Translate Pydantic validation errors (default 422) into HTTP 400 with a clean error message."""
    first_error = exc.errors()[0]
    error_msg = first_error.get("msg", "Invalid request body")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"error": f"Validation error: {error_msg}"},
    )


class Task(BaseModel):
    id: int
    title: str
    done: bool


class TaskCreate(BaseModel):
    title: str = Field(..., description="Title of the task (cannot be empty or whitespace-only)")

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Task title cannot be empty or whitespace-only")
        return v.strip()


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(
        default=None,
        description="Optional new title (cannot be empty or whitespace-only if provided)",
    )
    done: Optional[bool] = Field(
        default=None,
        description="Optional completion status",
    )

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("Task title cannot be empty or whitespace-only")
        return v.strip() if v is not None else None


# In-memory task list and helper functions to manage state cleanly
tasks: List[Dict[str, Any]] = []


def reset_tasks() -> None:
    """Reset tasks to initial state. Useful for startup and automated tests."""
    global tasks
    tasks = [
        {"id": 1, "title": "Review assignment requirements", "done": True},
        {"id": 2, "title": "Implement CRUD endpoints", "done": False},
        {"id": 3, "title": "Write automated test cases", "done": False},
    ]


# Initialize with the 3 required initial tasks
reset_tasks()


def get_next_id() -> int:
    """Generate the next unique ID safely without collision even if tasks are deleted."""
    if not tasks:
        return 1
    return max(task["id"] for task in tasks) + 1


@app.get("/", tags=["General"])
def root() -> Dict[str, Any]:
    """Root endpoint returning API metadata."""
    return {
        "name": "Task API",
        "version": "1.0",
        "endpoints": ["/tasks"],
    }


@app.get("/health", tags=["General"])
def health() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/tasks", response_model=List[Task], tags=["Tasks"])
def get_tasks(
    done: Optional[bool] = None,
    search: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return the list of tasks, with optional filtering by 'done' status or title search."""
    result = tasks
    if done is not None:
        result = [t for t in result if t["done"] == done]
    if search is not None:
        term = search.strip().lower()
        result = [t for t in result if term in t["title"].lower()]
    return result


@app.get(
    "/tasks/{task_id}",
    response_model=Task,
    responses={
        404: {
            "description": "Task not found",
            "content": {"application/json": {"example": {"error": "Task 99 not found"}}},
        }
    },
    tags=["Tasks"],
)
def get_task(task_id: int) -> Dict[str, Any]:
    """Return a single task by ID."""
    for task in tasks:
        if task["id"] == task_id:
            return task
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Task {task_id} not found",
    )


@app.post(
    "/tasks",
    response_model=Task,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {
            "description": "Validation error",
            "content": {"application/json": {"example": {"error": "Validation error: Task title cannot be empty"}}},
        }
    },
    tags=["Tasks"],
)
def create_task(task_in: TaskCreate) -> Dict[str, Any]:
    """Create a new task with auto-generated ID and done=False."""
    new_task = {
        "id": get_next_id(),
        "title": task_in.title,
        "done": False,
    }
    tasks.append(new_task)
    return new_task


@app.put(
    "/tasks/{task_id}",
    response_model=Task,
    responses={
        400: {
            "description": "Invalid update body",
            "content": {"application/json": {"example": {"error": "At least one field ('title' or 'done') must be provided for update"}}},
        },
        404: {
            "description": "Task not found",
            "content": {"application/json": {"example": {"error": "Task 99 not found"}}},
        },
    },
    tags=["Tasks"],
)
def update_task(task_id: int, task_in: TaskUpdate) -> Dict[str, Any]:
    """Update an existing task's title and/or done status."""
    target_task: Optional[Dict[str, Any]] = None
    for task in tasks:
        if task["id"] == task_id:
            target_task = task
            break

    if target_task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )

    # Check if empty update body (no fields provided)
    if task_in.title is None and task_in.done is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one field ('title' or 'done') must be provided for update",
        )

    # Update only provided fields (preserve omitted fields)
    if task_in.title is not None:
        target_task["title"] = task_in.title
    if task_in.done is not None:
        target_task["done"] = task_in.done

    return target_task


@app.delete(
    "/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        404: {
            "description": "Task not found",
            "content": {"application/json": {"example": {"error": "Task 99 not found"}}},
        }
    },
    tags=["Tasks"],
)
def delete_task(task_id: int) -> None:
    """Delete a task by ID. Returns HTTP 204 with an empty body on success."""
    for idx, task in enumerate(tasks):
        if task["id"] == task_id:
            tasks.pop(idx)
            return None
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Task {task_id} not found",
    )


# Optional Extras (Page 5 of FlyRank assignment)
@app.get("/stats", tags=["Extras"])
def get_stats() -> Dict[str, int]:
    """Calculate and return task statistics (total, completed, open)."""
    total = len(tasks)
    done_count = sum(1 for t in tasks if t["done"])
    return {
        "total": total,
        "done": done_count,
        "open": total - done_count,
    }


@app.post("/reset", tags=["Extras"])
def reset_tasks_endpoint() -> Dict[str, Any]:
    """Reset tasks back to the 3 initial example tasks."""
    reset_tasks()
    return {"message": "Tasks reset to initial state", "tasks": tasks}


# Custom HTTPException handler to ensure consistent {"error": "..."} response format
@app.exception_handler(HTTPException)
async def custom_http_exception_handler(
    request: Request, exc: HTTPException
) -> JSONResponse:
    """Ensure all HTTP exceptions return a uniform {"error": detail} JSON response."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail},
    )
