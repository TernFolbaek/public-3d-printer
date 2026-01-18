import httpx
from dataclasses import dataclass
from typing import Optional
import logging

from config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class Job:
    id: str
    filename: str
    tigris_key: str
    file_size_bytes: int
    status: str


class APIClient:
    """HTTP client for communicating with the fly-app API."""

    def __init__(self):

        settings = get_settings()
        self.base_url = settings.api_url.rstrip("/")
        self.api_key = settings.api_key
        self._client: Optional[httpx.Client] = None

    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.base_url,
                headers={"X-API-Key": self.api_key},
                timeout=30.0,
            )
        return self._client

    def close(self):
        if self._client:
            self._client.close()
            self._client = None

    def get_next_job(self) -> Optional[Job]:
        """Fetch the next approved job from the API."""
        try:
            response = self.client.get("/printer/jobs/next")
            response.raise_for_status()

            data = response.json()
            if data is None:
                return None

            return Job(
                id=data["id"],
                filename=data["filename"],
                tigris_key=data["tigris_key"],
                file_size_bytes=data["file_size_bytes"],
                status=data["status"],
            )
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching next job: {e.response.status_code}")
            raise
        except Exception as e:
            logger.error(f"Error fetching next job: {e}")
            raise

    def get_download_url(self, job_id: str) -> str:
        """Get the pre-signed download URL for a job."""
        try:
            response = self.client.get(f"/printer/jobs/{job_id}/download")
            response.raise_for_status()
            data = response.json()
            return data["download_url"]
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting download URL: {e.response.status_code}")
            raise
        except Exception as e:
            logger.error(f"Error getting download URL: {e}")
            raise

    def start_job(self, job_id: str) -> Job:
        """Mark a job as printing."""
        try:
            response = self.client.post(f"/printer/jobs/{job_id}/start")
            response.raise_for_status()
            data = response.json()
            return Job(
                id=data["id"],
                filename=data["filename"],
                tigris_key=data["tigris_key"],
                file_size_bytes=data["file_size_bytes"],
                status=data["status"],
            )
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error starting job: {e.response.status_code}")
            raise
        except Exception as e:
            logger.error(f"Error starting job: {e}")
            raise

    def update_progress(self, job_id: str, progress: int) -> Job:
        """Update the print progress for a job."""
        try:
            response = self.client.post(
                f"/printer/jobs/{job_id}/progress",
                json={"progress": progress},
            )
            response.raise_for_status()
            data = response.json()
            return Job(
                id=data["id"],
                filename=data["filename"],
                tigris_key=data["tigris_key"],
                file_size_bytes=data["file_size_bytes"],
                status=data["status"],
            )
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error updating progress: {e.response.status_code}")
            raise
        except Exception as e:
            logger.error(f"Error updating progress: {e}")
            raise

    def complete_job(self, job_id: str) -> Job:
        """Mark a job as done."""
        try:
            response = self.client.post(f"/printer/jobs/{job_id}/complete")
            response.raise_for_status()
            data = response.json()
            return Job(
                id=data["id"],
                filename=data["filename"],
                tigris_key=data["tigris_key"],
                file_size_bytes=data["file_size_bytes"],
                status=data["status"],
            )
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error completing job: {e.response.status_code}")
            raise
        except Exception as e:
            logger.error(f"Error completing job: {e}")
            raise

    def fail_job(self, job_id: str, error_message: str) -> Job:
        """Mark a job as failed."""
        try:
            response = self.client.post(
                f"/printer/jobs/{job_id}/fail",
                json={"error_message": error_message},
            )
            response.raise_for_status()
            data = response.json()
            return Job(
                id=data["id"],
                filename=data["filename"],
                tigris_key=data["tigris_key"],
                file_size_bytes=data["file_size_bytes"],
                status=data["status"],
            )
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error failing job: {e.response.status_code}")
            raise
        except Exception as e:
            logger.error(f"Error failing job: {e}")
            raise

    def download_file(self, download_url: str, destination: str) -> None:
        """Download a file from the given URL to the destination path."""
        try:
            with httpx.stream("GET", download_url, timeout=300.0) as response:
                response.raise_for_status()
                with open(destination, "wb") as f:
                    for chunk in response.iter_bytes(chunk_size=8192):
                        f.write(chunk)
            logger.info(f"Downloaded file to {destination}")
        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            raise
