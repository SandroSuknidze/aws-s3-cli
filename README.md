# AWS S3 CLI Tool

A command-line interface tool for managing AWS S3 buckets and objects.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Setup](#setup)
- [Commands](#commands)
- [Features](#features)
- [Usage Examples](#usage-examples)
- [Error Handling](#error-handling)

## Prerequisites
* Python 3.12+
* AWS credentials
* Poetry

## Setup

1. Clone the repository
2. Create `.env` file with AWS credentials:
   ```
   aws_access_key_id=your_access_key
   aws_secret_access_key=your_secret_key
   aws_session_token=your_session_token
   aws_region_name=your_region
   ```
3. Install dependencies:
   ```
   poetry install
   ```

## Commands

### Bucket Operations
| Command | Description | Usage |
|---------|-------------|-------|
| `list-buckets-cmd` | List all S3 buckets | `poetry run python main.py list-buckets-cmd` |
| `create-bucket-cmd` | Create a new bucket | `poetry run python main.py create-bucket-cmd BUCKET_NAME` |
| `delete-bucket-cmd` | Delete a bucket | `poetry run python main.py delete-bucket-cmd BUCKET_NAME` |
| `bucket-exists-cmd` | Check if bucket exists | `poetry run python main.py bucket-exists-cmd BUCKET_NAME` |

### File Operations
| Command | Description | Usage |
|---------|-------------|-------|
| `delete-file-cmd` | Delete file from bucket | `poetry run python main.py delete-file-cmd BUCKET_NAME FILE_KEY --del` |
| `download-file-and-upload-to-s3-cmd` | Upload from URL to S3 | `poetry run python main.py download-file-and-upload-to-s3-cmd BUCKET_NAME URL FILE_NAME` |

### Policy Management
| Command | Description | Usage |
|---------|-------------|-------|
| `set-object-access-policy-cmd` | Set object access policy | `poetry run python main.py set-object-access-policy-cmd BUCKET_NAME FILE_NAME` |
| `create-bucket-policy-cmd` | Create bucket policy | `poetry run python main.py create-bucket-policy-cmd BUCKET_NAME` |
| `read-bucket-policy-cmd` | Read bucket policy | `poetry run python main.py read-bucket-policy-cmd BUCKET_NAME` |

## Features
* ✅ Secure AWS client initialization
* ✅ Comprehensive bucket management
* ✅ File operations with safety checks
* ✅ Policy management
* ✅ Error handling

## Usage Examples

### Delete a File
```bash
# This will fail (safety check)
poetry run python main.py delete-file-cmd my-bucket my-file.txt

# This will delete the file
poetry run python main.py delete-file-cmd my-bucket my-file.txt --del
```
### Create and Configure Bucket

| Step | Command | Description |
|------|---------|-------------|
| 1. Create bucket | `poetry run python main.py create-bucket-cmd my-new-bucket` | Creates a new S3 bucket |
| 2. Set policy | `poetry run python main.py create-bucket-policy-cmd my-new-bucket` | Sets public read policy |

## Error Handling

The tool handles various error scenarios:

| Error Type | Description |
|------------|-------------|
| AWS Credentials | Invalid or missing AWS credentials |
| Network | Connection or timeout issues |
| Permissions | Insufficient access rights |
| Resources | Bucket or file not found |

## Support

For a complete list of available commands, use:

| Command | Description |
|---------|-------------|
| `poetry run python main.py list-commands` | Displays all available commands with descriptions |

## Safety Guidelines

1. Always use confirmation flags for destructive operations
2. Verify bucket names before creation
3. Check file existence before operations
4. Monitor operation success messages