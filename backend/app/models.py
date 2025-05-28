from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from datetime import datetime
from sqlalchemy.orm import relationship
from .database import Base


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String)
    is_done = Column(Boolean, default=False)
    priority = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

    files = relationship("TaskFile", back_populates="task",
                         cascade="all, delete-orphan")


class TaskFile(Base):
    __tablename__ = "task_files"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"))
    file_path = Column(String, nullable=False)

    task = relationship("Task", back_populates="files")
