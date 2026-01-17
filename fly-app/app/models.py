from sqlalchemy import Column, String, Boolean, DateTime, Integer, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum
import uuid


def generate_uuid():
    return str(uuid.uuid4())


class JobStatus(str, enum.Enum):
    submitted = "submitted"
    approved = "approved"
    rejected = "rejected"
    queued = "queued"
    printing = "printing"
    done = "done"
    failed = "failed"


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    oauth_provider = Column(String, nullable=False)  # "google" or "github"
    oauth_id = Column(String, nullable=False)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    jobs = relationship("Job", back_populates="user", foreign_keys="Job.user_id")
    approved_jobs = relationship("Job", back_populates="approved_by", foreign_keys="Job.approved_by_id")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    filename = Column(String, nullable=False)
    tigris_key = Column(String, nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    status = Column(SQLEnum(JobStatus), default=JobStatus.submitted, nullable=False)
    status_message = Column(String, nullable=True)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())
    approved_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    approved_by_id = Column(String, ForeignKey("users.id"), nullable=True)
    print_progress = Column(Integer, nullable=True)

    user = relationship("User", back_populates="jobs", foreign_keys=[user_id])
    approved_by = relationship("User", back_populates="approved_jobs", foreign_keys=[approved_by_id])
