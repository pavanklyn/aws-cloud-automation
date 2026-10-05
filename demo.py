import json
import os

os.environ.update(AWS_ACCESS_KEY_ID="test", AWS_SECRET_ACCESS_KEY="test", AWS_DEFAULT_REGION="ap-south-1")

import boto3
from moto import mock_aws

from automation import cloudwatch, iam, lambda_deploy, s3
from automation.config import Settings
from lambda_functions.s3_processor import handler

with mock_aws():
    cfg = Settings(region="ap-south-1", project="demo", bucket="demo-bucket-12345")
    s3c = boto3.client("s3", region_name=cfg.region)

    bucket = s3.ensure_bucket(cfg, client=s3c)
    print("1. Bucket created:", bucket)

    role = iam.ensure_lambda_role(cfg, bucket)
    print("2. IAM role:", role)

    fn = lambda_deploy.deploy_s3_pipeline(cfg, role, bucket, s3=s3c)
    print("3. Lambda deployed:", fn)

    print("4. Alarm:", cloudwatch.create_lambda_error_alarm(cfg, fn))

    s3c.put_object(Bucket=bucket, Key="raw/sample.txt", Body=b"name,score\nasha,90\nravi,85\n")
    print("5. Uploaded raw/sample.txt")

    handler.s3 = s3c  # moto won't invoke the Lambda itself, so call the handler directly
    event = {"Records": [{"s3": {"bucket": {"name": bucket}, "object": {"key": "raw/sample.txt"}}}]}
    print("6. Handler result:", handler.lambda_handler(event))

    out = s3c.get_object(Bucket=bucket, Key="processed/sample.txt.summary.json")["Body"].read()
    print("7. Output file contents:")
    print(json.dumps(json.loads(out), indent=2))