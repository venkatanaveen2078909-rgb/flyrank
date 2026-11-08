from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

from src.llm.client import triage_message
from src.llm.schema import TriageInput, TriageOutput
import repository


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database tables and seed rows on startup."""
    try:
        repository.init_db()
        print("Connected to PostgreSQL and verified tasks table.")
    except Exception as e:
        print(f"Warning: Could not connect to PostgreSQL on startup ({e}). Ensure DB container is running.")
    yield


app = FastAPI(
    title="Task API",
    description="Containerized PostgreSQL CRUD API - FlyRank BE-01 / W1 Assignment A3",
    version="1.0",
    lifespan=lifespan,
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Translate Pydantic validation errors (default 422) into HTTP 400 Bad Request."""
    first_error = exc.errors()[0]
    error_msg = first_error.get("msg", "Invalid request body")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"error": f"Validation error: {error_msg}"},
    )


@app.exception_handler(HTTPException)
async def custom_http_exception_handler(
    request: Request, exc: HTTPException
) -> JSONResponse:
    """Ensure all HTTP exceptions return a uniform {"error": detail} JSON response."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail},
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
    """Health check endpoint checking server and PostgreSQL status."""
    db_healthy = repository.check_db_health()
    return {
        "status": "ok",
        "db": "ok" if db_healthy else "disconnected",
    }


@app.get("/tasks", response_model=List[Task], tags=["Tasks"])
def get_tasks() -> List[Dict[str, Any]]:
    """Return all tasks from PostgreSQL."""
    return repository.get_all_tasks()


@app.get(
    "/tasks/{task_id}",
    response_model=Task,
    responses={
        404: {
            "description": "Task not found",
            "content": {"application/json": {"example": {"error": "Task not found"}}},
        }
    },
    tags=["Tasks"],
)
def get_task(task_id: int) -> Dict[str, Any]:
    """Return a single task by ID from PostgreSQL."""
    task = repository.get_task_by_id(task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    return task


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
    """Insert a new task into PostgreSQL with done=False."""
    return repository.create_task(task_in.title)


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
            "content": {"application/json": {"example": {"error": "Task not found"}}},
        },
    },
    tags=["Tasks"],
)
def update_task(task_id: int, task_in: TaskUpdate) -> Dict[str, Any]:
    """Update task title and/or done status in PostgreSQL, preserving omitted fields."""
    if task_in.title is None and task_in.done is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one field ('title' or 'done') must be provided for update",
        )

    updated_task = repository.update_task(task_id, task_in.title, task_in.done)
    if updated_task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    return updated_task


@app.delete(
    "/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        404: {
            "description": "Task not found",
            "content": {"application/json": {"example": {"error": "Task not found"}}},
        }
    },
    tags=["Tasks"],
)
def delete_task(task_id: int) -> None:
    """Delete a task by ID from PostgreSQL. Returns 204 No Content with empty body."""
    deleted = repository.delete_task(task_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    return None


@app.post(
    "/triage",
    response_model=TriageOutput,
    status_code=status.HTTP_200_OK,
    responses={
        400: {
            "description": "Validation error on input",
            "content": {"application/json": {"example": {"error": "Validation error: Support message text cannot be empty"}}},
        },
        422: {
            "description": "Model output unprocessable",
            "content": {"application/json": {"example": {"error": "Model output could not be validated against schema"}}},
        },
        504: {
            "description": "LLM Provider Timeout",
            "content": {"application/json": {"example": {"error": "LLM model request timed out after 30 seconds"}}},
        },
    },
    tags=["LLM Triage"],
)
def triage_support_ticket(payload: TriageInput) -> TriageOutput:
    """Classify incoming customer support messages into closed categories with an LLM."""
    return triage_message(payload.text)
