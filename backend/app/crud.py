from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from datetime import datetime
from . import models, schemas
import os
from typing import List, Optional


async def get_or_create_tag(db: AsyncSession, tag_name: str) -> models.Tag:
    query = select(models.Tag).where(models.Tag.name == tag_name)
    result = await db.execute(query)
    tag = result.scalar_one_or_none()

    if tag is None:
        tag = models.Tag(name=tag_name)
        db.add(tag)
        await db.commit()
        await db.refresh(tag)

    return tag


async def create_task(db: AsyncSession, task: schemas.TaskCreate):
    # Создаем задачу
    db_task = models.Task(
        title=task.title,
        description=task.description,
        priority=task.priority,
        status=task.status,
        deadline=task.deadline
    )

    # Добавляем теги
    if task.tags:
        for tag_name in task.tags:
            tag = await get_or_create_tag(db, tag_name)
            db_task.tags.append(tag)

    db.add(db_task)
    await db.commit()
    await db.refresh(db_task)

    # Загружаем связанные данные
    query = select(models.Task).options(
        selectinload(models.Task.files),
        selectinload(models.Task.tags)
    ).where(models.Task.id == db_task.id)
    result = await db.execute(query)
    return result.scalar_one()


async def get_tasks(
    db: AsyncSession,
    priority: Optional[schemas.Priority] = None,
    status: Optional[schemas.Status] = None,
    start_date_before: Optional[datetime] = None,
    start_date_after: Optional[datetime] = None,
    end_date_before: Optional[datetime] = None,
    end_date_after: Optional[datetime] = None,
    deadline_before: Optional[datetime] = None,
    deadline_after: Optional[datetime] = None,
    search: Optional[str] = None,
    tag: Optional[str] = None
):
    query = select(models.Task).options(
        selectinload(models.Task.files),
        selectinload(models.Task.tags)
    )

    # Применяем фильтры
    if priority:
        query = query.where(models.Task.priority == priority)
    if status:
        query = query.where(models.Task.status == status)
    if start_date_before:
        query = query.where(models.Task.start_date <= start_date_before)
    if start_date_after:
        query = query.where(models.Task.start_date >= start_date_after)
    if end_date_before:
        query = query.where(models.Task.end_date <= end_date_before)
    if end_date_after:
        query = query.where(models.Task.end_date >= end_date_after)
    if deadline_before:
        query = query.where(models.Task.deadline <= deadline_before)
    if deadline_after:
        query = query.where(models.Task.deadline >= deadline_after)
    if search:
        search_filter = or_(
            models.Task.title.ilike(f"%{search}%"),
            models.Task.description.ilike(f"%{search}%")
        )
        query = query.where(search_filter)
    if tag:
        query = query.join(models.Task.tags).where(models.Tag.name == tag)

    result = await db.execute(query.order_by(models.Task.created_at.desc()))
    return result.scalars().unique().all()


async def add_files_to_task(db: AsyncSession, task_id: int, file_paths: list[str]):
    files = [models.TaskFile(task_id=task_id, file_path=path)
             for path in file_paths]
    db.add_all(files)
    await db.commit()
    # Можно вернуть обновлённые файлы, если нужно
    return files


async def update_task(db: AsyncSession, task_id: int, task_data: schemas.TaskUpdate):
    # Получаем задачу со всеми связанными данными
    query = select(models.Task).options(
        selectinload(models.Task.files),
        selectinload(models.Task.tags)
    ).where(models.Task.id == task_id)
    result = await db.execute(query)
    task = result.scalar_one_or_none()

    if task is None:
        return None

    # Обновляем основные поля
    update_data = task_data.dict(exclude_unset=True)
    if "tags" in update_data:
        tags = update_data.pop("tags")
        task.tags = []
        if tags:
            for tag_name in tags:
                tag = await get_or_create_tag(db, tag_name)
                task.tags.append(tag)

    for key, value in update_data.items():
        setattr(task, key, value)

    await db.commit()
    await db.refresh(task)

    # Перезагружаем задачу со всеми связанными данными
    query = select(models.Task).options(
        selectinload(models.Task.files),
        selectinload(models.Task.tags)
    ).where(models.Task.id == task_id)
    result = await db.execute(query)
    return result.scalar_one()


async def delete_task(db: AsyncSession, task_id: int):
    result = await db.execute(select(models.Task).where(models.Task.id == task_id))
    task = result.scalar_one_or_none()
    if task is None:
        return False
    await db.delete(task)
    await db.commit()
    return True


async def get_task(db: AsyncSession, task_id: int):
    query = select(models.Task).options(
        selectinload(models.Task.files),
        selectinload(models.Task.tags)
    ).where(models.Task.id == task_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def delete_task_file(db: AsyncSession, task_id: int, file_id: int):
    query = select(models.TaskFile).where(
        models.TaskFile.id == file_id,
        models.TaskFile.task_id == task_id
    )
    result = await db.execute(query)
    file = result.scalar_one_or_none()
    if file is None:
        return False

    # Удаляем физический файл
    if os.path.exists(file.file_path):
        os.remove(file.file_path)

    # Удаляем запись из БД
    await db.delete(file)
    await db.commit()
    return True
