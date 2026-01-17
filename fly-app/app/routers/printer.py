from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from app.database import get_db
from app.models import Job, JobStatus
from app.schemas import (
    PrinterJobResponse,
    PrinterDownloadResponse,
    PrinterProgressUpdate,
    PrinterFailRequest,
)
from app.routers.auth import get_printer_api_key
from app.tigris import generate_download_url

router = APIRouter()


@router.get("/jobs/next", response_model=PrinterJobResponse | None)
async def get_next_job(
    _: str = Depends(get_printer_api_key),
    db: AsyncSession = Depends(get_db),
):
    """Get the next approved job and mark it as queued."""
    result = await db.execute(
        select(Job)
        .where(Job.status == JobStatus.approved)
        .order_by(Job.approved_at.asc())
        .limit(1)
    )
    job = result.scalar_one_or_none()

    if not job:
        return None

    job.status = JobStatus.queued
    await db.commit()
    await db.refresh(job)

    return job


@router.get("/jobs/{job_id}/download", response_model=PrinterDownloadResponse)
async def get_job_download_url(
    job_id: str,
    _: str = Depends(get_printer_api_key),
    db: AsyncSession = Depends(get_db),
):
    """Get a pre-signed download URL for a job's file."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    download_url = generate_download_url(job.tigris_key)
    return PrinterDownloadResponse(download_url=download_url)


@router.post("/jobs/{job_id}/start", response_model=PrinterJobResponse)
async def start_job(
    job_id: str,
    _: str = Depends(get_printer_api_key),
    db: AsyncSession = Depends(get_db),
):
    """Mark a job as printing."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != JobStatus.queued:
        raise HTTPException(
            status_code=400,
            detail=f"Job must be in 'queued' status to start, current status: {job.status}",
        )

    job.status = JobStatus.printing
    job.print_progress = 0
    await db.commit()
    await db.refresh(job)

    return job


@router.post("/jobs/{job_id}/progress", response_model=PrinterJobResponse)
async def update_job_progress(
    job_id: str,
    progress_update: PrinterProgressUpdate,
    _: str = Depends(get_printer_api_key),
    db: AsyncSession = Depends(get_db),
):
    """Update the print progress for a job."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != JobStatus.printing:
        raise HTTPException(
            status_code=400,
            detail=f"Job must be in 'printing' status to update progress, current status: {job.status}",
        )

    if progress_update.progress < 0 or progress_update.progress > 100:
        raise HTTPException(status_code=400, detail="Progress must be between 0 and 100")

    job.print_progress = progress_update.progress
    await db.commit()
    await db.refresh(job)

    return job


@router.post("/jobs/{job_id}/complete", response_model=PrinterJobResponse)
async def complete_job(
    job_id: str,
    _: str = Depends(get_printer_api_key),
    db: AsyncSession = Depends(get_db),
):
    """Mark a job as done."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != JobStatus.printing:
        raise HTTPException(
            status_code=400,
            detail=f"Job must be in 'printing' status to complete, current status: {job.status}",
        )

    job.status = JobStatus.done
    job.print_progress = 100
    job.completed_at = datetime.utcnow()
    await db.commit()
    await db.refresh(job)

    return job


@router.post("/jobs/{job_id}/fail", response_model=PrinterJobResponse)
async def fail_job(
    job_id: str,
    fail_request: PrinterFailRequest,
    _: str = Depends(get_printer_api_key),
    db: AsyncSession = Depends(get_db),
):
    """Mark a job as failed."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status not in [JobStatus.queued, JobStatus.printing]:
        raise HTTPException(
            status_code=400,
            detail=f"Job must be in 'queued' or 'printing' status to fail, current status: {job.status}",
        )

    job.status = JobStatus.failed
    job.status_message = fail_request.error_message
    job.completed_at = datetime.utcnow()
    await db.commit()
    await db.refresh(job)

    return job
