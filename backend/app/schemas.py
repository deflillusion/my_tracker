from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class TaskFile(BaseModel):
    id: int
    file_path: str

    class Config:
        orm_mode = True


class TaskBase(BaseModel):
    title: str
    description: str
    priority: int = 1


class TaskCreate(TaskBase):
    pass


class Task(TaskBase):
    id: int
    is_done: bool
    created_at: datetime
    files: List[TaskFile] = []

    class Config:
        orm_mode = True
