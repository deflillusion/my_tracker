from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from enum import Enum


class Priority(str, Enum):
    LOW = "Низкий"
    MEDIUM = "Средний"
    HIGH = "Высокий"


class Status(str, Enum):
    CREATED = "Создано"
    IN_PROGRESS = "В работе"
    TESTING = "Тестирование"
    REVISION = "На доработке"
    UPDATE = "К обновлению"
    DONE = "Выполнено"


class TagBase(BaseModel):
    name: str


class TagCreate(TagBase):
    pass


class Tag(TagBase):
    id: int

    class Config:
        orm_mode = True


class TaskFile(BaseModel):
    id: int
    file_path: str

    class Config:
        orm_mode = True


class TaskBase(BaseModel):
    title: str
    description: str
    priority: Priority = Priority.MEDIUM
    status: Status = Status.CREATED
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    deadline: Optional[datetime] = None


class TaskCreate(TaskBase):
    tags: Optional[List[str]] = []


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[Priority] = None
    status: Optional[Status] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    deadline: Optional[datetime] = None
    tags: Optional[List[str]] = None

    class Config:
        orm_mode = True


class Task(TaskBase):
    id: int
    created_at: datetime
    files: List[TaskFile] = []
    tags: List[Tag] = []

    class Config:
        orm_mode = True
