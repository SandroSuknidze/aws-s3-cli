import os

import typer
from app.s3_cli import (
    init_client, list_buckets, create_bucket, delete_bucket,
    bucket_exists, download_file_and_upload_to_s3,
    set_object_access_policy, create_bucket_policy,
    read_bucket_policy, generate_public_read_policy, validate_mime_type, upload_large_file, upload_small_file,
    set_lifecycle_policy, delete_file, get_bucket_versioning, list_file_versions, restore_file_version
)

app = typer.Typer()


@app.command()
def list_commands():
    commands = [
        "init-client-cmd           - Initialize S3 client",
        "list-buckets-cmd         - List all S3 buckets",
        "create-bucket-cmd        - Create a new bucket",
        "delete-bucket-cmd        - Delete an existing bucket",
        "bucket-exists-cmd        - Check if bucket exists",
        "download-file-and-upload-to-s3-cmd - Download and upload file to S3",
        "set-object-access-policy-cmd      - Set access policy for an object",
        "create-bucket-policy-cmd          - Create bucket policy",
        "read-bucket-policy-cmd            - Read bucket policy",
        "list-commands           - Show this list of commands",
        "get-bucket-versioning-cmd    - Check if bucket versioning is enabled",
        "list-file-versions-cmd      - List all versions of a specific file",
        "restore-version-cmd         - Restore a previous version as the lates"
    ]

    typer.echo("Available commands:")
    for command in commands:
        typer.echo(f"  {command}")


@app.command()
def list_buckets_cmd():
    client = init_client()
    buckets = list_buckets(client)
    if buckets:
        for bucket in buckets['Buckets']:
            typer.echo(f'  {bucket["Name"]}')
    else:
        typer.echo("No buckets found.")


@app.command()
def create_bucket_cmd(bucket_name: str):
    client = init_client()
    result = create_bucket(client, bucket_name)
    typer.echo(f"Create Bucket: {'Success' if result else 'Failed'}")


@app.command()
def delete_bucket_cmd(bucket_name: str):
    client = init_client()
    result = delete_bucket(client, bucket_name)
    typer.echo(f"Delete Bucket: {'Success' if result else 'Failed'}")


@app.command()
def bucket_exists_cmd(bucket_name: str):
    client = init_client()
    result = bucket_exists(client, bucket_name)
    typer.echo(f"Bucket exists: {'Yes' if result else 'No'}")


@app.command()
def download_file_and_upload_to_s3_cmd(bucket_name: str, url: str, file_name: str, keep_local: bool = False):
    client = init_client()
    result = download_file_and_upload_to_s3(client, bucket_name, url, file_name, keep_local)
    typer.echo(f"File URL: {result}")


@app.command()
def set_object_access_policy_cmd(bucket_name: str, file_name: str):
    client = init_client()
    result = set_object_access_policy(client, bucket_name, file_name)
    typer.echo(f"Set access policy: {'Success' if result else 'Failed'}")


@app.command()
def create_bucket_policy_cmd(bucket_name: str):
    client = init_client()
    try:
        create_bucket_policy(client, bucket_name)
        typer.echo(f"Successfully created policy for bucket: {bucket_name}")
    except Exception as e:
        typer.echo(f"Failed to create policy: {str(e)}")


@app.command()
def read_bucket_policy_cmd(bucket_name: str):
    client = init_client()
    result = read_bucket_policy(client, bucket_name)
    if not result:
        typer.echo(f"Failed to read policy for bucket: {bucket_name}")


@app.command()
def upload_file_cmd(bucket_name: str, file_path: str, key: str = None, validate_mime: bool = False):
    client = init_client()

    if validate_mime and not validate_mime_type(file_path):
        typer.echo("Error: Invalid file type")
        return

    file_size = os.path.getsize(file_path)
    if file_size >= 100 * 1024 * 1024:  # 100MB
        typer.echo("Using multipart upload for large file...")
        result = upload_large_file(client, bucket_name, file_path, key)
    else:
        typer.echo("Using simple upload for small file...")
        result = upload_small_file(client, bucket_name, file_path, key)

    typer.echo(f"Upload {'successful' if result else 'failed'}")


@app.command()
def set_lifecycle_cmd(bucket_name: str, prefix: str = "", days: int = 120):
    client = init_client()
    result = set_lifecycle_policy(client, bucket_name, prefix, days)
    typer.echo(f"Lifecycle policy {'set successfully' if result else 'failed to set'}")


@app.command()
def delete_file_cmd(bucket_name: str, file_key: str,
                   delete: bool = typer.Option(False, "--del", help="Flag to confirm deletion")):
    if not delete:
        typer.echo("Please provide --del flag to confirm deletion")
        raise typer.Exit(1)

    client = init_client()
    if delete_file(client, bucket_name, file_key):
        typer.echo(f"Successfully deleted {file_key} from {bucket_name}")
    else:
        typer.echo(f"Failed to delete {file_key}")
        raise typer.Exit(1)

@app.command()
def get_bucket_versioning_cmd(bucket_name: str):
    client = init_client()
    is_enabled = get_bucket_versioning(client, bucket_name)
    typer.echo(f"Versioning for bucket {bucket_name}: {'Enabled' if is_enabled else 'Disabled'}")

@app.command()
def list_file_versions_cmd(bucket_name: str, file_name: str):
    client = init_client()
    versions = list_file_versions(client, bucket_name, file_name)
    if versions:
        typer.echo(f"\nVersions of {file_name} in {bucket_name}:")
        for version in versions:
            typer.echo(f"Version ID: {version['VersionId']}")
            typer.echo(f"Last Modified: {version['LastModified']}")
            typer.echo(f"Is Latest: {version['IsLatest']}")
            typer.echo("---")
        typer.echo(f"\nTotal versions: {len(versions)}")
    else:
        typer.echo(f"No versions found for {file_name}")


@app.command()
def restore_version_cmd(bucket_name: str, file_name: str, version_id: str):
    client = init_client()
    success = restore_file_version(client, bucket_name, file_name, version_id)
    if success:
        typer.echo(f"Successfully restored version {version_id} of {file_name}")
    else:
        typer.echo("Failed to restore version")


if __name__ == "__main__":
    app()
