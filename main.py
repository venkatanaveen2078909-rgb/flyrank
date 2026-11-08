from typing import Any, Dict
from fastapi import FastAPI

app = FastAPI(title="Task API", version="1.0")

@app.get("/")
def root() -> Dict[str, Any]:
    return {
        "name": "Task API",
        "version": "1.0",
        "endpoints": ["/tasks"],
    }

@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}
