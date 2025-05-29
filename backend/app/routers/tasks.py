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
from sqlalchemy.sql import select
from fastapi.responses import FileResponse
from datetime import datetime

router = APIRouter()

UPLOAD_DIR = "uploads"
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 МБ в байтах
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/", response_model=schemas.Task)
async def create_task(
    title: str = Form(...),
    description: str = Form(...),
    priority: schemas.Priority = Form(schemas.Priority.MEDIUM),
    status: schemas.Status = Form(schemas.Status.CREATED),
    start_date: Optional[datetime] = Form(None),
    end_date: Optional[datetime] = Form(None),
    deadline: Optional[datetime] = Form(None),
    tags: Optional[List[str]] = Form(None),
    files: Optional[List[UploadFile]] = File(None),
    db: AsyncSession = Depends(get_db),
):
    # Валидация дат
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=400,
            detail="Start date cannot be later than end date"
        )

    if deadline and start_date and deadline < start_date:
        raise HTTPException(
            status_code=400,
            detail="Deadline cannot be earlier than start date"
        )

    # 1. Создаем задачу
    task_data = schemas.TaskCreate(
        title=title,
        description=description,
        priority=priority,
        status=status,
        start_date=start_date,
        end_date=end_date,
        deadline=deadline,
        tags=tags or []
    )
    task = await crud.create_task(db, task_data)

    # 2. Если есть файлы, сохраняем их
    if files:
        # Создаем директорию для файлов задачи
        task_dir = os.path.join(UPLOAD_DIR, str(task.id))
        os.makedirs(task_dir, exist_ok=True)

        saved_paths = []
        for file in files:
            # Проверка размера файла
            file_size = 0
            chunk_size = 1024 * 1024  # 1 МБ

            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                file_size += len(chunk)
                if file_size > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File '{file.filename}' is too large. Maximum size is 20MB"
                    )

            await file.seek(0)

            file_location = os.path.join(task_dir, file.filename)

            # Проверяем, не существует ли уже файл с таким именем
            if os.path.exists(file_location):
                raise HTTPException(
                    status_code=400,
                    detail=f"File '{file.filename}' already exists in this task"
                )

            with open(file_location, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            saved_paths.append(file_location)

        # 3. Добавляем записи файлов в БД
        await crud.add_files_to_task(db, task.id, saved_paths)

    return task


@router.get("/", response_model=List[schemas.Task])
async def read_tasks(
    priority: Optional[schemas.Priority] = None,
    status: Optional[schemas.Status] = None,
    start_date_before: Optional[datetime] = None,
    start_date_after: Optional[datetime] = None,
    end_date_before: Optional[datetime] = None,
    end_date_after: Optional[datetime] = None,
    deadline_before: Optional[datetime] = None,
    deadline_after: Optional[datetime] = None,
    search: Optional[str] = None,
    tag: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    return await crud.get_tasks(
        db,
        priority=priority,
        status=status,
        start_date_before=start_date_before,
        start_date_after=start_date_after,
        end_date_before=end_date_before,
        end_date_after=end_date_after,
        deadline_before=deadline_before,
        deadline_after=deadline_after,
        search=search,
        tag=tag
    )


async def update_task_file_path(db: AsyncSession, task_id: int, file_path: str):
    stmt = (
        update(Task)
        .where(Task.id == task_id)
        .values(file_path=file_path)
        .execution_options(synchronize_session="fetch")
    )
    await db.execute(stmt)
    await db.commit()


@router.get("/{task_id}", response_model=schemas.Task)
async def read_task(task_id: int, db: AsyncSession = Depends(get_db)):
    task = await crud.get_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.put("/{task_id}", response_model=schemas.Task)
async def update_task(
    task_id: int,
    task_data: schemas.TaskUpdate,
    db: AsyncSession = Depends(get_db)
):
    # Получаем текущую задачу
    current_task = await crud.get_task(db, task_id)
    if current_task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    # Валидация дат
    update_data = task_data.dict(exclude_unset=True)

    start_date = update_data.get('start_date', current_task.start_date)
    end_date = update_data.get('end_date', current_task.end_date)
    deadline = update_data.get('deadline', current_task.deadline)

    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=400,
            detail="Start date cannot be later than end date"
        )

    if deadline and start_date and deadline < start_date:
        raise HTTPException(
            status_code=400,
            detail="Deadline cannot be earlier than start date"
        )

    task = await crud.update_task(db, task_id, update_data)
    return task


@router.delete("/{task_id}")
async def delete_task(task_id: int, db: AsyncSession = Depends(get_db)):
    success = await crud.delete_task(db, task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"message": "Task deleted successfully"}


@router.get("/{task_id}/files", response_model=List[schemas.TaskFile])
async def get_task_files(task_id: int, db: AsyncSession = Depends(get_db)):
    task = await crud.get_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task.files


@router.delete("/{task_id}/files/{file_id}")
async def delete_task_file(
    task_id: int,
    file_id: int,
    db: AsyncSession = Depends(get_db)
):
    success = await crud.delete_task_file(db, task_id, file_id)
    if not success:
        raise HTTPException(status_code=404, detail="File not found")
    return {"message": "File deleted successfully"}


@router.post("/{task_id}/files", response_model=List[schemas.TaskFile])
async def upload_task_files(
    task_id: int,
    files: Optional[List[UploadFile]] = File(None, max_size=MAX_FILE_SIZE),
    db: AsyncSession = Depends(get_db)
):
    # Проверяем существование задачи
    task = await crud.get_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    if not files:
        return []

    # Создаем директорию для файлов задачи, если её нет
    task_dir = os.path.join(UPLOAD_DIR, str(task_id))
    os.makedirs(task_dir, exist_ok=True)

    saved_paths = []
    for file in files:
        # Дополнительная проверка размера файла
        file_size = 0
        chunk_size = 1024 * 1024  # 1 МБ

        # Читаем файл по частям и проверяем размер
        while True:
            chunk = await file.read(chunk_size)
            if not chunk:
                break
            file_size += len(chunk)
            if file_size > MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=413,
                    detail=f"File '{file.filename}' is too large. Maximum size is 20MB"
                )

        # Сбрасываем указатель файла в начало
        await file.seek(0)

        file_location = os.path.join(task_dir, file.filename)

        # Проверяем, не существует ли уже файл с таким именем
        if os.path.exists(file_location):
            raise HTTPException(
                status_code=400,
                detail=f"File '{file.filename}' already exists in this task"
            )

        # Сохраняем файл
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        saved_paths.append(file_location)

    # Добавляем записи файлов в БД
    return await crud.add_files_to_task(db, task_id, saved_paths)


@router.get("/{task_id}/files/{file_id}/download")
async def download_task_file(
    task_id: int,
    file_id: int,
    db: AsyncSession = Depends(get_db)
):
    # Получаем информацию о файле
    query = select(models.TaskFile).where(
        models.TaskFile.id == file_id,
        models.TaskFile.task_id == task_id
    )
    result = await db.execute(query)
    file = result.scalar_one_or_none()

    if file is None:
        raise HTTPException(status_code=404, detail="File not found")

    if not os.path.exists(file.file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")

    # Получаем имя файла из пути
    filename = os.path.basename(file.file_path)

    # Возвращаем файл как поток
    return FileResponse(
        file.file_path,
        media_type="application/octet-stream",
        filename=filename
    )
