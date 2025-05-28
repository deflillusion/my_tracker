from fastapi import APIRouter, Depends, UploadFile, File, Form
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
import os
import shutil
from sqlalchemy import update
from app.models import Task
from sqlalchemy.ext.asyncio import AsyncSession
from app import schemas, crud
from app.database import get_db

router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/", response_model=schemas.Task)
async def create_task(
    title: str = Form(...),
    description: str = Form(...),
    priority: int = Form(1),
    files: Optional[List[UploadFile]] = File(None),
    db: AsyncSession = Depends(get_db),
):
    # 1. Создаем задачу без файлов
    task_data = schemas.TaskCreate(
        title=title, description=description, priority=priority)
    task = await crud.create_task(db, task_data)

    # 2. Если есть файлы, сохраняем их
    saved_paths = []
    if files:
        task_dir = os.path.join(UPLOAD_DIR, str(task.id))
        os.makedirs(task_dir, exist_ok=True)

        for file in files:
            file_location = os.path.join(task_dir, file.filename)

            if os.path.exists(file_location):
                raise HTTPException(
                    status_code=400,
                    detail=f"File '{file.filename}' already exists in this task."
                )

            with open(file_location, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            saved_paths.append(file_location)

        # 3. Добавляем записи файлов в БД
        await crud.add_files_to_task(db, task.id, saved_paths)

    # Возвращаем задачу с файлами (если нужно, подгрузи их через relation в Pydantic)
    return task


@router.get("/", response_model=List[schemas.Task])
async def read_tasks(is_done: Optional[bool] = None, db: AsyncSession = Depends(get_db)):
    return await crud.get_tasks(db, is_done)


async def update_task_file_path(db: AsyncSession, task_id: int, file_path: str):
    stmt = (
        update(Task)
        .where(Task.id == task_id)
        .values(file_path=file_path)
        .execution_options(synchronize_session="fetch")
    )
    await db.execute(stmt)
    await db.commit()
