import json
import os
from typing import Optional

import requests
import typer
from botocore.exceptions import ClientError

from app.s3_cli import (
    init_client, list_buckets, create_bucket, delete_bucket,
    bucket_exists, download_file_and_upload_to_s3,
    set_object_access_policy, create_bucket_policy,
    read_bucket_policy, generate_public_read_policy, validate_mime_type, upload_large_file, upload_small_file,
    set_lifecycle_policy, delete_file, get_bucket_versioning, list_file_versions, restore_file_version,
    collecting_objects, upload_to_folder, delete_old_files, basic_file_upload, download_webpage_source
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


@app.command()
def collecting_objects_cmd(bucket_name: str,
                           collect: bool = typer.Option(False, "--col", help="Flag to confirm collection")):
    if not collect:
        typer.echo("Please provide --col flag to confirm collection")
        raise typer.Exit(1)

    client = init_client()
    result = collecting_objects(bucket_name, client)

    if result:
        typer.echo(f"Successfully collected objects from {bucket_name}")
    else:
        typer.echo(f"Failed to collect objects from {bucket_name}")
        raise typer.Exit(1)


@app.command()
def upload_to_folder_cmd(
        bucket_name: str,
        file_path: str,
):
    client = init_client()

    result = upload_to_folder(bucket_name, file_path, client)

    if result:
        typer.echo(f"Successfully uploaded {file_path} to {bucket_name}")
    else:
        typer.echo("Upload failed")


@app.command()
def delete_old_files_cmd(bucket_name: str, file_name: str):
    client = init_client()
    delete_old_files(bucket_name, client, file_name)


@app.command()
def create_static_website_cmd(bucket_name: str, file_name: str):
    client = init_client()

    if not create_bucket(client, bucket_name):
        typer.echo("Failed to create bucket")
        raise typer.Exit(1)

    try:
        client.delete_public_access_block(
            Bucket=bucket_name
        )

        website_configuration = {
            'ErrorDocument': {'Key': 'error.html'},
            'IndexDocument': {'Suffix': 'index.html'},
        }
        client.put_bucket_website(Bucket=bucket_name, WebsiteConfiguration=website_configuration)

        client.put_bucket_policy(
            Bucket=bucket_name,
            Policy=generate_public_read_policy(bucket_name)
        )

        if upload_small_file(client, bucket_name, file_name):
            typer.echo(f"Successfully configured static website hosting for {bucket_name}")
            typer.echo(f"Website URL: http://{bucket_name}.s3-website-{client.meta.region_name}.amazonaws.com")
        else:
            typer.echo("Failed to upload file")

    except ClientError as e:
        typer.echo(f"Error configuring website: {e}")
        raise typer.Exit(1)


@app.command()
def create_webpage_from_url_cmd(bucket_name: str, source_url: str):
    """
    Creates a static website from a URL source

    Args:
        bucket_name: Name of the S3 bucket to create
        source_url: URL of the webpage to copy
    """
    client = init_client()

    content, tmp_file = download_webpage_source(source_url)
    if not content or not tmp_file:
        typer.echo("Failed to download webpage")
        raise typer.Exit(1)

    try:
        if not create_bucket(client, bucket_name):
            typer.echo("Failed to create bucket")
            raise typer.Exit(1)

        website_configuration = {
            'ErrorDocument': {'Key': 'error.html'},
            'IndexDocument': {'Suffix': 'index.html'},
        }

        client.delete_public_access_block(Bucket=bucket_name)

        client.put_bucket_website(
            Bucket=bucket_name,
            WebsiteConfiguration=website_configuration
        )

        client.put_bucket_policy(
            Bucket=bucket_name,
            Policy=generate_public_read_policy(bucket_name)
        )

        if basic_file_upload(bucket_name, tmp_file, client):
            client.copy_object(
                Bucket=bucket_name,
                CopySource={'Bucket': bucket_name, 'Key': os.path.basename(tmp_file)},
                Key='index.html',
            )
            client.delete_object(
                Bucket=bucket_name,
                Key=os.path.basename(tmp_file)
            )
            with open(tmp_file, 'rb') as file:
                client.put_object(
                    Bucket=bucket_name,
                    Key='index.html',
                    Body=file,
                    ContentType='text/html'
                )

            typer.echo(f"Successfully created website from {source_url}")
            typer.echo(f"Website URL: http://{bucket_name}.s3-website-{client.meta.region_name}.amazonaws.com")
        else:
            typer.echo("Failed to upload webpage content")

    except ClientError as e:
        typer.echo(f"Error configuring website: {e}")
        raise typer.Exit(1)
    finally:
        if os.path.exists(tmp_file):
            os.unlink(tmp_file)


@app.command()
def inspire_cmd(
        author: Optional[str] = typer.Option(None, help="Get quote from specific author"),
        bucket_name: Optional[str] = typer.Option(None, help="S3 bucket name to save quote"),
):
    """
    Get inspiring quotes from the API. Optionally filter by author and save to S3.
    """
    try:
        quote_url = f"https://api.quotable.kurokeita.dev/api/quotes/random?author={author}"
        quote_response = requests.get(quote_url)
        quote_response.raise_for_status()
        quote_data = quote_response.json()

        if not quote_data['quote']:
            typer.echo(f"No author found matching '{author}'")
            raise typer.Exit(1)

        formatted_quote = f"\"{quote_data['quote']['content']}\"\n- {author}"
        typer.echo(formatted_quote)

        if not bucket_name:
            typer.echo("Error: bucket_name is required when using --save")
            raise typer.Exit(1)

        client = init_client()

        quote_json = {
            "quote": quote_data['quote']['content'],
            "author": quote_data['quote']['author'],
            "tags": quote_data['quote']['tags'],
            "id": quote_data['quote']['id']
        }

        filename = f"quote_{quote_data['quote']['id']}.json"

        try:
            client.put_object(
                Bucket=bucket_name,
                Key=filename,
                Body=json.dumps(quote_json, indent=2),
                ContentType='application/json'
            )
            typer.echo(f"\nQuote saved to s3://{bucket_name}/{filename}")
        except ClientError as e:
            typer.echo(f"Error saving to S3: {e}")
            raise typer.Exit(1)

    except requests.RequestException as e:
        typer.echo(f"Error fetching quote: {e}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
