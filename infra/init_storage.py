"""Create the private local development bucket; never changes an existing bucket policy."""
import os
import time

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError


def main():
    client = boto3.client(
        's3', endpoint_url=os.environ['S3_ENDPOINT_URL'],
        aws_access_key_id=os.environ['S3_ACCESS_KEY'],
        aws_secret_access_key=os.environ['S3_SECRET_KEY'],
        region_name=os.getenv('S3_REGION', 'us-east-1'),
        config=Config(connect_timeout=2, read_timeout=5, retries={'max_attempts': 0}),
    )
    bucket = os.environ['S3_BUCKET']
    for attempt in range(30):
        try:
            try:
                client.head_bucket(Bucket=bucket)
            except ClientError as exc:
                if str(exc.response['Error']['Code']) not in ('404', 'NoSuchBucket', 'NotFound'):
                    raise
                client.create_bucket(Bucket=bucket)
            print('Local private storage bucket is ready.')
            return
        except (BotoCoreError, ClientError):
            if attempt == 29:
                raise RuntimeError('Local object storage did not become ready.') from None
            time.sleep(2)


if __name__ == '__main__':
    main()
