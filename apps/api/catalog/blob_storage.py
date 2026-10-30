"""Private Vercel Blob adapter for the catalog's existing object-store contract.

The database keeps tenant-prefixed object keys, never public download URLs.
Reads still pass through the catalog's permission checks and no-store responses.
"""
import io

from botocore.exceptions import BotoCoreError
from vercel.blob import BlobError
from vercel.blob.sync import delete_blob, get_blob, put_blob, query_blobs


class PrivateBlobClient:
    def put_object(self, *, Bucket, Key, Body, ContentType, CacheControl):
        try:
            put_blob(Key, Body, access='private', content_type=ContentType,
                     add_random_suffix=False, allow_overwrite=False,
                     cache_control_max_age=60)
        except BlobError as exc:
            raise BotoCoreError() from exc

    def get_object(self, *, Bucket, Key):
        try:
            result = get_blob(Key, access='private')
            return {'Body': io.BytesIO(result.body)}
        except BlobError as exc:
            raise BotoCoreError() from exc

    def delete_object(self, *, Bucket, Key):
        try:
            delete_blob(Key)
        except BlobError as exc:
            raise BotoCoreError() from exc

    def get_paginator(self, operation):
        if operation != 'list_objects_v2':
            raise ValueError('Unsupported image storage operation')
        return self

    def paginate(self, *, Bucket, Prefix):
        try:
            for item in query_blobs(prefix=Prefix, page_size=100):
                yield {'Contents': [{'Key': item.pathname, 'LastModified': item.uploaded_at}]}
        except BlobError as exc:
            raise BotoCoreError() from exc
