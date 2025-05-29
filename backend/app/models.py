from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum as SQLEnum, Table
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base
from .schemas import Priority, Status

# Таблица связи многие-ко-многим для тегов
task_tags = Table(
    'task_tags',
    Base.metadata,
    Column('task_id', Integer, ForeignKey('tasks.id')),
    Column('tag_id', Integer, ForeignKey('tags.id'))
)


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    tasks = relationship("Task", secondary=task_tags, back_populates="tags")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String)
    priority = Column(SQLEnum(Priority), default=Priority.MEDIUM)
    status = Column(SQLEnum(Status), default=Status.CREATED)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    deadline = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    files = relationship("TaskFile", back_populates="task",
                         cascade="all, delete-orphan")
    tags = relationship("Tag", secondary=task_tags, back_populates="tasks")


class TaskFile(Base):
    __tablename__ = "task_files"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"))
    file_path = Column(String)

    task = relationship("Task", back_populates="files")
