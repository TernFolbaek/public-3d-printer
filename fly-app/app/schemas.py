from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.models import JobStatus


class UserBase(BaseModel):
    email: str
    name: Optional[str] = None
    avatar_url: Optional[str] = None


class UserResponse(UserBase):
    id: str
    is_admin: bool
    created_at: datetime

    class Config:
        from_attributes = True


class JobBase(BaseModel):
    filename: str


class JobCreate(JobBase):
    file_size_bytes: int


class JobResponse(JobBase):
    id: str
    user_id: str
    tigris_key: str
    file_size_bytes: int
    status: JobStatus
    status_message: Optional[str] = None
    submitted_at: datetime
    approved_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    approved_by_id: Optional[str] = None
    print_progress: Optional[int] = None

    class Config:
        from_attributes = True


class JobWithUser(JobResponse):
    user: UserResponse


class UploadUrlResponse(BaseModel):
    job_id: str
    upload_url: str
    tigris_key: str


class JobApprovalRequest(BaseModel):
    message: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    version: str = "1.0.0"


# Printer API schemas
class PrinterJobResponse(BaseModel):
    """Simplified job response for the printer API."""
    id: str
    filename: str
    tigris_key: str
    file_size_bytes: int
    status: JobStatus

    class Config:
        from_attributes = True


class PrinterDownloadResponse(BaseModel):
    """Response containing the pre-signed download URL."""
    download_url: str


class PrinterProgressUpdate(BaseModel):
    """Request body for updating print progress."""
    progress: int


class PrinterFailRequest(BaseModel):
    """Request body for marking a job as failed."""
    error_message: str
