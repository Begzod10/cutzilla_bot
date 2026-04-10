from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from src.core.database import get_db
from src.models.service import Service
from src.schemas.service import ServiceResponse

router = APIRouter()

@router.get("/", response_model=List[ServiceResponse])
async def read_services(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Service).offset(skip).limit(limit))
    services = result.scalars().all()
    return services

@router.get("/{id}", response_model=ServiceResponse)
async def read_service(id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Service).where(Service.id == id))
    service = result.scalars().first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    return service
