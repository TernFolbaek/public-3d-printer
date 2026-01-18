#!/usr/bin/env python3
"""
Pi Controller for Bambu P1S

Polls for approved jobs from the fly-app API, sends them to the Bambu P1S printer,
and monitors print status.
"""

import os
import sys
import time
import signal
import logging
from pathlib import Path

from config import get_settings
from api_client import APIClient, Job
from bambu_printer import BambuPrinter, PrinterStatus

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Global flag for graceful shutdown
shutdown_requested = False


def signal_handler(signum, frame):
    global shutdown_requested
    logger.info("Shutdown signal received")
    shutdown_requested = True


def ensure_download_dir(download_dir: str) -> Path:
    """Ensure the download directory exists."""
    path = Path(download_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def download_job_file(api: APIClient, job: Job, download_dir: Path) -> Path:
    """Download the job file from Tigris storage."""
    download_url = api.get_download_url(job.id)
    file_path = download_dir / f"{job.id}_{job.filename}"
    api.download_file(download_url, str(file_path))
    return file_path


def process_job(api: APIClient, printer: BambuPrinter, job: Job, download_dir: Path):
    """Process a single print job."""
    logger.info(f"Processing job {job.id}: {job.filename}")

    try:
        # Download the file
        logger.info(f"Downloading {job.filename}...")
        file_path = download_job_file(api, job, download_dir)
        logger.info(f"Downloaded to {file_path}")

        # Upload to printer
        remote_filename = f"{job.id}.3mf"
        logger.info(f"Uploading to printer as {remote_filename}...")
        if not printer.upload_file(str(file_path), remote_filename):
            raise Exception("Failed to upload file to printer")

        # Mark job as printing
        api.start_job(job.id)
        logger.info(f"Job {job.id} marked as printing")

        # Start the print
        if not printer.start_print(remote_filename):
            raise Exception("Failed to start print on printer")

        # Monitor print progress
        monitor_print(api, printer, job)

        # Clean up downloaded file
        try:
            os.remove(file_path)
        except OSError:
            pass

    except Exception as e:
        logger.error(f"Error processing job {job.id}: {e}")
        try:
            api.fail_job(job.id, str(e))
        except Exception as fail_error:
            logger.error(f"Failed to mark job as failed: {fail_error}")


def monitor_print(api: APIClient, printer: BambuPrinter, job: Job):
    """Monitor the print until it completes or fails."""
    settings = get_settings()
    last_progress = -1
    last_progress_update = 0

    logger.info(f"Monitoring print for job {job.id}...")

    while not shutdown_requested:
        status = printer.status

        if status is None:
            time.sleep(2)
            continue

        # Update progress if changed and enough time has passed
        current_time = time.time()
        if (
            status.progress != last_progress
            and current_time - last_progress_update >= settings.progress_update_interval_seconds
        ):
            try:
                api.update_progress(job.id, status.progress)
                last_progress = status.progress
                last_progress_update = current_time
                logger.info(
                    f"Job {job.id} progress: {status.progress}% "
                    f"(layer {status.layer_num}/{status.total_layers}, "
                    f"{status.remaining_time}min remaining)"
                )
            except Exception as e:
                logger.warning(f"Failed to update progress: {e}")

        # Check for completion
        if status.state == "FINISH":
            logger.info(f"Job {job.id} completed successfully!")
            try:
                api.complete_job(job.id)
            except Exception as e:
                logger.error(f"Failed to mark job as complete: {e}")
            return

        # Check for errors
        if status.state == "FAILED" or status.error_code:
            error_msg = f"Print failed: {status.error_code or 'Unknown error'}"
            logger.error(f"Job {job.id} failed: {error_msg}")
            try:
                api.fail_job(job.id, error_msg)
            except Exception as e:
                logger.error(f"Failed to mark job as failed: {e}")
            return

        # Check if print was stopped/idle unexpectedly
        if status.state == "IDLE" and last_progress > 0:
            error_msg = "Print stopped unexpectedly"
            logger.error(f"Job {job.id}: {error_msg}")
            try:
                api.fail_job(job.id, error_msg)
            except Exception as e:
                logger.error(f"Failed to mark job as failed: {e}")
            return

        time.sleep(2)

    # Shutdown requested during print
    logger.warning(f"Shutdown requested while printing job {job.id}")


def main():
    global shutdown_requested

    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    settings = get_settings()

    # Validate configuration
    if not settings.api_key:
        logger.error("API_KEY not configured")
        sys.exit(1)

    if not settings.bambu_ip or not settings.bambu_serial or not settings.bambu_access_code:
        logger.error("Bambu printer configuration incomplete (BAMBU_IP, BAMBU_SERIAL, BAMBU_ACCESS_CODE)")
        sys.exit(1)

    # Initialize components
    download_dir = ensure_download_dir(settings.download_dir)
    api = APIClient()
    printer = BambuPrinter()

    logger.info("Pi Controller starting...")
    logger.info(f"API URL: {settings.api_url}")
    logger.info(f"Printer IP: {settings.bambu_ip}")
    logger.info(f"Poll interval: {settings.poll_interval_seconds}s")

    try:
        # Connect to printer
        printer.connect()

        # Main loop
        while not shutdown_requested:
            try:
                # Check if printer is ready
                if not printer.is_idle():
                    logger.debug("Printer is busy, waiting...")
                    time.sleep(settings.poll_interval_seconds)
                    continue

                # Poll for next job
                logger.debug("Checking for new jobs...")
                job = api.get_next_job()

                if job:
                    logger.info(f"Found job: {job.id} - {job.filename}")
                    process_job(api, printer, job, download_dir)
                else:
                    logger.debug("No jobs available")

            except Exception as e:
                logger.error(f"Error in main loop: {e}")

            # Wait before next poll
            if not shutdown_requested:
                time.sleep(settings.poll_interval_seconds)

    except KeyboardInterrupt:
        logger.info("Interrupted")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
    finally:
        logger.info("Shutting down...")
        printer.disconnect()
        api.close()
        logger.info("Goodbye!")


if __name__ == "__main__":
    main()
