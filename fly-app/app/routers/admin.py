from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime
from typing import List

from app.database import get_db
from app.models import User, Job, JobStatus
from app.schemas import JobWithUser, JobApprovalRequest
from app.routers.auth import get_current_admin

router = APIRouter()


@router.get("/jobs", response_model=List[JobWithUser])
async def list_pending_jobs(
    status: JobStatus | None = None,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    query = select(Job).options(selectinload(Job.user))

    if status:
        query = query.where(Job.status == status)
    else:
        # Default to showing submitted (pending) jobs
        query = query.where(Job.status == JobStatus.submitted)

    query = query.order_by(Job.submitted_at.asc())
    result = await db.execute(query)
    jobs = result.scalars().all()
    return jobs


@router.get("/jobs/all", response_model=List[JobWithUser])
async def list_all_jobs(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Job)
        .options(selectinload(Job.user))
        .order_by(Job.submitted_at.desc())
    )
    jobs = result.scalars().all()
    return jobs


@router.post("/jobs/{job_id}/approve", response_model=JobWithUser)
async def approve_job(
    job_id: str,
    request: JobApprovalRequest = None,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Job).options(selectinload(Job.user)).where(Job.id == job_id)
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != JobStatus.submitted:
        raise HTTPException(
            status_code=400,
            detail=f"Job cannot be approved (current status: {job.status})",
        )

    job.status = JobStatus.approved
    job.approved_at = datetime.utcnow()
    job.approved_by_id = admin.id
    if request and request.message:
        job.status_message = request.message

    await db.commit()
    await db.refresh(job)
    return job


@router.post("/jobs/{job_id}/reject", response_model=JobWithUser)
async def reject_job(
    job_id: str,
    request: JobApprovalRequest = None,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Job).options(selectinload(Job.user)).where(Job.id == job_id)
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != JobStatus.submitted:
        raise HTTPException(
            status_code=400,
            detail=f"Job cannot be rejected (current status: {job.status})",
        )

    job.status = JobStatus.rejected
    if request and request.message:
        job.status_message = request.message

    await db.commit()
    await db.refresh(job)
    return job


@router.post("/jobs/{job_id}/queue", response_model=JobWithUser)
async def queue_job(
    job_id: str,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Move an approved job to the print queue."""
    result = await db.execute(
        select(Job).options(selectinload(Job.user)).where(Job.id == job_id)
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != JobStatus.approved:
        raise HTTPException(
            status_code=400,
            detail=f"Only approved jobs can be queued (current status: {job.status})",
        )

    job.status = JobStatus.queued
    await db.commit()
    await db.refresh(job)
    return job
