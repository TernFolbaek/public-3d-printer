import boto3
from botocore.config import Config
from app.config import get_settings

settings = get_settings()


def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.tigris_endpoint_url,
        aws_access_key_id=settings.tigris_access_key_id,
        aws_secret_access_key=settings.tigris_secret_access_key,
        region_name=settings.tigris_region,
        config=Config(signature_version="s3v4"),
    )


def generate_upload_url(job_id: str, filename: str) -> tuple[str, str]:
    """Generate a pre-signed URL for uploading a file to Tigris."""
    s3_client = get_s3_client()
    key = f"jobs/{job_id}/{filename}"

    url = s3_client.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": settings.tigris_bucket_name,
            "Key": key,
            "ContentType": "application/octet-stream",
        },
        ExpiresIn=3600,  # 1 hour
    )

    return url, key


def generate_download_url(tigris_key: str) -> str:
    """Generate a pre-signed URL for downloading a file from Tigris."""
    s3_client = get_s3_client()

    url = s3_client.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": settings.tigris_bucket_name,
            "Key": tigris_key,
        },
        ExpiresIn=3600,  # 1 hour
    )

    return url


def delete_file(tigris_key: str) -> None:
    """Delete a file from Tigris."""
    s3_client = get_s3_client()
    s3_client.delete_object(
        Bucket=settings.tigris_bucket_name,
        Key=tigris_key,
    )
