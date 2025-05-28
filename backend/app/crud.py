from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from . import models, schemas


async def create_task(db: AsyncSession, task: schemas.TaskCreate):
    db_task = models.Task(**task.dict())
    db.add(db_task)
    await db.commit()
    await db.refresh(db_task)

    # Загрузить файлы (их пока нет, но для единообразия)
    query = select(models.Task).options(selectinload(
        models.Task.files)).where(models.Task.id == db_task.id)
    result = await db.execute(query)
    task_with_files = result.scalar_one()
    return task_with_files


async def get_tasks(db: AsyncSession, is_done: bool | None = None):
    query = select(models.Task).options(selectinload(models.Task.files))
    if is_done is not None:
        query = query.where(models.Task.is_done == is_done)
    result = await db.execute(query.order_by(models.Task.created_at.desc()))
    return result.scalars().unique().all()


async def add_files_to_task(db: AsyncSession, task_id: int, file_paths: list[str]):
    files = [models.TaskFile(task_id=task_id, file_path=path)
             for path in file_paths]
    db.add_all(files)
    await db.commit()
    # Можно вернуть обновлённые файлы, если нужно
    return files


async def update_task(db: AsyncSession, task_id: int, task_data: dict):
    result = await db.execute(select(models.Task).where(models.Task.id == task_id))
    task = result.scalar_one_or_none()
    if task is None:
        return None
    for key, value in task_data.items():
        setattr(task, key, value)
    await db.commit()
    await db.refresh(task)
    return task


async def delete_task(db: AsyncSession, task_id: int):
    result = await db.execute(select(models.Task).where(models.Task.id == task_id))
    task = result.scalar_one_or_none()
    if task is None:
        return False
    await db.delete(task)
    await db.commit()
    return True
