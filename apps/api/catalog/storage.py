import io
import logging
import uuid
import warnings

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from django.conf import settings
from django.http import FileResponse
from PIL import Image, ImageOps, UnidentifiedImageError
from rest_framework.exceptions import APIException, ValidationError

logger = logging.getLogger(__name__)
FORMATS = {"JPEG": ("jpg", "image/jpeg"), "PNG": ("png", "image/png"), "WEBP": ("webp", "image/webp")}


class StorageUnavailable(APIException):
    status_code = 503
    default_detail = "Image storage is temporarily unavailable."
    default_code = "storage_unavailable"


def client():
    return boto3.client(
        "s3", endpoint_url=settings.S3_ENDPOINT_URL or None,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
        region_name=settings.S3_REGION,
        config=Config(signature_version="s3v4", connect_timeout=5, read_timeout=10, retries={"max_attempts": 2}),
    )


def validate_image(upload):
    limit = getattr(settings, "IMAGE_MAX_BYTES", 5 * 1024 * 1024)
    if upload.size > limit:
        raise ValidationError({"file": "Image exceeds the 5 MB limit."})
    data = upload.read(limit + 1)
    if len(data) > limit:
        raise ValidationError({"file": "Image exceeds the 5 MB limit."})
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as opened:
                image_format = opened.format
                if image_format not in FORMATS or opened.width * opened.height > 20_000_000:
                    raise ValidationError({"file": "Use JPEG, PNG or WebP images up to 20 megapixels."})
                opened.verify()
            with Image.open(io.BytesIO(data)) as opened:
                clean = ImageOps.exif_transpose(opened)
                # Decode and re-encode; discard metadata and trailing arbitrary file content.
                if image_format == "JPEG":
                    clean = clean.convert("RGB")
                clean.info.clear()
                output = io.BytesIO()
                clean.save(output, format=image_format)
                encoded = output.getvalue()
        if len(encoded) > limit:
            raise ValidationError({"file": "Normalized image exceeds the size limit."})
        extension, mime = FORMATS[image_format]
        return encoded, extension, mime
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ValidationError({"file": "File is not a supported, valid image."}) from exc


def upload_image(restaurant_id, product_id, upload):
    encoded, extension, mime = validate_image(upload)
    key = f"restaurants/{restaurant_id}/products/{product_id}/{uuid.uuid4()}.{extension}"
    try:
        client().put_object(Bucket=settings.S3_BUCKET, Key=key, Body=encoded, ContentType=mime, CacheControl="no-store")
    except (BotoCoreError, ClientError) as exc:
        raise StorageUnavailable() from exc
    return key, len(encoded), mime


def delete_image(key):
    try:
        client().delete_object(Bucket=settings.S3_BUCKET, Key=key)
    except (BotoCoreError, ClientError):
        # DB access has already been revoked. Reconciliation removes orphaned objects.
        logger.exception("Image object deletion failed; storage reconciliation is required")


def image_response(image):
    try:
        stored = client().get_object(Bucket=settings.S3_BUCKET, Key=image.storage_key)
    except (BotoCoreError, ClientError) as exc:
        raise StorageUnavailable() from exc
    response = FileResponse(stored["Body"], content_type=image.mime)
    response["Content-Length"] = image.size
    response["Cache-Control"] = "no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response
