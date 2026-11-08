from typing import Any, Dict, List
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI(title="Task API", version="1.0")

class Task(BaseModel):
    id: int
    title: str
    done: bool

tasks: List[Dict[str, Any]] = [
    {"id": 1, "title": "Review assignment requirements", "done": True},
    {"id": 2, "title": "Implement CRUD endpoints", "done": False},
    {"id": 3, "title": "Write automated test cases", "done": False},
]

@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})

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
