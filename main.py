import typer
from app.s3_cli import (
    init_client, list_buckets, create_bucket, delete_bucket,
    bucket_exists, download_file_and_upload_to_s3,
    set_object_access_policy, create_bucket_policy,
    read_bucket_policy
)

app = typer.Typer()

@app.command()
def hello():
    typer.echo("🚀 S3 CLI Tool is ready to go!")

@app.command()
def create(bucket_name: str):
    client = init_client()
    result = create_bucket(client, bucket_name)
    typer.echo(f"Create Bucket: {'✅ Success' if result else '❌ Failed'}")

@app.command()
def delete(bucket_name: str):
    client = init_client()
    result = delete_bucket(client, bucket_name)
    typer.echo(f"Delete Bucket: {'✅ Success' if result else '❌ Failed'}")

# more commands to come...

if __name__ == "__main__":
    app()
