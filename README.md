# AWS Cloud Infrastructure Automation (Python + boto3 + AWS CLI)

Idempotent provisioning for S3, IAM, Lambda, EC2 and CloudWatch, replacing manual console steps.

## What it builds
- Private, versioned, encrypted S3 bucket
- Least-privilege IAM role for Lambda (read `raw/`, write `processed/`, own logs)
- S3-triggered Lambda: uploads to `raw/` produce a summary in `processed/`
- CloudWatch alarms for Lambda errors and EC2 CPU (optional SNS via `ALARM_TOPIC_ARN`)
- Tagged EC2 launch/list/stop helpers (IMDSv2 enforced)

## Use
    pip install -r requirements.txt
    export AWS_REGION=ap-south-1 BUCKET_NAME=<globally-unique-name> PROJECT_NAME=demo
    python -m automation.cli provision-pipeline
    AMI_ID=ami-xxxx python -m automation.cli launch-ec2

## Test (no AWS account needed; uses moto)
    pytest -q

`scripts/aws_cli_bootstrap.sh` shows the equivalent AWS CLI calls for the bucket.
