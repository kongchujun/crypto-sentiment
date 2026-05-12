from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Response, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.case import Case
from app.schemas.case import CaseCreate, CaseRead

router = APIRouter(prefix="/cases", tags=["cases"])


@router.get("", response_model=list[CaseRead])
async def list_cases(db: AsyncSession = Depends(get_db)) -> list[CaseRead]:
    result = await db.execute(select(Case).order_by(Case.created_at.asc()))
    return [CaseRead.model_validate(row) for row in result.scalars().all()]


@router.post("", response_model=CaseRead, status_code=status.HTTP_201_CREATED)
async def create_case(payload: CaseCreate, db: AsyncSession = Depends(get_db)) -> CaseRead:
    case = Case(symbol=payload.symbol)
    db.add(case)
    await db.commit()
    await db.refresh(case)
    return CaseRead.model_validate(case)


@router.delete(
    "/{case_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_case(
    case_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_db),
) -> Response:
    result = await db.execute(delete(Case).where(Case.id == case_id))
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="case not found")
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
