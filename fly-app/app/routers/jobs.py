from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.database import get_db
from app.models import User, Job, JobStatus
from app.schemas import JobResponse, JobCreate, UploadUrlResponse
from app.routers.auth import get_current_user
from app.tigris import generate_upload_url, generate_download_url
from app.config import get_settings

router = APIRouter()
settings = get_settings()

MAX_FILE_SIZE = settings.max_file_size_mb * 1024 * 1024  # Convert MB to bytes


@router.post("", response_model=UploadUrlResponse)
async def create_job(
    job_data: JobCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Validate file extension
    if not job_data.filename.lower().endswith(".3mf"):
        raise HTTPException(status_code=400, detail="Only .3mf files are allowed")

    # Validate file size
    if job_data.file_size_bytes > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds maximum allowed ({settings.max_file_size_mb}MB)",
        )

    # Create job record
    job = Job(
        user_id=user.id,
        filename=job_data.filename,
        tigris_key="",  # Will be updated after we generate the URL
        file_size_bytes=job_data.file_size_bytes,
        status=JobStatus.submitted,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Generate pre-signed upload URL
    upload_url, tigris_key = generate_upload_url(job.id, job_data.filename)

    # Update job with tigris key
    job.tigris_key = tigris_key
    await db.commit()

    return UploadUrlResponse(
        job_id=job.id,
        upload_url=upload_url,
        tigris_key=tigris_key,
    )


@router.get("", response_model=List[JobResponse])
async def list_jobs(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Job)
        .where(Job.user_id == user.id)
        .order_by(Job.submitted_at.desc())
    )
    jobs = result.scalars().all()
    return jobs


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Users can only view their own jobs (unless admin)
    if job.user_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized to view this job")

    return job


@router.get("/{job_id}/download")
async def get_download_url(
    job_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Users can only download their own jobs (unless admin)
    if job.user_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized to download this job")

    download_url = generate_download_url(job.tigris_key)
    return {"download_url": download_url}
