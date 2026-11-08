from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

app = FastAPI(title="Task API", version="1.0")

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
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
    title: str = Field(...)

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Task title cannot be empty or whitespace-only")
        return v.strip()

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    done: Optional[bool] = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("Task title cannot be empty or whitespace-only")
        return v.strip() if v is not None else None

tasks: List[Dict[str, Any]] = [
    {"id": 1, "title": "Review assignment requirements", "done": True},
    {"id": 2, "title": "Implement CRUD endpoints", "done": False},
    {"id": 3, "title": "Write automated test cases", "done": False},
]

def get_next_id() -> int:
    if not tasks:
        return 1
    return max(task["id"] for task in tasks) + 1

@app.get("/")
def root() -> Dict[str, Any]:
    return {"name": "Task API", "version": "1.0", "endpoints": ["/tasks"]}

@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}

@app.get("/tasks", response_model=List[Task])
def get_tasks() -> List[Dict[str, Any]]:
    return tasks

@app.get("/tasks/{task_id}", response_model=Task)
def get_task(task_id: int) -> Dict[str, Any]:
    for task in tasks:
        if task["id"] == task_id:
            return task
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task {task_id} not found")

@app.post("/tasks", response_model=Task, status_code=status.HTTP_201_CREATED)
def create_task(task_in: TaskCreate) -> Dict[str, Any]:
    new_task = {"id": get_next_id(), "title": task_in.title, "done": False}
    tasks.append(new_task)
    return new_task

@app.put("/tasks/{task_id}", response_model=Task)
def update_task(task_id: int, task_in: TaskUpdate) -> Dict[str, Any]:
    target_task = None
    for task in tasks:
        if task["id"] == task_id:
            target_task = task
            break
    if target_task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task {task_id} not found")
    if task_in.title is None and task_in.done is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one field ('title' or 'done') must be provided for update")
    if task_in.title is not None:
        target_task["title"] = task_in.title
    if task_in.done is not None:
        target_task["done"] = task_in.done
    return target_task

@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int) -> None:
    for idx, task in enumerate(tasks):
        if task["id"] == task_id:
            tasks.pop(idx)
            return None
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task {task_id} not found")

@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})
