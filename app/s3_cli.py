from datetime import datetime, timedelta

from collections import defaultdict

import boto3
from os import getenv

import magic
import typer
from dotenv import load_dotenv
from botocore.exceptions import ClientError
import json

import mimetypes
import math
import os
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

load_dotenv()


def init_client():
    try:
        client = boto3.client(
            "s3",
            aws_access_key_id=getenv("aws_access_key_id"),
            aws_secret_access_key=getenv("aws_secret_access_key"),
            aws_session_token=getenv("aws_session_token"),
            region_name=getenv("aws_region_name"))

        return client
    except ClientError as e:
        print(e)
        raise e


def list_buckets(aws_s3_client):
    try:
        return aws_s3_client.list_buckets()
    except ClientError as e:
        print(e)
        return False


def create_bucket(aws_s3_client, bucket_name,
                  region="us-west-2"):
    try:
        location = {'LocationConstraint': region}
        response = aws_s3_client.create_bucket(
            Bucket=bucket_name, CreateBucketConfiguration=location)
    except ClientError as e:
        print(e)
        return False
    status_code = response["ResponseMetadata"]["HTTPStatusCode"]
    if status_code == 200:
        return True
    return False


def delete_bucket(aws_s3_client, bucket_name):
    try:
        response = aws_s3_client.delete_bucket(Bucket=bucket_name)
    except ClientError as e:
        print(e)
        return False
    status_code = response["ResponseMetadata"]["HTTPStatusCode"]
    return str(status_code).startswith("2")


def bucket_exists(aws_s3_client, bucket_name):
    try:
        response = aws_s3_client.head_bucket(Bucket=bucket_name)
    except ClientError as e:
        # print(e)
        return False
    status_code = response["ResponseMetadata"]["HTTPStatusCode"]
    if status_code == 200:
        return True
    return False


def download_file_and_upload_to_s3(aws_s3_client,
                                   bucket_name,
                                   url,
                                   file_name,
                                   keep_local=False):
    from urllib.request import urlopen
    import io
    with urlopen(url) as response:
        content = response.read()
        try:
            aws_s3_client.upload_fileobj(
                Fileobj=io.BytesIO(content),
                Bucket=bucket_name,
                ExtraArgs={'ContentType': 'image/jpg'},
                Key=file_name)
        except Exception as e:
            print(e)

    if keep_local:
        with open(file_name, mode='wb') as file:
            file.write(content)

    return f"https://s3-us-west-2.amazonaws.com/{bucket_name}/{file_name}"


def set_object_access_policy(aws_s3_client, bucket_name, file_name):
    try:
        response = aws_s3_client.put_object_acl(ACL="public-read",
                                                Bucket=bucket_name,
                                                Key=file_name)
    except ClientError as e:
        print(e)
        return False
    status_code = response["ResponseMetadata"]["HTTPStatusCode"]
    if status_code == 200:
        return True
    return False


