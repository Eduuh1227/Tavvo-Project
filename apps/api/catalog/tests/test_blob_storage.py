from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from botocore.exceptions import BotoCoreError
from django.core.files.uploadedfile import SimpleUploadedFile
from vercel.blob import BlobError

from catalog import blob_storage, storage


def test_private_blob_uses_tenant_key_and_private_access(monkeypatch, settings):
    settings.IMAGE_STORAGE_BACKEND = 'vercel_blob'
    put = Mock()
    monkeypatch.setattr(blob_storage, 'put_blob', put)
    key = 'restaurants/tenant/products/product/image.png'
    client = storage.client()
    client.put_object(Bucket='unused', Key=key, Body=b'image', ContentType='image/png', CacheControl='no-store')
    assert put.call_args.args == (key, b'image')
    assert put.call_args.kwargs['access'] == 'private'
    assert put.call_args.kwargs['allow_overwrite'] is False
    assert put.call_args.kwargs['add_random_suffix'] is False
    get = Mock(return_value=SimpleNamespace(body=b'image'))
    monkeypatch.setattr(blob_storage, 'get_blob', get)
    image = SimpleNamespace(storage_key=key, mime='image/png', size=5)
    response = storage.image_response(image)
    assert b''.join(response.streaming_content) == b'image'
    assert response['Cache-Control'] == 'no-store'
    get.assert_called_once_with(key, access='private')


def test_blob_reconciliation_keeps_prefix_and_timestamps(monkeypatch):
    when = datetime(2026, 1, 1, tzinfo=timezone.utc)
    query = Mock(return_value=[SimpleNamespace(pathname='restaurants/a/old.png', uploaded_at=when)])
    monkeypatch.setattr(blob_storage, 'query_blobs', query)
    pages = list(blob_storage.PrivateBlobClient().get_paginator('list_objects_v2').paginate(Bucket='', Prefix='restaurants/a/'))
    assert pages == [{'Contents': [{'Key': 'restaurants/a/old.png', 'LastModified': when}]}]
    query.assert_called_once_with(prefix='restaurants/a/', page_size=100)


def test_blob_failure_returns_service_unavailable(monkeypatch, settings):
    settings.IMAGE_STORAGE_BACKEND = 'vercel_blob'
    monkeypatch.setattr(blob_storage, 'get_blob', Mock(side_effect=BlobError('offline')))
    with pytest.raises(storage.StorageUnavailable):
        storage.image_response(SimpleNamespace(storage_key='restaurants/a/image.png'))
    monkeypatch.setattr(blob_storage, 'delete_blob', Mock(side_effect=BlobError('offline')))
    with pytest.raises(BotoCoreError):
        storage.client().delete_object(Bucket='', Key='restaurants/a/image.png')


def test_invalid_upload_never_reaches_blob(monkeypatch, settings):
    settings.IMAGE_STORAGE_BACKEND = 'vercel_blob'
    put = Mock()
    monkeypatch.setattr(blob_storage, 'put_blob', put)
    with pytest.raises(storage.ValidationError):
        storage.upload_image('a', 'b', SimpleUploadedFile('fake.png', b'not an image'))
    put.assert_not_called()