def generate_public_read_policy(bucket_name):
    policy = {
        "Version":
            "2012-10-17",
        "Statement": [{
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": f"arn:aws:s3:::{bucket_name}/*",
        }],
    }

    return json.dumps(policy)


def create_bucket_policy(aws_s3_client, bucket_name):
    aws_s3_client.delete_public_access_block(Bucket=bucket_name)
    aws_s3_client.put_bucket_policy(
        Bucket=bucket_name, Policy=generate_public_read_policy(bucket_name))
    print("Bucket policy created successfully")


def read_bucket_policy(aws_s3_client, bucket_name):
    try:
        policy = aws_s3_client.get_bucket_policy(Bucket=bucket_name)
        policy_str = policy["Policy"]
        print(policy_str)
    except ClientError as e:
        print(e)
        return False


def upload_small_file(aws_s3_client, bucket_name, file_path, key=None):
    """
    Upload a small file (< 100MB) to S3
    """
    if key is None:
        key = os.path.basename(file_path)

    # Detect content type
    content_type = mimetypes.guess_type(file_path)[0]
    extra_args = {}
    if content_type:
        extra_args['ContentType'] = content_type

    try:
        aws_s3_client.upload_file(
            Filename=file_path,
            Bucket=bucket_name,
            Key=key,
            ExtraArgs=extra_args
        )
        return True
    except ClientError as e:
        print(f"Error uploading file: {e}")
        return False


def upload_large_file(aws_s3_client, bucket_name, file_path, key=None, part_size=10 * 1024 * 1024):
    """
    Upload a large file using multipart upload
    part_size is in bytes (default 10MB)
    """
    if key is None:
        key = os.path.basename(file_path)

    content_type = mimetypes.guess_type(file_path)[0]

    file_size = os.path.getsize(file_path)

    if file_size < 100 * 1024 * 1024:
        return upload_small_file(aws_s3_client, bucket_name, file_path, key)

    try:
        mpu = aws_s3_client.create_multipart_upload(
            Bucket=bucket_name,
            Key=key,
            ContentType=content_type if content_type else 'application/octet-stream'
        )

        num_parts = math.ceil(file_size / part_size)

        parts_lock = Lock()
        parts = []

        def upload_part(part_number):
            offset = (part_number - 1) * part_size

            bytes_range = min(part_size, file_size - offset)

            with open(file_path, 'rb') as f:
                f.seek(offset)
                part_data = f.read(bytes_range)

            response = aws_s3_client.upload_part(
                Bucket=bucket_name,
                Key=key,
                PartNumber=part_number,
                UploadId=mpu['UploadId'],
                Body=part_data
            )

            with parts_lock:
                parts.append({
                    'PartNumber': part_number,
                    'ETag': response['ETag']
                })

        with ThreadPoolExecutor(max_workers=min(num_parts, 4)) as executor:
            executor.map(upload_part, range(1, num_parts + 1))

        aws_s3_client.complete_multipart_upload(
            Bucket=bucket_name,
            Key=key,
            UploadId=mpu['UploadId'],
            MultipartUpload={'Parts': sorted(parts, key=lambda x: x['PartNumber'])}
        )

        return True

    except Exception as e:
        print(f"Error in multipart upload: {e}")

        if 'mpu' in locals():
            aws_s3_client.abort_multipart_upload(
                Bucket=bucket_name,
                Key=key,
                UploadId=mpu['UploadId']
            )
        return False


def set_lifecycle_policy(aws_s3_client, bucket_name, prefix="", days=120):
    """
    Set a lifecycle policy to delete objects after specified days
    """
    try:
        lifecycle_config = {
            'Rules': [
                {
                    'ID': f'Delete after {days} days',
                    'Status': 'Enabled',
                    'Prefix': prefix,
                    'Expiration': {'Days': days}
                }
            ]
        }

        aws_s3_client.put_bucket_lifecycle_configuration(
            Bucket=bucket_name,
            LifecycleConfiguration=lifecycle_config
        )
        return True
    except ClientError as e:
        print(f"Error setting lifecycle policy: {e}")
        return False


def validate_mime_type(file_path, allowed_types=None):
    """
    Validate if file's MIME type is in allowed types
    """
    if allowed_types is None:
        allowed_types = [
            'image/jpeg',
            'image/png',
            'image/gif',
            'application/pdf',
            'text/plain',
            'application/json'
        ]

    mime_type = mimetypes.guess_type(file_path)[0]
    if mime_type is None:
        return False

    return mime_type in allowed_types


def delete_file(aws_s3_client, bucket_name, file_key):
    """
    Delete a file from S3
    """
    try:
        response = aws_s3_client.delete_object(Bucket=bucket_name, Key=file_key)
        status_code = response["ResponseMetadata"]["HTTPStatusCode"]
        return str(status_code).startswith("2")
    except ClientError as e:
        print(f"Error deleting file: {e}")
        return False


def get_bucket_versioning(aws_s3_client, bucket_name):
    """Get bucket versioning status"""
    try:
        response = aws_s3_client.get_bucket_versioning(Bucket=bucket_name)
        status = response.get('Status', 'Disabled')
        return status == 'Enabled'
    except ClientError as e:
        print(f"Error getting bucket versioning: {e}")
        return False


def list_file_versions(aws_s3_client, bucket_name, file_name):
    """List all versions of a specific file"""
    try:
        response = aws_s3_client.list_object_versions(
            Bucket=bucket_name,
            Prefix=file_name
        )
        versions = []
        if 'Versions' in response:
            for version in response['Versions']:
                if version['Key'] == file_name:
                    versions.append({
                        'VersionId': version['VersionId'],
                        'LastModified': version['LastModified'],
                        'IsLatest': version['IsLatest']
                    })
        return versions
    except ClientError as e:
        print(f"Error listing file versions: {e}")
        return []


def restore_file_version(aws_s3_client, bucket_name, file_name, version_id):
    """Restore a specific version of a file as the latest version"""
    try:
        # Copy the old version to the same location, which creates a new version
        copy_source = {
            'Bucket': bucket_name,
            'Key': file_name,
            'VersionId': version_id
        }
        aws_s3_client.copy_object(
            CopySource=copy_source,
            Bucket=bucket_name,
            Key=file_name
        )
        return True
    except ClientError as e:
        print(f"Error restoring file version: {e}")
        return False


def collecting_objects(bucket_name, aws_s3_client):
    extension_counts = defaultdict(int)
    response = aws_s3_client.list_objects_v2(Bucket=bucket_name)

    try:
        if 'Contents' in response:
            for obj in response['Contents']:
                file_name = obj['Key']
                extension = file_name.split('.')[-1] if '.' in file_name else ''
                extension_counts[extension] += 1

                aws_s3_client.copy_object(
                    Bucket=bucket_name,
                    CopySource={
                        'Bucket': bucket_name,
                        'Key': file_name
                    },
                    Key=extension + '/' + file_name,
                    MetadataDirective='REPLACE',
                    ContentType=obj['ContentType'] if 'ContentType' in obj else 'application/octet-stream'
                )
    except ClientError as e:
        print(e)
        return False
    for ext, count in extension_counts.items():
        print(f"{ext}: {count} files")
    return True


def upload_to_folder(bucket_name, file_path, aws_s3_client):
    mime = magic.Magic(mime=True)
    file_type = mime.from_file(file_path)

    main_type = file_type.split('/')[0]
    file_name = os.path.basename(file_path)
    key = f"{main_type}/{file_name}"

    file_size = os.path.getsize(file_path)
    if file_size >= 100 * 1024 * 1024:  # 100MB
        typer.echo("Using multipart upload for large file...")
        result = upload_large_file(aws_s3_client, bucket_name, file_path, key)
    else:
        typer.echo("Using simple upload for small file...")
        result = upload_small_file(aws_s3_client, bucket_name, file_path, key)

    if result:
        typer.echo(f"Successfully uploaded {file_path} to {bucket_name}/{key}")
    else:
        typer.echo("Upload failed")

def delete_old_files(bucket_name, aws_s3_client, file_name):
    versions = list_file_versions(aws_s3_client, bucket_name, file_name)
    if versions:
        six_months_ago = datetime.now(versions[0]['LastModified'].tzinfo) - timedelta(days=180)
        for version in versions:
            if version['LastModified'] < six_months_ago:
                try:
                    aws_s3_client.delete_object(
                        Bucket=bucket_name,
                        Key=file_name,
                        VersionId=version['VersionId']
                    )
                    typer.echo(f"Deleted version {version['VersionId']} of {file_name} from {bucket_name}")
                except ClientError as e:
                    typer.echo(f"Error deleting version {version['VersionId']}: {e}")

